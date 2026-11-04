"""Contrôle qualité d'un export : loudness EBU R128, true peak, noirs, images figées, silences."""

from __future__ import annotations

import re
from typing import Any

from . import config
from .media import summarize
from .proc import ToolError, ffprobe_json, require_file, run

# Cibles de loudness intégrée (LUFS) et de true peak max (dBTP) par plateforme.
PLATFORM_TARGETS: dict[str, tuple[float, float]] = {
    "youtube": (-14.0, -1.0),
    "tiktok": (-14.0, -1.0),
    "instagram": (-14.0, -1.0),
    "podcast": (-16.0, -1.0),
    "broadcast": (-23.0, -1.0),
}
LOUDNESS_TOLERANCE_LU = 1.0
EDGE_MARGIN_S = 0.1  # un noir qui touche le début ou la fin de la vidéo…
FADE_MAX_S = 1.5     # …et dure au plus ça est un fondu d'ouverture/fermeture, pas un défaut


def suspicious_blacks(blacks: list[list[float]], duration: float) -> list[list[float]]:
    """Noirs à signaler : tous ceux du milieu, et ceux des bords plus longs qu'un fondu."""
    out = []
    for start, end in blacks:
        at_edge = start <= EDGE_MARGIN_S or end >= duration - EDGE_MARGIN_S
        if not at_edge or end - start > FADE_MAX_S:
            out.append([start, end])
    return out

_I_RE = re.compile(r"Integrated loudness:\s*\n\s*I:\s*(-?[\d.]+|-inf) LUFS")
_LRA_RE = re.compile(r"Loudness range:\s*\n\s*LRA:\s*([\d.]+) LU")
_TP_RE = re.compile(r"True peak:\s*\n\s*Peak:\s*(-?[\d.]+|-inf) dBFS")
_BLACK_RE = re.compile(r"black_start:\s*([\d.]+)\s+black_end:\s*([\d.]+)")
_FREEZE_START_RE = re.compile(r"freeze_start:\s*([\d.]+)")
_FREEZE_END_RE = re.compile(r"freeze_end:\s*([\d.]+)")
_SIL_START_RE = re.compile(r"silence_start:\s*(-?[\d.]+)")
_SIL_END_RE = re.compile(r"silence_end:\s*([\d.]+)")


def _float(m: re.Match[str] | None) -> float | None:
    if not m:
        return None
    return float("-inf") if m.group(1) == "-inf" else float(m.group(1))


def _pairs(starts: list[str], ends: list[str], duration: float) -> list[list[float]]:
    out = []
    for i, s in enumerate(starts):
        start = max(0.0, float(s))
        end = float(ends[i]) if i < len(ends) else duration
        out.append([round(start, 2), round(end, 2)])
    return out


def parse_report(stderr: str, duration: float) -> dict[str, Any]:
    """Extrait les mesures du stderr de ffmpeg (ebur128, blackdetect, freezedetect, silencedetect)."""
    summary = stderr[stderr.rfind("Summary:"):] if "Summary:" in stderr else ""
    blacks = [[round(float(a), 2), round(float(b), 2)] for a, b in _BLACK_RE.findall(stderr)]
    return {
        "integratedLufs": _float(_I_RE.search(summary)),
        "loudnessRangeLu": _float(_LRA_RE.search(summary)),
        "truePeakDbtp": _float(_TP_RE.search(summary)),
        "black": blacks,
        "frozen": _pairs(_FREEZE_START_RE.findall(stderr), _FREEZE_END_RE.findall(stderr), duration),
        "silence": _pairs(_SIL_START_RE.findall(stderr), _SIL_END_RE.findall(stderr), duration),
    }


def evaluate(report: dict[str, Any], platform: str, duration: float) -> list[dict[str, str]]:
    target, max_tp = PLATFORM_TARGETS[platform]
    checks: list[dict[str, str]] = []

    def add(name: str, ok: bool, detail: str, fix: str = "") -> None:
        checks.append({"check": name, "status": "ok" if ok else "à corriger", "detail": detail, **({"fix": fix} if fix and not ok else {})})

    lufs, tp = report["integratedLufs"], report["truePeakDbtp"]
    if lufs is not None:
        add("loudness", abs(lufs - target) <= LOUDNESS_TOLERANCE_LU, f"{lufs:.1f} LUFS (cible {target:.0f} ±1)",
            f"Ré-exporter avec file.exportMedia loudnessLufs={target:.0f}.")
    if tp is not None:
        add("true peak", tp <= max_tp, f"{tp:.1f} dBTP (max {max_tp:.0f})",
            "Ajouter un limiteur true peak sur la piste Mix (mixer.addInsert) ou baisser le gain.")
    blacks = suspicious_blacks(report["black"], duration)
    add("noirs", not blacks, f"{len(blacks)} passage(s) noir(s) suspect(s) {blacks[:5]}",
        "Vérifier les trous dans la timeline (sequence_inspect) : edit.closeGap / ripple delete.")
    add("images figées", not report["frozen"], f"{len(report['frozen'])} plan(s) figé(s) ≥ 2 s {report['frozen'][:5]}",
        "Plan fixe voulu ? Sinon média hors ligne ou clip trop court (renderer qui tient la dernière image).")
    long_sil = [s for s in report["silence"] if s[1] - s[0] >= 2.0]
    add("silences", not long_sil, f"{len(long_sil)} silence(s) ≥ 2 s {long_sil[:5]}",
        "Silence voulu ? Sinon piste audio coupée/mutée ou musique trop courte.")
    return checks


async def export_qc(path: str, platform: str) -> dict[str, Any]:
    if platform not in PLATFORM_TARGETS:
        raise ToolError(f"Plateforme inconnue : {platform}. Choix : {', '.join(PLATFORM_TARGETS)}.")
    src = require_file(path)
    info = summarize(src, await ffprobe_json(src))
    duration = info["durationSeconds"]
    has_v, has_a = "video" in info, "audio" in info
    graph = []
    if has_v:
        graph.append("[0:v]blackdetect=d=0.5:pix_th=0.10,freezedetect=n=-60dB:d=2[v]")
    if has_a:
        graph.append("[0:a]ebur128=peak=true:framelog=verbose,silencedetect=n=-50dB:d=2[a]")
    if not graph:
        raise ToolError("Ni vidéo ni audio dans ce fichier.")
    maps = (["-map", "[v]"] if has_v else []) + (["-map", "[a]"] if has_a else [])
    code, _, err = await run([config.ffmpeg_exe(), "-nostdin", "-hide_banner", "-nostats", "-i", str(src),
                              "-filter_complex", ";".join(graph), *maps, "-f", "null", "-"], timeout=3600)
    if code != 0:
        raise ToolError(f"Analyse ffmpeg échouée : {err.strip()[-500:]}")
    report = parse_report(err, duration)
    checks = evaluate(report, platform, duration)
    return {
        "file": info,
        "platform": platform,
        "verdict": "OK" if all(c["status"] == "ok" for c in checks) else "À CORRIGER",
        "checks": checks,
        "measures": {k: report[k] for k in ("integratedLufs", "loudnessRangeLu", "truePeakDbtp")},
    }
