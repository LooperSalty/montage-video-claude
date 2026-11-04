# CLAUDE.md

Usine à TikToks faceless « Pourtant c'est vrai » : des histoires vraies et sourcées, en 9:16, de 65 à 75 s. Tout est gratuit : images Wikimedia Commons, voix edge-tts, montage Remotion, son normalisé par ffmpeg.

## Pour produire une vidéo

Utiliser la skill du projet **`pourtant-cest-vrai`** (`.claude/skills/pourtant-cest-vrai/SKILL.md`). Elle couvre tout, de l'histoire du backlog à la publication.

## Carte du projet

| Chemin | Rôle |
|---|---|
| `docs/STRATEGIE.md`, `docs/BACKLOG_100.md` | Ligne éditoriale, format, 100 idées d'histoires |
| `stories/<id>.json` | Script d'une vidéo (beats, tampons, sfx, musique, post) |
| `stories/sel/<id>.json` | Images Wikimedia choisies pour cette vidéo |
| `studio_assets/<id>/` | Images téléchargées et `credits.json` |
| `pipeline/commons.py` | Recherche et téléchargement d'images libres |
| `pipeline/build_story.py` | Voix off, timeline Remotion, `post.txt` |
| `pipeline/render.py` | Rendu Remotion, puis son à -14 LUFS → `exports/<id>/<id>.mp4` |
| `pipeline/qc.py` | Contrôle qualité et planche contact |
| `studio/` | Projet Remotion 4.0.532 (`src/Root.tsx` : liste `STORIES`) |

## Conventions

- Français partout (scripts, commentaires, messages).
- Python : toujours `python -I` (`-X utf8` si la console plante sur un emoji). macOS/Linux : `source .venv/bin/activate` avant.
- Ne pas modifier `studio/public/stories/` à la main : c'est généré par `build_story.py`.
- Remotion : versions figées à `4.0.532` (mettre à jour `remotion`, `@remotion/cli` et `@remotion/fonts` ensemble, en `--save-exact`).
- Marque : outro dans `pipeline/build_story.py` (texte) et `studio/src/components/Outro.tsx`, « DOSSIER Nº » dans `Overlays.tsx`, couleurs dans `studio/src/theme.ts`.
