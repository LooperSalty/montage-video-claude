"""Processus de calcul lourd (librosa, faster-whisper), lancé par proc.run_worker.

Pourquoi un processus séparé : sous Windows, le transport stdio du MCP garde une lecture
synchrone en attente sur stdin ; charger une DLL (numpy, cuBLAS…) depuis un thread du serveur
se bloque alors sur ce même handle. Ici stdin est fermé, et un plantage GPU ne tue pas le MCP.

Protocole : `python -m filmcraft_assist.worker <job> <params json>` → résultat JSON sur stdout,
avancement `PROGRESS <0..1>` sur stderr.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Callable


def _report(fraction: float) -> None:
    print(f"PROGRESS {fraction:.3f}", file=sys.stderr, flush=True)


def _transcribe(params: dict[str, Any], progress: Callable[[float], None]) -> dict[str, Any]:
    from .transcribe import transcribe_words

    result = transcribe_words(Path(params["path"]), params.get("language"), params["model"],
                              params["keep_fillers"], progress)
    words = [[w.text, w.start, w.end, w.probability] for w in result["words"]]
    return {**result, "words": words}


def _beats(params: dict[str, Any], progress: Callable[[float], None]) -> dict[str, Any]:
    from .beats import analyze_sync

    return analyze_sync(Path(params["path"]))


JOBS: dict[str, Callable[[dict[str, Any], Callable[[float], None]], dict[str, Any]]] = {
    "transcribe": _transcribe,
    "beats": _beats,
}


def encode_result(result: dict[str, Any]) -> bytes:
    """JSON en ASCII pur : un tube Windows est en cp1252 par défaut, les accents s'y perdraient."""
    return json.dumps(result, ensure_ascii=True).encode("ascii")


def main() -> int:
    sys.stderr.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
    if len(sys.argv) != 3 or sys.argv[1] not in JOBS:
        print(f"usage: worker <{'|'.join(JOBS)}> <params json>", file=sys.stderr)
        return 2
    try:
        result = JOBS[sys.argv[1]](json.loads(sys.argv[2]), _report)
    except Exception as exc:  # message renvoyé tel quel à l'agent par run_worker
        print(f"ERROR {type(exc).__name__}: {exc}", file=sys.stderr, flush=True)
        return 1
    sys.stdout.buffer.write(encode_result(result))
    sys.stdout.flush()
    return 0


if __name__ == "__main__":
    sys.exit(main())
