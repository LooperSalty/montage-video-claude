"""Transcription mot à mot avec faster-whisper (GPU CUDA si dispo) et sorties FilmCraft / SRT."""

from __future__ import annotations

import os
import subprocess
import sys
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from .config import ffmpeg_exe, seconds_to_ticks
from .proc import ToolError

DEFAULT_MODEL = "large-v3-turbo"
WHISPER_SAMPLE_RATE = 16000
# Un prompt initial plein d'hésitations pousse Whisper à transcrire les « euh » au lieu de les
# gommer : FilmCraft peut ensuite les couper (transcript.removeFillers).
FILLER_PROMPTS = {
    "fr": "Euh, alors... hum, bon, euh, en fait, bah, voilà, euh, je pense que, hein.",
    "en": "Um, so... uh, well, um, you know, like, uh, I mean, hmm.",
}
FILLERS = {
    "fr": ["euh", "heu", "euhm", "hum", "hmm", "mmh", "bah", "ben", "beh", "hein"],
    "en": ["um", "uh", "umm", "uhm", "erm", "er", "ah", "hmm", "mm", "mhm"],
}
SENTENCE_END = (".", "!", "?", "…")
JOINERS = ("'", "’", "-")


@dataclass(frozen=True)
class Word:
    text: str
    start: float
    end: float
    probability: float


_models: dict[tuple[str, str], Any] = {}
_models_lock = threading.Lock()


def _add_cuda_dll_dirs() -> None:
    """Rend visibles les DLL cuBLAS / cuDNN installées par pip (paquets nvidia-*) sous Windows."""
    if sys.platform != "win32":
        return
    nvidia_root = Path(sys.prefix) / "Lib" / "site-packages" / "nvidia"
    for bin_dir in nvidia_root.glob("*/bin"):
        os.add_dll_directory(str(bin_dir))
        os.environ["PATH"] = str(bin_dir) + os.pathsep + os.environ.get("PATH", "")


def load_model(name: str, force_cpu: bool = False) -> tuple[Any, str]:
    """Charge le modèle une seule fois ; CUDA float16 si possible, sinon CPU int8."""
    _add_cuda_dll_dirs()
    import ctranslate2
    from faster_whisper import WhisperModel

    device = "cuda" if not force_cpu and ctranslate2.get_cuda_device_count() > 0 else "cpu"
    key = (name, device)
    with _models_lock:
        if key not in _models:
            compute = "float16" if device == "cuda" else "int8"
            _models[key] = WhisperModel(name, device=device, compute_type=compute)
        return _models[key], device


def load_audio(path: Path) -> Any:
    """Décode n'importe quel média en mono 16 kHz float32 avec ffmpeg 8.

    faster-whisper décode normalement avec PyAV, mais les versions récentes de PyAV ont cassé
    son appel (`metadata_errors`) ; ffmpeg lit aussi plus de formats.
    """
    import numpy as np

    proc = subprocess.run(
        [ffmpeg_exe(), "-nostdin", "-hide_banner", "-v", "error", "-i", str(path), "-vn",
         "-ac", "1", "-ar", str(WHISPER_SAMPLE_RATE), "-f", "f32le", "-"],
        stdin=subprocess.DEVNULL, capture_output=True, check=False)
    if proc.returncode != 0 or not proc.stdout:
        raise ToolError(f"Décodage audio impossible : {proc.stderr.decode('utf-8', 'replace').strip()[-400:]}")
    return np.frombuffer(proc.stdout, dtype=np.float32)


def transcribe_words(path: Path, language: str | None, model_name: str, keep_fillers: bool,
                     on_progress: Callable[[float], None] | None = None) -> dict[str, Any]:
    audio = load_audio(path)
    try:
        return _transcribe(audio, language, model_name, keep_fillers, on_progress, force_cpu=False)
    except RuntimeError as exc:
        # DLL cuBLAS/cuDNN absente ou VRAM pleine : l'erreur sort souvent pendant le décodage.
        if not any(k in str(exc).lower() for k in ("cuda", "cublas", "cudnn", "out of memory")):
            raise
        result = _transcribe(audio, language, model_name, keep_fillers, on_progress, force_cpu=True)
        return {**result, "gpuError": str(exc)[:300]}


