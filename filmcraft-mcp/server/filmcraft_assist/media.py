"""Analyse des rushes (ffprobe) et conformation en intermédiaire de montage à cadence fixe."""

from __future__ import annotations

from fractions import Fraction
from pathlib import Path
from typing import Any

from .proc import ProgressCallback, ToolError, ffmpeg_with_progress, ffprobe_json, require_file

STANDARD_RATES: tuple[Fraction, ...] = (
    Fraction(24000, 1001), Fraction(24), Fraction(25), Fraction(30000, 1001),
    Fraction(30), Fraction(50), Fraction(60000, 1001), Fraction(60),
)
# Écart relatif entre r_frame_rate et avg_frame_rate au-delà duquel on suspecte du VFR.
VFR_TOLERANCE = 0.0005
HDR_TRANSFERS = {"smpte2084": "PQ", "arib-std-b67": "HLG"}

CONFORM_CODECS: dict[str, list[str]] = {
    "prores_lt": ["-c:v", "prores_ks", "-profile:v", "1", "-vendor", "apl0", "-pix_fmt", "yuv422p10le"],
    "prores_hq": ["-c:v", "prores_ks", "-profile:v", "3", "-vendor", "apl0", "-pix_fmt", "yuv422p10le"],
    "dnxhr_hq": ["-c:v", "dnxhd", "-profile:v", "dnxhr_hq", "-pix_fmt", "yuv422p"],
    "h264_hq": ["-c:v", "libx264", "-preset", "slow", "-crf", "14", "-g", "12", "-pix_fmt", "yuv420p"],
}


def parse_rate(text: str | None) -> Fraction | None:
    if not text or text in ("0/0", "0"):
        return None
    try:
        rate = Fraction(text)
    except (ValueError, ZeroDivisionError):
        return None
    return rate if rate > 0 else None


def is_probably_vfr(r_rate: Fraction | None, avg_rate: Fraction | None) -> bool:
    if r_rate is None or avg_rate is None:
        return False
    return abs(float(r_rate - avg_rate)) / float(r_rate) > VFR_TOLERANCE


def nearest_standard_rate(rate: Fraction) -> Fraction:
    return min(STANDARD_RATES, key=lambda std: abs(float(std - rate)))


def target_rate(fps: float | None, source: Fraction | None) -> Fraction:
    """Cadence de conformation : 29.97 → 30000/1001 exactement (pas 2997/100), sinon la valeur demandée."""
    if fps is None:
        return nearest_standard_rate(source or Fraction(30))
    std = nearest_standard_rate(Fraction(fps))
    if abs(float(std) - fps) / fps < 0.001:
        return std
    return Fraction(fps).limit_denominator(1001)


def _rotation(stream: dict[str, Any]) -> int:
    for side in stream.get("side_data_list", []) or []:
        if "rotation" in side:
            return int(side["rotation"])
    tag = (stream.get("tags") or {}).get("rotate")
    return int(tag) if tag and tag.lstrip("-").isdigit() else 0


