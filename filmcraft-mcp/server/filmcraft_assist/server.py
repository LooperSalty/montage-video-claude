"""Serveur MCP « filmcraft_assist » : les outils d'analyse qui manquent à FilmCraft.

Le MCP officiel `filmcraft` pilote l'appli (650+ commandes). Celui-ci ajoute ce qu'elle ne sait
pas faire, ou mal : transcription Whisper large sur GPU, beats musicaux, contrôle qualité
d'export, planches contact, conformation VFR → CFR. Les gros volumes (mots, marqueurs) partent
directement dans FilmCraft par le canal de contrôle au lieu de passer par la conversation.
"""

from __future__ import annotations

import asyncio
import json
import time
from pathlib import Path
from typing import Annotated, Any, Awaitable, Callable, Literal, TypeVar

from mcp.server.fastmcp import Context, FastMCP
from mcp.server.fastmcp.exceptions import ToolError as McpToolError
from mcp.types import ToolAnnotations
from pydantic import Field

from . import beats, bridge, media, qc, sheet, transcribe
from .config import CHARACTER_LIMIT
from .control import FilmCraftError
from .proc import ToolError, require_file, run_worker

mcp = FastMCP("filmcraft_assist")
T = TypeVar("T")
TRANSCRIBE_TIMEOUT_S = 4 * 3600

READ_ONLY = ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=False)
WRITES_FILES = ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=True, openWorldHint=False)
EDITS_PROJECT = ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=False, openWorldHint=False)


async def _guard(work: Awaitable[T]) -> T:
    """Convertit les erreurs connues en erreurs d'outil lisibles."""
    try:
        return await work
    except (FilmCraftError, ToolError, FileNotFoundError) as exc:
        raise McpToolError(str(exc)) from exc


def _progress(ctx: Context | None) -> Callable[[float], Awaitable[None]] | None:
    if ctx is None:
        return None

    async def report(fraction: float) -> None:
        await ctx.report_progress(round(fraction * 100, 1), 100)
    return report


def _clip(data: dict[str, Any]) -> dict[str, Any]:
    text = json.dumps(data, ensure_ascii=False)
    if len(text) > CHARACTER_LIMIT:
        data = {**data, "truncated": True}
        for key in ("times", "beats", "bars"):
            if isinstance(data.get(key), list):
                data[key] = data[key][:64]
    return data


@mcp.tool(name="filmcraft_status", annotations=READ_ONLY)
async def filmcraft_status() -> dict[str, Any]:
    """État de l'installation FilmCraft : installée ?, lancée avec le canal de contrôle ?, projet ouvert.

    À appeler en premier. Si running=false, lancer FilmCraft avec filmcraft_launch.
    Renvoie {installDir, installed, tokenFile, port, running, ffmpeg, project?: {name, path, dirty, activeSequence}}.
    """
    return await _guard(bridge.status())


@mcp.tool(name="filmcraft_launch", annotations=EDITS_PROJECT)
async def filmcraft_launch(
    files: Annotated[list[str] | None, Field(description="Chemins absolus à ouvrir : un .fcproj et/ou des médias. Vide = projet par défaut.", max_length=50)] = None,
    wait_seconds: Annotated[float, Field(ge=1, le=120, description="Attente max du canal de contrôle.")] = 30,
) -> dict[str, Any]:
    """Lance FilmCraft (ou réutilise l'instance ouverte) avec le canal de contrôle, puis attend qu'il réponde.

    Après ça, le MCP `filmcraft` (command_run, sequence_inspect, ui_screenshot…) peut piloter l'appli.
    """
    return await _guard(bridge.launch([str(Path(f)) for f in files or []], wait_seconds))


@mcp.tool(name="media_probe", annotations=READ_ONLY)
async def media_probe(
    paths: Annotated[list[str], Field(min_length=1, max_length=30, description="Chemins absolus des rushes.")],
) -> dict[str, Any]:
    """Analyse des rushes avant montage : codec, résolution, cadence, VFR, HDR, rotation, audio.

    `issues` liste ce qui gênera un montage précis (VFR de téléphone, HDR, 44,1 kHz…) et l'outil
    qui le corrige. Renvoie {files: [{path, container, durationSeconds, video, audio, issues}], errors}.
    """
    results = await asyncio.gather(*[media.probe(p) for p in paths], return_exceptions=True)
    files = [r for r in results if isinstance(r, dict)]
    errors = [f"{p}: {r}" for p, r in zip(paths, results) if isinstance(r, Exception)]
    return _clip({"files": files, "errors": errors})