def _transcribe(audio: Any, language: str | None, model_name: str, keep_fillers: bool,
                on_progress: Callable[[float], None] | None, force_cpu: bool) -> dict[str, Any]:
    model, device = load_model(model_name, force_cpu)
    prompt = FILLER_PROMPTS.get(language or "") if keep_fillers else None
    segments, info = model.transcribe(
        audio, language=language, word_timestamps=True, vad_filter=True,
        initial_prompt=prompt, condition_on_previous_text=False, beam_size=5)
    raw: list[Word] = []
    for seg in segments:
        for w in seg.words or []:
            text = w.word.strip()
            if text:
                raw.append(Word(text, float(w.start), float(w.end), float(w.probability)))
        if on_progress and info.duration:
            on_progress(min(1.0, seg.end / info.duration))
    return {"words": merge_split_words(raw), "language": info.language, "duration": float(info.duration),
            "device": device, "model": model_name}


def merge_split_words(words: list[Word]) -> list[Word]:
    """Recolle les élisions et composés que Whisper découpe : « aujourd » + « 'hui », « sous » + « -titres »."""
    merged: list[Word] = []
    for w in words:
        glued = w.text.startswith(JOINERS) and w.text[1:2].isalpha()  # « 'hui », pas un tiret isolé
        if merged and glued and merged[-1].text[-1:].isalpha():
            prev = merged[-1]
            merged[-1] = Word(prev.text + w.text, prev.start, w.end, min(prev.probability, w.probability))
        else:
            merged.append(w)
    return merged


def to_filmcraft(words: list[Word], language: str, model_name: str) -> dict[str, Any]:
    """Transcription au format de `transcript.set` : temps média en ticks, mots sans chevauchement."""
    out: list[dict[str, Any]] = []
    for w in words:
        start, end = seconds_to_ticks(w.start), seconds_to_ticks(w.end)
        if out and out[-1]["end"] > start:
            out[-1]["end"] = max(out[-1]["start"], start)
        out.append({"text": w.text, "start": start, "end": max(start, end),
                    "confidence": round(min(1.0, max(0.0, w.probability)), 3)})
    return {"language": language, "source": f"faster-whisper-{model_name}", "speakers": [], "words": out}


def count_fillers(words: list[Word], language: str) -> dict[str, int]:
    fillers = set(FILLERS.get(language, []))
    counts: dict[str, int] = {}
    for w in words:
        key = w.text.strip(".,!?…;:\"'«» ").lower()
        if key in fillers:
            counts[key] = counts.get(key, 0) + 1
    return counts


def build_cues(words: list[Word], max_chars: int, max_lines: int, max_seconds: float,
               max_gap: float) -> list[tuple[float, float, str]]:
    """Regroupe les mots en sous-titres : coupe sur ponctuation finale, pause, longueur ou durée."""
    cues: list[tuple[float, float, str]] = []
    current: list[Word] = []

    def flush() -> None:
        if current:
            cues.append((current[0].start, current[-1].end,
                         _wrap([w.text for w in current], max_chars, max_lines)))
            current.clear()

    for w in words:
        if current:
            too_long = _lines_needed([x.text for x in current] + [w.text], max_chars) > max_lines
            if (w.start - current[-1].end > max_gap or too_long
                    or w.end - current[0].start > max_seconds):
                flush()
        current.append(w)
        if w.text.endswith(SENTENCE_END):
            flush()
    flush()
    return cues


def _greedy_lines(texts: list[str], max_chars: int) -> list[str]:
    lines: list[str] = []
    for t in texts:
        if lines and len(lines[-1]) + 1 + len(t) <= max_chars:
            lines[-1] = f"{lines[-1]} {t}"
        else:
            lines.append(t)
    return lines


def _lines_needed(texts: list[str], max_chars: int) -> int:
    return len(_greedy_lines(texts, max_chars))


def _wrap(texts: list[str], max_chars: int, max_lines: int) -> str:
    """Une ligne si possible ; sinon deux lignes équilibrées (ou remplissage glouton au-delà)."""
    text = " ".join(texts)
    if len(text) <= max_chars:
        return text
    if max_lines != 2:
        return "\n".join(_greedy_lines(texts, max_chars))
    best, best_score = text, float("inf")
    for i in range(1, len(texts)):
        a, b = " ".join(texts[:i]), " ".join(texts[i:])
        score = abs(len(a) - len(b)) + (1000 if max(len(a), len(b)) > max_chars else 0)
        if score < best_score:
            best, best_score = f"{a}\n{b}", score
    return best


def _srt_time(seconds: float) -> str:
    ms = max(0, round(seconds * 1000))
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def to_srt(cues: list[tuple[float, float, str]]) -> str:
    blocks = [f"{i}\n{_srt_time(a)} --> {_srt_time(b)}\n{text}\n" for i, (a, b, text) in enumerate(cues, 1)]
    return "\n".join(blocks)
