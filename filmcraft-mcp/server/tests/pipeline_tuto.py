"""Validation de la recette A (tuto face caméra) avec le CLI FilmCraft headless.

Usage : uv run python tests/pipeline_tuto.py <video.mp4> <transcript.json> <dossier_sortie>
Crée un projet, place la vidéo, pose la transcription, coupe les « euh » et les blancs, crée les
sous-titres, étalonne, nettoie la voix, exporte à -14 LUFS puis lance le contrôle qualité.
"""

from __future__ import annotations

import asyncio
import json
import subprocess
import sys
from pathlib import Path

from filmcraft_assist import qc, sheet
from filmcraft_assist.config import FILMCRAFT_CLI
from filmcraft_assist.transcribe import FILLERS


def cli(project: Path, *args: str, save: bool = True) -> object:
    cmd = [str(FILMCRAFT_CLI), "--compact", "--project", str(project), *(["--save"] if save else []), *args]
    out = subprocess.run(cmd, capture_output=True, stdin=subprocess.DEVNULL)
    text = out.stdout.decode("utf-8", "replace").strip()
    if out.returncode != 0:
        raise SystemExit(f"échec {args[:2]} : {out.stderr.decode('utf-8', 'replace')[-600:]} {text[-300:]}")
    return json.loads(text) if text.startswith(("{", "[")) else text


def run(project: Path, command: str, params: dict) -> object:
    result = cli(project, "exec", command, json.dumps(params, ensure_ascii=False))
    print(f"{command}: {json.dumps(result, ensure_ascii=False)[:200]}")
    return result


def clips(project: Path, kind: str) -> list[int]:
    seq = cli(project, "inspect", "sequence", save=False)
    return [c["clip"] for track in seq[kind] for c in track["items"]]  # type: ignore[index]


def main(video: str, transcript_json: str, out_dir: str) -> None:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    project = out / "tuto_test.fcproj"
    subprocess.run([str(FILMCRAFT_CLI), "--compact", "--save-as", str(project), "exec", "file.newSequence",
                    json.dumps({"name": "Tuto", "width": 1280, "height": 720, "fps": 30, "sampleRate": 48000})],
                   check=True, capture_output=True, stdin=subprocess.DEVNULL)
    run(project, "file.import", {"paths": [video]})
    status = cli(project, "exec", "media.status", save=False)
    item = next(e["item"] for e in status if e.get("path") and Path(e["path"]).name == Path(video).name)  # type: ignore[union-attr]
    run(project, "timeline.place", {"item": item, "track": "V1", "seconds": 0})
    transcript = json.loads(Path(transcript_json).read_text(encoding="utf-8"))
    run(project, "transcript.set", {"item": item, "transcript": transcript})
    run(project, "transcript.removeFillers", {"fillers": FILLERS["fr"]})
    run(project, "transcript.removePauses", {"minSeconds": 0.6, "keepSeconds": 0.15})
    run(project, "transcript.createCaptions", {"maxChars": 42, "lines": 2})
    for clip in clips(project, "video"):
        run(project, "effects.apply", {"clips": [clip], "effect": "lumetri"})
        for param, value in (("contrast", 12), ("saturation", 110), ("vibrance", 10)):
            run(project, "effects.setParam", {"clip": clip, "effect": "lumetri", "param": param, "value": value})
    run(project, "essentialSound.applyPreset", {"clips": clips(project, "audio"), "preset": "Clean Up Noisy Dialogue",
                                                "type": "dialogue"})
    export = out / "tuto_test.mp4"
    run(project, "file.exportMedia", {"path": str(export), "format": "h264", "loudnessLufs": -14,
                                      "burnCaptions": True, "wait": True})
    report = asyncio.run(qc.export_qc(str(export), "youtube"))
    print("QC :", report["verdict"], report["measures"], [c["check"] for c in report["checks"] if c["status"] != "ok"])
    sheet_result = asyncio.run(sheet.contact_sheet(str(export), 8, 4, 1280, None, 0.0, None))
    print("planche :", sheet_result["image"], "durée export :", report["file"]["durationSeconds"], "s")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main(*sys.argv[1:4])
