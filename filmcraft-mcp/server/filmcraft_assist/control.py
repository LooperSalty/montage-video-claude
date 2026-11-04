"""Client du canal de contrôle de FilmCraft (JSON lines sur TCP, 127.0.0.1).

Le MCP officiel `filmcraft` couvre le pilotage général. Ce client sert aux outils du compagnon
qui doivent pousser beaucoup de données d'un coup (transcription mot à mot, centaines de
marqueurs) sans les faire transiter par la conversation.
"""

from __future__ import annotations

import asyncio
import json
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator

from . import config


class FilmCraftError(Exception):
    """Erreur lisible par l'agent, avec la marche à suivre."""


def read_token() -> str:
    try:
        token = config.TOKEN_FILE.read_text(encoding="utf-8").strip()
    except FileNotFoundError as exc:
        raise FilmCraftError(
            "Jeton du canal de contrôle absent. Lance FilmCraft une fois avec le raccourci du "
            "bureau ou l'outil filmcraft_launch : le lanceur le crée."
        ) from exc
    if len(token) != 64:
        raise FilmCraftError(f"Jeton invalide dans {config.TOKEN_FILE} (64 caractères hex attendus).")
    return token


async def is_running(timeout: float = 0.5) -> bool:
    try:
        _, writer = await asyncio.wait_for(
            asyncio.open_connection(config.CONTROL_HOST, config.CONTROL_PORT), timeout
        )
    except (OSError, asyncio.TimeoutError):
        return False
    writer.close()
    try:
        await writer.wait_closed()
    except OSError:
        pass
    return True


class Connection:
    def __init__(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter, token: str):
        self._reader = reader
        self._writer = writer
        self._token = token
        self._next_id = 1

    async def call(self, method: str, params: dict[str, Any] | None = None) -> Any:
        request = {"id": self._next_id, "token": self._token, "method": method, "params": params or {}}
        self._next_id += 1
        try:
            self._writer.write((json.dumps(request, ensure_ascii=False) + "\n").encode("utf-8"))
            await self._writer.drain()
            line = await asyncio.wait_for(self._reader.readline(), config.CONTROL_TIMEOUT_S)
            reply = json.loads(line) if line else None
        except asyncio.TimeoutError as exc:
            raise FilmCraftError(f"FilmCraft n'a pas répondu à {method} en {config.CONTROL_TIMEOUT_S:.0f} s.") from exc
        except (OSError, ValueError) as exc:  # connexion coupée, réponse tronquée ou trop longue
            raise FilmCraftError(f"Liaison avec FilmCraft perdue pendant {method} : {exc}") from exc
        if not isinstance(reply, dict):
            raise FilmCraftError("FilmCraft a fermé la connexion (jeton refusé ou appli fermée).")
        if not reply.get("ok"):
            raise FilmCraftError(f"{method} a échoué : {reply.get('error', reply)}")
        return reply.get("result")

    async def execute(self, command: str, params: dict[str, Any] | None = None) -> Any:
        return await self.call("engine.execute", {"command": command, "params": params or {}})


@asynccontextmanager
async def connect() -> AsyncIterator[Connection]:
    token = read_token()
    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(
                config.CONTROL_HOST, config.CONTROL_PORT, limit=config.CONTROL_LINE_LIMIT
            ),
            5.0,
        )
    except (OSError, asyncio.TimeoutError) as exc:
        raise FilmCraftError(
            f"FilmCraft n'écoute pas sur {config.CONTROL_HOST}:{config.CONTROL_PORT}. "
            "Lance-le avec l'outil filmcraft_launch ou le raccourci FilmCraft du bureau."
        ) from exc
    try:
        yield Connection(reader, writer, token)
    finally:
        writer.close()
        try:
            await writer.wait_closed()
        except OSError:
            pass
