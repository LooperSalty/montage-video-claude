#!/usr/bin/env bash
# Installe l'environnement du kit « Pourtant c'est vrai » (macOS / Linux).
# Usage : bash install.sh            (SKIP_REMOTION_SKILLS=1 bash install.sh pour sauter les skills Remotion)
set -euo pipefail
cd "$(dirname "$0")"

step() { printf '\n==> %s\n' "$1"; }
ok() { printf '    OK  %s\n' "$1"; }
warn() { printf '    !!  %s\n' "$1"; }
need() {  # need <commande> <conseil d'installation>
  command -v "$1" >/dev/null 2>&1 || { echo "Manque : $1. Installer avec : $2" >&2; exit 1; }
}

step "1/6 Outils système"
need python3 "brew install python@3.12   |  sudo apt install python3 python3-venv"
need node "brew install node             |  https://nodejs.org (LTS)"
need ffmpeg "brew install ffmpeg           |  sudo apt install ffmpeg"
python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)' || { echo "Python 3.10+ requis" >&2; exit 1; }
[ "$(node -p 'process.versions.node.split(".")[0]')" -ge 18 ] || { echo "Node 18+ requis" >&2; exit 1; }
ok "python3, node, ffmpeg"

step "2/6 Environnement Python (.venv)"
[ -d .venv ] || python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
ok "paquets Python dans .venv (activer avec : source .venv/bin/activate)"

step "3/6 Dépendances du studio Remotion (npm ci, ~700 Mo)"
(cd studio && npm ci --no-audit --no-fund)
ok "node_modules"

step "4/6 Assets partagés"
.venv/bin/python -I pipeline/setup_assets.py
ok "assets"

step "5/6 Navigateur de rendu Remotion"
(cd studio && npx remotion browser ensure)
ok "navigateur de rendu"

step "6/6 Claude Code et skills"
if command -v claude >/dev/null 2>&1; then ok "Claude Code présent"; else warn "Claude Code absent : curl -fsSL https://claude.ai/install.sh | bash"; fi
ok "skill du projet « pourtant-cest-vrai » : déjà dans .claude/skills"
if [ "${SKIP_REMOTION_SKILLS:-0}" = "1" ]; then
  warn "skills Remotion officielles ignorées"
else
  npx -y skills add remotion-dev/skills || warn "skills Remotion non installées (facultatif)"
fi

printf '\nTout est prêt.\n'
echo "Test rapide : source .venv/bin/activate && python -I pipeline/build_story.py lustig && python -I pipeline/render.py lustig && python -I pipeline/qc.py lustig"
