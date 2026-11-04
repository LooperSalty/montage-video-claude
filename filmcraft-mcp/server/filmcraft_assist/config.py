"""Constantes et chemins partagés par les outils du MCP compagnon."""

from __future__ import annotations

import os
import shutil
from pathlib import Path

# FilmCraft compte le temps en « ticks » : 254 016 000 000 par seconde (divisible par toutes
# les cadences et fréquences d'échantillonnage courantes).
TICKS_PER_SECOND = 254_016_000_000

CONTROL_HOST = "127.0.0.1"
CONTROL_PORT = int(os.environ.get("FILMCRAFT_CONTROL_PORT", "9876"))
CONTROL_TIMEOUT_S = 120.0
# Une réponse du canal de contrôle peut contenir tout le projet : on accepte de longues lignes.
CONTROL_LINE_LIMIT = 32 * 1024 * 1024

LOCALAPPDATA = Path(os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData" / "Local")))
FILMCRAFT_DIR = Path(os.environ.get("FILMCRAFT_DIR", str(LOCALAPPDATA / "Programs" / "FilmCraft")))
FILMCRAFT_CLI = FILMCRAFT_DIR / "filmcraft-cli.exe"
TOKEN_FILE = LOCALAPPDATA / "FilmCraft-Claude" / "control.token"
LAUNCHER = Path(__file__).resolve().parents[2] / "launcher" / "FilmCraftClaude.exe"

# Limite de taille des réponses renvoyées à l'agent (caractères).
CHARACTER_LIMIT = 20_000

# Le ffmpeg trouvé en premier sur le PATH de cette machine est une version de 2013 :
# on préfère la variable d'environnement, puis le ffmpeg 8 installé par WinGet.
_WINGET_LINKS = LOCALAPPDATA / "Microsoft" / "WinGet" / "Links"


def _resolve_tool(name: str, env_var: str) -> str:
    explicit = os.environ.get(env_var)
    if explicit and Path(explicit).exists():
        return explicit
    winget = _WINGET_LINKS / f"{name}.exe"
    if winget.exists():
        return str(winget)
    found = shutil.which(name)
    if found:
        return found
    raise FileNotFoundError(
        f"{name} introuvable. Installe-le (winget install Gyan.FFmpeg) ou définis {env_var}."
    )


def ffmpeg_exe() -> str:
    return _resolve_tool("ffmpeg", "FFMPEG")


def ffprobe_exe() -> str:
    return _resolve_tool("ffprobe", "FFPROBE")


def seconds_to_ticks(seconds: float) -> int:
    return round(seconds * TICKS_PER_SECOND)


def ticks_to_seconds(ticks: int) -> float:
    return ticks / TICKS_PER_SECOND