@mcp.tool(name="media_conform", annotations=WRITES_FILES)
async def media_conform(
    path: Annotated[str, Field(description="Chemin absolu du rush (souvent un MP4/MOV de téléphone en VFR).")],
    codec: Annotated[Literal["prores_lt", "prores_hq", "dnxhr_hq", "h264_hq"], Field(description="prores_lt = qualité visuellement sans perte, taille raisonnable.")] = "prores_lt",
    fps: Annotated[float | None, Field(gt=0, le=240, description="Cadence cible (29.97, 25…). Défaut : la cadence standard la plus proche.")] = None,
    out_dir: Annotated[str | None, Field(description="Dossier de sortie. Défaut : à côté du fichier source.")] = None,
    ctx: Context | None = None,
) -> dict[str, Any]:
    """Convertit un rush en intermédiaire de montage à cadence FIXE (CFR) + audio PCM 48 kHz.

    À utiliser quand media_probe signale du VFR : coupes à l'image près, synchro son stable, lecture
    fluide. Garde les métadonnées de couleur (HDR inclus). Renvoie {source, output, fps, codec, sizeMB, next}.
    """
    return await _guard(media.conform(path, codec, fps, out_dir, _progress(ctx)))


@mcp.tool(name="transcribe_media", annotations=EDITS_PROJECT)
async def transcribe_media(
    path: Annotated[str, Field(description="Chemin absolu du média (vidéo ou audio) à transcrire.")],
    language: Annotated[str | None, Field(description="Code ISO 639-1 (fr, en…). None = détection auto.")] = "fr",
    model: Annotated[str, Field(description="Modèle faster-whisper : large-v3-turbo (rapide, très bon), large-v3 (max), medium, small.")] = transcribe.DEFAULT_MODEL,
    keep_fillers: Annotated[bool, Field(description="Transcrire les hésitations (euh, hum) pour pouvoir les couper ensuite.")] = True,
    apply_to_filmcraft: Annotated[bool, Field(description="Envoyer la transcription mot à mot dans FilmCraft (transcript.set) pour les éléments du projet qui pointent sur ce fichier.")] = True,
    import_if_missing: Annotated[bool, Field(description="Importer le média dans le projet s'il n'y est pas.")] = False,
    max_chars: Annotated[int, Field(ge=12, le=80, description="Caractères max par ligne de sous-titre SRT (42 = norme TV, 20-28 pour un short vertical).")] = 42,
    max_lines: Annotated[int, Field(ge=1, le=3)] = 2,
    out_dir: Annotated[str | None, Field(description="Dossier des sorties .srt / .transcript.json. Défaut : à côté du média.")] = None,
    ctx: Context | None = None,
) -> dict[str, Any]:
    """Transcrit mot à mot avec Whisper large sur le GPU (bien meilleur que le whisper-base intégré à FilmCraft).

    Écrit <nom>.srt et <nom>.transcript.json et, si FilmCraft tourne, pose la transcription sur le
    média : le montage par le texte de FilmCraft devient utilisable (transcript.removeFillers,
    transcript.removePauses, transcript.createCaptions, transcript.search).
    Renvoie {language, durationSeconds, words, cues, fillers, srt, transcriptJson, filmcraft, preview, next}.
    """
    return await _guard(_transcribe(path, language, model, keep_fillers, apply_to_filmcraft,
                                    import_if_missing, max_chars, max_lines, out_dir, ctx))


async def _transcribe(path: str, language: str | None, model: str, keep_fillers: bool, apply: bool,
                      import_if_missing: bool, max_chars: int, max_lines: int, out_dir: str | None,
                      ctx: Context | None) -> dict[str, Any]:
    src = require_file(path)
    started = time.monotonic()
    result = await run_worker("transcribe", {"path": str(src), "language": language, "model": model,
                                             "keep_fillers": keep_fillers},
                              _progress(ctx), TRANSCRIBE_TIMEOUT_S)
    words = [transcribe.Word(*w) for w in result["words"]]
    lang = result["language"]
    dest = Path(out_dir) if out_dir else src.parent
    dest.mkdir(parents=True, exist_ok=True)
    cues = transcribe.build_cues(words, max_chars, max_lines, max_seconds=6.0, max_gap=0.6)
    srt_path, json_path = dest / f"{src.stem}.srt", dest / f"{src.stem}.transcript.json"
    srt_path.write_text(transcribe.to_srt(cues), encoding="utf-8")
    fc_transcript = transcribe.to_filmcraft(words, lang, model)
    json_path.write_text(json.dumps(fc_transcript, ensure_ascii=False), encoding="utf-8")
    applied: dict[str, Any] = {"skipped": "apply_to_filmcraft=false"}
    if apply:
        try:
            applied = await bridge.apply_transcript(str(src), fc_transcript, import_if_missing)
        except FilmCraftError as exc:
            applied = {"error": str(exc)}
    fillers = transcribe.count_fillers(words, lang)
    filler_list = transcribe.FILLERS.get(lang, [])
    return {
        "language": lang, "durationSeconds": round(result["duration"], 2), "device": result["device"],
        "model": model, "elapsedSeconds": round(time.monotonic() - started, 1),
        "words": len(words), "cues": len(cues), "fillers": fillers,
        "srt": str(srt_path), "transcriptJson": str(json_path), "filmcraft": applied,
        "preview": " ".join(w.text for w in words)[:600],
        "next": [
            f"Couper les hésitations (clip dans la séquence active) : command_run transcript.removeFillers {{\"fillers\": {json.dumps(filler_list, ensure_ascii=False)}}}",
            "Resserrer les pauses : command_run transcript.removePauses {\"minSeconds\": 0.6, \"keepSeconds\": 0.15}",
            f"Sous-titres : command_run transcript.createCaptions {{\"maxChars\": {max_chars}, \"lines\": {max_lines}}} ou captions.import {{\"path\": srt}}",
        ],
    }