def summarize(path: Path, data: dict[str, Any]) -> dict[str, Any]:
    """Résumé compact d'un média + problèmes qui gênent un montage précis."""
    fmt = data.get("format", {})
    streams = data.get("streams", [])
    video = next((s for s in streams if s.get("codec_type") == "video"
                  and not (s.get("disposition") or {}).get("attached_pic")), None)
    audio = [s for s in streams if s.get("codec_type") == "audio"]
    issues: list[str] = []
    summary: dict[str, Any] = {
        "path": str(path),
        "container": fmt.get("format_name"),
        "durationSeconds": round(float(fmt.get("duration", 0) or 0), 3),
        "sizeMB": round(int(fmt.get("size", 0) or 0) / 1e6, 1),
        "bitrateMbps": round(int(fmt.get("bit_rate", 0) or 0) / 1e6, 2),
    }
    if video:
        r_rate = parse_rate(video.get("r_frame_rate"))
        avg_rate = parse_rate(video.get("avg_frame_rate"))
        transfer = video.get("color_transfer")
        vfr = is_probably_vfr(r_rate, avg_rate)
        summary["video"] = {
            "codec": video.get("codec_name"), "profile": video.get("profile"),
            "width": video.get("width"), "height": video.get("height"),
            "fps": round(float(avg_rate or r_rate or 0), 3),
            "probablyVFR": vfr, "pixFmt": video.get("pix_fmt"),
            "colorTransfer": transfer, "hdr": HDR_TRANSFERS.get(transfer or ""),
            "rotation": _rotation(video),
        }
        if vfr and (avg_rate or r_rate):
            target = nearest_standard_rate(avg_rate or r_rate)  # type: ignore[arg-type]
            issues.append(f"Cadence probablement variable (VFR, typique des téléphones) : conformer en "
                          f"{float(target):.3f} i/s avec media_conform pour des coupes à l'image près.")
        if summary["video"]["hdr"]:
            issues.append(f"Source HDR {summary['video']['hdr']} : régler l'espace de travail de la séquence "
                          "(sequence.colorSettings) ou exporter en SDR tone-mappé (file.exportMedia sdr=true).")
        if summary["video"]["rotation"]:
            issues.append(f"Rotation de {summary['video']['rotation']}° dans les métadonnées : vérifier le cadrage.")
    if audio:
        a = audio[0]
        summary["audio"] = {"codec": a.get("codec_name"), "sampleRate": int(a.get("sample_rate", 0) or 0),
                            "channels": a.get("channels"), "tracks": len(audio)}
        if summary["audio"]["sampleRate"] not in (0, 48000):
            issues.append(f"Audio à {summary['audio']['sampleRate']} Hz : la vidéo travaille en 48 kHz, "
                          "media_conform le rééchantillonne proprement.")
    summary["issues"] = issues
    return summary


async def probe(path: str) -> dict[str, Any]:
    p = require_file(path)
    return summarize(p, await ffprobe_json(p))


def _color_args(video: dict[str, Any]) -> list[str]:
    args: list[str] = []
    for key, flag in (("color_primaries", "-color_primaries"), ("color_transfer", "-color_trc"),
                      ("color_space", "-colorspace")):
        value = video.get(key)
        if value and value != "unknown":
            args += [flag, value]
    return args


async def conform(
    path: str, codec: str, fps: float | None, out_dir: str | None, on_progress: ProgressCallback | None
) -> dict[str, Any]:
    src = require_file(path)
    if codec not in CONFORM_CODECS:
        raise ToolError(f"Codec inconnu : {codec}. Choix : {', '.join(CONFORM_CODECS)}.")
    data = await ffprobe_json(src)
    info = summarize(src, data)
    video = next((s for s in data.get("streams", []) if s.get("codec_type") == "video"), None)
    if video is None:
        raise ToolError("Pas de piste vidéo à conformer.")
    source_rate = parse_rate(video.get("avg_frame_rate")) or parse_rate(video.get("r_frame_rate"))
    target = target_rate(fps, source_rate)
    dest_dir = Path(out_dir) if out_dir else src.parent
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / f"{src.stem}_cfr{target.numerator}-{target.denominator}_{codec}.mov"
    args = ["-y", "-i", str(src), "-map", "0:v:0", "-map", "0:a?", "-fps_mode", "cfr",
            "-r", f"{target.numerator}/{target.denominator}", *CONFORM_CODECS[codec], *_color_args(video),
            "-c:a", "pcm_s24le", "-ar", "48000", "-map_metadata", "0", str(dest)]
    await ffmpeg_with_progress(args, info["durationSeconds"], on_progress, timeout=6 * 3600)
    return {"source": str(src), "output": str(dest), "fps": f"{target.numerator}/{target.denominator}",
            "codec": codec, "sizeMB": round(dest.stat().st_size / 1e6, 1),
            "next": "Importer la sortie dans FilmCraft (media_import) à la place de l'original, "
                    "ou media.replaceFootage {item, path} pour garder le montage existant."}
