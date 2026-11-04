"""Régénère les références de la skill FilmCraft depuis le CLI installé.

Usage : python gen_reference.py [chemin/vers/filmcraft-cli.exe]
Écrit references/commands.md, references/effects.md et references/export-presets.md.
À relancer après chaque mise à jour de FilmCraft.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parents[1]
REF_DIR = SKILL_DIR / "references"
DEFAULT_CLI = Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "FilmCraft" / "filmcraft-cli.exe"


def cli_json(cli: Path, *args: str) -> object:
    out = subprocess.run([str(cli), "--demo", "--compact", *args], capture_output=True, check=True)
    return json.loads(out.stdout.decode("utf-8"))


def write_commands(cli: Path) -> int:
    commands = cli_json(cli, "commands", "--json")
    groups: dict[str, list[dict]] = defaultdict(list)
    for c in commands:  # type: ignore[union-attr]
        groups[c["id"].split(".")[0]].append(c)
    lines = ["# Commandes FilmCraft (générées par scripts/gen_reference.py)", "",
             "Format : `id` — libellé — raccourci — params. Lancer avec command_run {id, params}.", ""]
    for group in sorted(groups):
        lines += [f"## {group}", ""]
        for c in groups[group]:
            shortcut = f" — `{c['shortcut']}`" if c.get("shortcut") else ""
            params = c.get("params") or "{}"
            lines.append(f"- `{c['id']}` — {c.get('label', '')}{shortcut} — `{params}`")
        lines.append("")
    (REF_DIR / "commands.md").write_text("\n".join(lines), encoding="utf-8")
    return len(commands)  # type: ignore[arg-type]


def _param(p: dict) -> str:
    kind = p.get("type", "?")
    if "options" in p:
        return f"{p['id']}:choice({'|'.join(p['options'])})"
    if "min" in p and "max" in p:
        return f"{p['id']}:{kind}[{p['min']:g}..{p['max']:g}]"
    return f"{p['id']}:{kind}"


def write_effects(cli: Path) -> int:
    lines = ["# Effets et transitions FilmCraft (générés par scripts/gen_reference.py)", "",
             "Appliquer : effects.apply {clips, effect: id}. Régler : effects.setParam {clip, effect: id|index, param, value}.", ""]
    total = 0
    for kind in ("Video", "Audio", "VideoTransition", "AudioTransition"):
        effects = cli_json(cli, "exec", "effects.list", json.dumps({"kind": kind, "detail": True}))
        lines += [f"## {kind}", ""]
        for e in effects:  # type: ignore[union-attr]
            total += 1
            params = ", ".join(_param(p) for p in e.get("paramInfo", []))
            folder = e.get("folder", "")
            lines.append(f"- `{e['id']}` ({e.get('name', '')}, {folder})" + (f" — {params}" if params else ""))
        lines.append("")
    (REF_DIR / "effects.md").write_text("\n".join(lines), encoding="utf-8")
    return total


def write_presets(cli: Path) -> int:
    out = subprocess.run([str(cli), "--compact", "export", "--list-presets"], capture_output=True, check=True)
    presets = json.loads(out.stdout.decode("utf-8"))
    lines = ["# Préréglages d'export FilmCraft (générés par scripts/gen_reference.py)", "",
             "Utiliser : file.exportMedia {path, preset: \"<nom>\", wait: true}.", ""]
    for p in presets:
        lines.append(f"- `{p.get('name')}` — {p.get('category', '')} — {p.get('format', '')}")
    (REF_DIR / "export-presets.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return len(presets)


def main() -> None:
    cli = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_CLI
    if not cli.exists():
        raise SystemExit(f"filmcraft-cli introuvable : {cli}")
    REF_DIR.mkdir(parents=True, exist_ok=True)
    print(f"commandes : {write_commands(cli)}, effets : {write_effects(cli)}, préréglages : {write_presets(cli)}")


if __name__ == "__main__":
    main()
