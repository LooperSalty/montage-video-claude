"""Lancement asynchrone de ffmpeg / ffprobe / du worker, avec suivi de progression."""

from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any, AsyncIterator, Awaitable, Callable

from . import config

ProgressCallback = Callable[[float], Awaitable[None]]
# Les barres de progression (tqdm, ffmpeg) peuvent produire de très longues « lignes ».
STREAM_LIMIT = 16 * 1024 * 1024
WORKER_ENV = {"PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8", "HF_HUB_DISABLE_PROGRESS_BARS": "1"}


class ToolError(Exception):
    """Échec d'un outil externe, message prêt pour l'agent."""


def require_file(path: str) -> Path:
    p = Path(path).expanduser()
    if not p.is_absolute():
        raise ToolError(f"Chemin absolu attendu : {path}")
    if not p.is_file():
        raise ToolError(f"Fichier introuvable : {path}")
    return p


async def _spawn(args: list[str], env: dict[str, str] | None = None) -> asyncio.subprocess.Process:
    # stdin=DEVNULL est vital : le stdin du serveur MCP est le canal JSON-RPC, ffmpeg y lirait
    # ses « touches clavier » et bloquerait (ou volerait des messages).
    return await asyncio.create_subprocess_exec(
        *args, stdin=asyncio.subprocess.DEVNULL, stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE, limit=STREAM_LIMIT, env=env)


async def _supervise(proc: asyncio.subprocess.Process, work: Awaitable[Any], timeout: float, what: str) -> Any:
    """Attend `work` ; sur délai dépassé, annulation ou erreur, tue le processus (pas d'orphelin)."""
    try:
        return await asyncio.wait_for(work, timeout)
    except asyncio.TimeoutError as exc:
        raise ToolError(f"{what} arrêté après {timeout:.0f} s.") from exc
    finally:
        if proc.returncode is None:
            proc.kill()
            await proc.wait()


async def _lines(stream: asyncio.StreamReader | None) -> AsyncIterator[str]:
    """Lignes d'un flux, découpées aussi sur « \\r » (barres de progression)."""
    if stream is None:
        return
    async for raw in stream:
        for part in raw.decode("utf-8", "replace").replace("\r", "\n").split("\n"):
            if part.strip():
                yield part.strip()


async def run(args: list[str], timeout: float = 600.0) -> tuple[int, str, str]:
    proc = await _spawn(args)
    out, err = await _supervise(proc, proc.communicate(), timeout, Path(args[0]).name)
    return proc.returncode or 0, out.decode("utf-8", "replace"), err.decode("utf-8", "replace")


async def run_worker(job: str, params: dict[str, Any], on_progress: ProgressCallback | None,
                     timeout: float) -> dict[str, Any]:
    """Lance `filmcraft_assist.worker` dans un processus séparé (voir worker.py pour la raison)."""
    proc = await _spawn([sys.executable, "-m", "filmcraft_assist.worker", job, json.dumps(params)],
                        env={**os.environ, **WORKER_ENV})
    errors: list[str] = []

    async def work() -> bytes:
        stdout_task = asyncio.create_task(proc.stdout.read())  # type: ignore[union-attr]
        try:
            async for line in _lines(proc.stderr):
                if line.startswith("PROGRESS ") and on_progress:
                    await on_progress(float(line.split()[1]))
                elif line.startswith("ERROR "):
                    errors.append(line[6:])
            await proc.wait()
            return await stdout_task
        finally:
            stdout_task.cancel()

    out = await _supervise(proc, work(), timeout, f"Calcul « {job} »")
    if proc.returncode != 0:
        raise ToolError(errors[-1] if errors else f"Calcul « {job} » échoué (code {proc.returncode}).")
    return json.loads(out)


async def ffprobe_json(path: Path) -> dict[str, Any]:
    code, out, err = await run(
        [config.ffprobe_exe(), "-v", "error", "-print_format", "json", "-show_format", "-show_streams", str(path)],
        timeout=60,
    )
    if code != 0:
        raise ToolError(f"ffprobe n'a pas pu lire {path.name} : {err.strip()[-400:]}")
    return json.loads(out)


async def ffmpeg_with_progress(
    args: list[str], duration_s: float, on_progress: ProgressCallback | None, timeout: float
) -> str:
    """Lance ffmpeg avec `-progress pipe:1` et remonte l'avancement (0..1). Renvoie stderr."""
    proc = await _spawn([config.ffmpeg_exe(), "-nostdin", "-hide_banner", "-nostats", "-progress", "pipe:1", *args])

    async def work() -> bytes:
        stderr_task = asyncio.create_task(proc.stderr.read())  # type: ignore[union-attr]
        try:
            async for line in _lines(proc.stdout):
                key, _, value = line.partition("=")
                if key == "out_time_us" and value.isdigit() and duration_s > 0 and on_progress:
                    await on_progress(min(1.0, int(value) / 1e6 / duration_s))
            await proc.wait()
            return await stderr_task
        finally:
            stderr_task.cancel()

    err = (await _supervise(proc, work(), timeout, "ffmpeg")).decode("utf-8", "replace")
    if proc.returncode != 0:
        raise ToolError(f"ffmpeg a échoué : {err.strip()[-600:]}")
    return err
