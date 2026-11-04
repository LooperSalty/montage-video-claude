"""Test de bout en bout : démarre le serveur MCP en stdio et appelle chaque outil.

Usage : uv run python tests/smoke_mcp.py <video.mp4> <musique.wav> <voix.wav>
(FilmCraft doit tourner pour la partie transcription → FilmCraft et marqueurs.)
"""

from __future__ import annotations

import asyncio
import json
import sys
import time
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

SERVER_DIR = Path(__file__).resolve().parents[1]


async def call(session: ClientSession, name: str, **args: object) -> dict:
    started = time.monotonic()
    result = await session.call_tool(name, args)
    text = "".join(getattr(c, "text", "") for c in result.content)
    status = "ERREUR" if result.isError else "ok"
    print(f"\n=== {name} [{status}] {time.monotonic() - started:.1f} s\n{text[:1500]}")
    if result.isError:
        raise SystemExit(1)
    return json.loads(text) if text.startswith("{") else {}


async def main(video: str, music: str, voice: str) -> None:
    params = StdioServerParameters(command="uv", args=["run", "--directory", str(SERVER_DIR), "filmcraft-assist"])
    async with stdio_client(params) as (read, write), ClientSession(read, write) as session:
        await session.initialize()
        tools = await session.list_tools()
        print("outils :", [t.name for t in tools.tools])
        await call(session, "filmcraft_status")
        probe = await call(session, "media_probe", paths=[video, music])
        assert probe["files"][0]["video"]["width"] == 1280
        await call(session, "contact_sheet", path=video, count=8, columns=4, width=1280)
        qc = await call(session, "export_qc", path=video, platform="youtube")
        assert qc["checks"], "pas de contrôle"
        beats = await call(session, "music_beats", path=music)
        assert 115 <= beats["bpm"] <= 125, beats["bpm"]
        tr = await call(session, "transcribe_media", path=voice, language="fr", import_if_missing=True)
        assert tr["words"] > 20
        await call(session, "media_conform", path=video, codec="prores_lt")
        await call(session, "music_beats", path=music, add_markers=True, every="bar", offset_seconds=0)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")  # console Windows en cp1252 par défaut
    asyncio.run(main(*sys.argv[1:4]))
