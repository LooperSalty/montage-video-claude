"""Planche contact : une image avec N vignettes horodatées, pour relire un montage d'un coup d'œil."""

from __future__ import annotations

import asyncio
import tempfile
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont

from . import config
from .proc import ToolError, ffprobe_json, require_file, run

MAX_PARALLEL_EXTRACTS = 4
LABEL_HEIGHT = 28
BACKGROUND = (18, 18, 20)
LABEL_COLOR = (235, 235, 235)


def sample_times(duration: float, count: int, start: float = 0.0, end: float | None = None) -> list[float]:
    """Instants régulièrement espacés au milieu de chaque tranche (jamais pile sur la fin)."""
    stop = min(end if end is not None else duration, duration)
    span = max(0.0, stop - start)
    if span <= 0 or count <= 0:
        return []
    step = span / count
    return [round(start + step * (i + 0.5), 3) for i in range(count)]


def media_duration(probe: dict[str, Any]) -> float:
    """Durée du conteneur, sinon la plus longue durée de flux (WebM de MediaRecorder, certains MKV)."""
    fmt = float((probe.get("format") or {}).get("duration", 0) or 0)
    if fmt > 0:
        return fmt
    streams = [float(s.get("duration", 0) or 0) for s in probe.get("streams", [])]
    return max(streams, default=0.0)


def timecode(seconds: float) -> str:
    m, s = divmod(seconds, 60)
    h, m = divmod(int(m), 60)
    return f"{h:d}:{m:02d}:{s:05.2f}" if h else f"{m:02d}:{s:05.2f}"


def _font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for name in ("segoeui.ttf", "arial.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


async def _extract(src: Path, t: float, width: int, out: Path, sem: asyncio.Semaphore) -> Path | None:
    async with sem:
        code, _, _ = await run([config.ffmpeg_exe(), "-nostdin", "-hide_banner", "-v", "error", "-ss", f"{t:.3f}",
                                "-i", str(src), "-frames:v", "1", "-vf", f"scale={width}:-2", "-y", str(out)],
                               timeout=120)
    return out if code == 0 and out.exists() else None


async def contact_sheet(path: str, count: int, columns: int, width: int, out_path: str | None,
                        start: float, end: float | None) -> dict[str, Any]:
    src = require_file(path)
    data = await ffprobe_json(src)
    duration = media_duration(data)
    times = sample_times(duration, count, start, end)
    if not times:
        raise ToolError("Plage vide : vérifier start/end et la durée du média.")
    columns = max(1, min(columns, len(times)))
    thumb_w = max(80, width // columns)
    sem = asyncio.Semaphore(MAX_PARALLEL_EXTRACTS)
    with tempfile.TemporaryDirectory(prefix="fc-sheet-") as tmp:
        frames = await asyncio.gather(*[
            _extract(src, t, thumb_w, Path(tmp) / f"f{i:03d}.png", sem) for i, t in enumerate(times)])
        images = [(t, Image.open(f).convert("RGB")) for t, f in zip(times, frames) if f]
        if not images:
            raise ToolError("Aucune image extraite (fichier sans vidéo ?).")
        thumb_h = images[0][1].height
        rows = -(-len(images) // columns)
        sheet = Image.new("RGB", (columns * thumb_w, rows * (thumb_h + LABEL_HEIGHT)), BACKGROUND)
        draw, font = ImageDraw.Draw(sheet), _font(16)
        for i, (t, img) in enumerate(images):
            x, y = (i % columns) * thumb_w, (i // columns) * (thumb_h + LABEL_HEIGHT)
            sheet.paste(img.resize((thumb_w, thumb_h)), (x, y))
            draw.text((x + 8, y + thumb_h + 5), f"#{i + 1}  {timecode(t)}", fill=LABEL_COLOR, font=font)
    dest = Path(out_path) if out_path else src.with_name(f"{src.stem}_planche.png")
    dest.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(dest)
    return {"image": str(dest), "frames": len(images), "times": times,
            "next": "Lire l'image (outil Read) pour juger rythme, cadrage, étalonnage et titres."}
