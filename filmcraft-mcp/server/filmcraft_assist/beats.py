"""Détection du tempo, des temps et des premiers temps de mesure d'une musique (librosa)."""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path
from typing import Any, Sequence

from . import config
from .proc import ToolError, require_file, run_worker

ANALYSIS_SAMPLE_RATE = 22050
BEATS_PER_BAR = 4
WORKER_TIMEOUT_S = 900


def downbeat_phase(strengths: Sequence[float], beats_per_bar: int = BEATS_PER_BAR) -> int:
    """Indice (0..beats_per_bar-1) du temps qui porte le plus d'énergie d'attaque : le « 1 »."""
    if not strengths:
        return 0
    totals = [sum(strengths[phase::beats_per_bar]) / max(1, len(strengths[phase::beats_per_bar]))
              for phase in range(min(beats_per_bar, len(strengths)))]
    return max(range(len(totals)), key=totals.__getitem__)


def select_times(beats: list[float], phase: int, every: str) -> list[float]:
    if every == "beat":
        return beats
    if every == "half_bar":
        return [t for i, t in enumerate(beats) if i >= phase and (i - phase) % (BEATS_PER_BAR // 2) == 0]
    if every == "bar":
        return [t for i, t in enumerate(beats) if i >= phase and (i - phase) % BEATS_PER_BAR == 0]
    raise ToolError(f"every inconnu : {every} (beat, half_bar, bar).")


def analyze_sync(src: Path) -> dict[str, Any]:
    """Analyse complète (extraction ffmpeg + librosa). Tourne dans le processus worker."""
    import librosa
    import numpy as np

    with tempfile.TemporaryDirectory(prefix="fc-beats-") as tmp:
        wav = Path(tmp) / "music.wav"
        proc = subprocess.run([config.ffmpeg_exe(), "-nostdin", "-hide_banner", "-v", "error", "-i", str(src),
                               "-vn", "-ac", "1", "-ar", str(ANALYSIS_SAMPLE_RATE), "-y", str(wav)],
                              stdin=subprocess.DEVNULL, capture_output=True, check=False)
        if proc.returncode != 0:
            raise ToolError(f"Extraction audio impossible : {proc.stderr.decode('utf-8', 'replace').strip()[-400:]}")
        y, sr = librosa.load(str(wav), sr=ANALYSIS_SAMPLE_RATE, mono=True)
    onset_env = librosa.onset.onset_strength(y=y, sr=sr)
    tempo, frames = librosa.beat.beat_track(onset_envelope=onset_env, sr=sr)
    beat_times = librosa.frames_to_time(frames, sr=sr).tolist()
    strengths = onset_env[np.clip(frames, 0, len(onset_env) - 1)].tolist() if len(frames) else []
    bpm = float(np.atleast_1d(tempo)[0]) if np.size(tempo) else 0.0
    return {"bpm": bpm, "beats": [round(t, 3) for t in beat_times], "strengths": strengths,
            "duration": float(len(y) / sr)}


async def analyze(path: str) -> dict[str, Any]:
    src = require_file(path)
    result = await run_worker("beats", {"path": str(src)}, None, WORKER_TIMEOUT_S)
    if not result["beats"]:
        raise ToolError("Aucun temps détecté (morceau trop court, sans rythme ou silencieux).")
    phase = downbeat_phase(result["strengths"])
    return {**result, "downbeatPhase": phase, "bars": select_times(result["beats"], phase, "bar")}
