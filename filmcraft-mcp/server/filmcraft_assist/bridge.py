"""Opérations FilmCraft composées : lancement, état, recherche de médias, envoi en masse."""

from __future__ import annotations

import asyncio
import os
import subprocess
from pathlib import Path
from typing import Any

from . import config
from .control import Connection, FilmCraftError, connect, is_running

MAX_MARKERS = 1000
LAUNCH_POLL_S = 0.5


def same_path(a: str | None, b: str) -> bool:
    if not a:
        return False
    return os.path.normcase(os.path.abspath(a)) == os.path.normcase(os.path.abspath(b))


async def launch(files: list[str], wait_seconds: float) -> dict[str, Any]:
    if not config.LAUNCHER.exists():
        raise FilmCraftError(f"Lanceur introuvable : {config.LAUNCHER}. Recompiler filmcraft-mcp/launcher.")
    already = await is_running()
    # Aucun flux hérité : les journaux de FilmCraft corrompraient le canal JSON-RPC du MCP.
    subprocess.Popen([str(config.LAUNCHER), *files], close_fds=True,
                     stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                     creationflags=getattr(subprocess, "DETACHED_PROCESS", 0))
    if already:
        return {"running": True, "started": False, "note": "FilmCraft tournait déjà : fichiers ouverts dans l'instance existante."}
    loop = asyncio.get_running_loop()
    deadline = loop.time() + wait_seconds
    while loop.time() < deadline:
        if await is_running():
            return {"running": True, "started": True, "port": config.CONTROL_PORT}
        await asyncio.sleep(LAUNCH_POLL_S)
    raise FilmCraftError(f"FilmCraft ne répond pas après {wait_seconds:.0f} s. Voir le journal : "
                         f"{config.FILMCRAFT_DIR / 'data' / 'Logs' / 'filmcraft.log'}")


async def status() -> dict[str, Any]:
    result: dict[str, Any] = {
        "installDir": str(config.FILMCRAFT_DIR),
        "installed": config.FILMCRAFT_CLI.exists(),
        "tokenFile": config.TOKEN_FILE.exists(),
        "port": config.CONTROL_PORT,
        "running": await is_running(),
    }
    try:
        result["ffmpeg"] = config.ffmpeg_exe()
    except FileNotFoundError as exc:
        result["ffmpeg"] = str(exc)
    if result["running"] and result["tokenFile"]:
        try:
            async with connect() as conn:
                project = await conn.execute("project.inspect") or {}
            result["project"] = {"name": project.get("name"), "path": project.get("path"),
                                 "dirty": project.get("dirty"), "activeSequence": project.get("activeSequence")}
        except FilmCraftError as exc:  # diagnostic, pas plantage : c'est l'outil appelé en premier
            result["projectError"] = (f"{exc} — FilmCraft a peut-être été lancé sans le raccourci "
                                      "(pas de canal de contrôle) : le fermer puis filmcraft_launch.")
    return result


async def find_items(conn: Connection, path: str) -> list[int]:
    entries = await conn.execute("media.status")
    return [e["item"] for e in entries or [] if same_path(e.get("path"), path)]


async def ensure_items(conn: Connection, path: str, import_if_missing: bool) -> list[int]:
    items = await find_items(conn, path)
    if items or not import_if_missing:
        return items
    await conn.execute("file.import", {"paths": [str(Path(path))]})
    return await find_items(conn, path)


async def apply_transcript(path: str, transcript: dict[str, Any], import_if_missing: bool) -> dict[str, Any]:
    async with connect() as conn:
        items = await ensure_items(conn, path, import_if_missing)
        if not items:
            return {"applied": [], "note": "Média absent du projet : importer puis relancer, ou import_if_missing=true."}
        applied = [await conn.execute("transcript.set", {"item": item, "transcript": transcript}) for item in items]
    return {"applied": applied}


async def add_markers(times: list[float], offset_seconds: float, name_prefix: str,
                      color: str | None) -> dict[str, Any]:
    if len(times) > MAX_MARKERS:
        raise FilmCraftError(f"{len(times)} marqueurs : trop (max {MAX_MARKERS}). Utiliser every='bar'.")
    added = 0
    try:
        async with connect() as conn:
            for i, t in enumerate(times, 1):
                params: dict[str, Any] = {"target": "program", "name": f"{name_prefix} {i}",
                                          "time": config.seconds_to_ticks(t + offset_seconds)}
                if color:
                    params["color"] = color
                await conn.execute("markers.add", params)
                added += 1
    except FilmCraftError as exc:
        # Ne pas relancer à l'aveugle : les `added` premiers marqueurs sont déjà posés.
        return {"markersAdded": added, "markersRequested": len(times), "error": str(exc)}
    return {"markersAdded": added}