@mcp.tool(name="music_beats", annotations=EDITS_PROJECT)
async def music_beats(
    path: Annotated[str, Field(description="Chemin absolu de la musique (ou d'une vidéo avec musique).")],
    add_markers: Annotated[bool, Field(description="Poser des marqueurs de séquence dans FilmCraft sur les temps choisis.")] = False,
    every: Annotated[Literal["beat", "half_bar", "bar"], Field(description="Densité des marqueurs : chaque temps, chaque demi-mesure ou chaque mesure.")] = "bar",
    offset_seconds: Annotated[float, Field(ge=0, description="Position dans la séquence où commence la musique (s), ajoutée à chaque marqueur.")] = 0.0,
    color: Annotated[str | None, Field(description="Couleur/étiquette FilmCraft des marqueurs (ex. Mango, Forest). None = défaut.")] = None,
) -> dict[str, Any]:
    """Tempo (BPM), temps et débuts de mesure d'une musique, pour caler les coupes sur le rythme.

    Avec add_markers=true, pose les marqueurs dans la séquence active (Marqueurs ▸ aller au suivant
    pour couper dessus). Renvoie {bpm, durationSeconds, beatCount, downbeatPhase, bars, times, markers?}.
    """
    return await _guard(_beats(path, add_markers, every, offset_seconds, color))


async def _beats(path: str, add: bool, every: str, offset: float, color: str | None) -> dict[str, Any]:
    result = await beats.analyze(path)
    times = beats.select_times(result["beats"], result["downbeatPhase"], every)
    out: dict[str, Any] = {"bpm": round(result["bpm"], 1), "durationSeconds": round(result["duration"], 2),
                           "beatCount": len(result["beats"]), "downbeatPhase": result["downbeatPhase"],
                           "every": every, "times": times}
    if add:
        label = {"beat": "Temps", "half_bar": "Demi", "bar": "Mesure"}[every]
        out["markers"] = await bridge.add_markers(times, offset, label, color)
    return _clip(out)


@mcp.tool(name="export_qc", annotations=READ_ONLY)
async def export_qc(
    path: Annotated[str, Field(description="Chemin absolu de la vidéo exportée à contrôler.")],
    platform: Annotated[Literal["youtube", "tiktok", "instagram", "podcast", "broadcast"], Field(description="Cible de loudness : youtube/tiktok/instagram -14 LUFS, podcast -16, broadcast EBU R128 -23.")] = "youtube",
) -> dict[str, Any]:
    """Contrôle qualité d'un export avant publication : loudness intégrée, true peak, noirs, images figées, silences.

    Chaque contrôle raté indique la correction à faire dans FilmCraft.
    Renvoie {file, platform, verdict: OK|À CORRIGER, checks: [{check, status, detail, fix?}], measures}.
    """
    return await _guard(qc.export_qc(path, platform))


@mcp.tool(name="contact_sheet", annotations=WRITES_FILES)
async def contact_sheet(
    path: Annotated[str, Field(description="Chemin absolu d'une vidéo (rush ou export).")],
    count: Annotated[int, Field(ge=1, le=60, description="Nombre de vignettes.")] = 12,
    columns: Annotated[int, Field(ge=1, le=10)] = 4,
    width: Annotated[int, Field(ge=320, le=3840, description="Largeur totale de la planche en pixels.")] = 1600,
    out_path: Annotated[str | None, Field(description="PNG de sortie. Défaut : <nom>_planche.png à côté de la vidéo.")] = None,
    start: Annotated[float, Field(ge=0, description="Début de la plage (s).")] = 0.0,
    end: Annotated[float | None, Field(gt=0, description="Fin de la plage (s). Défaut : fin du média.")] = None,
) -> dict[str, Any]:
    """Planche contact horodatée d'une vidéo : relire tout un montage en une image (puis l'ouvrir avec Read).

    Renvoie {image, frames, times, next}.
    """
    return await _guard(sheet.contact_sheet(path, count, columns, width, out_path, start, end))


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
