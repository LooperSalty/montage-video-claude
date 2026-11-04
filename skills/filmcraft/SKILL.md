---
name: filmcraft
description: Montage vidéo de qualité pro dans FilmCraft (NLE open source en Rust installé sur ce PC), piloté par deux MCP — `filmcraft` (l'appli : 700+ commandes, timeline, étalonnage Lumetri, mixage, sous-titres, export) et `filmcraft-assist` (Whisper large GPU, beats musicaux, contrôle qualité d'export, planches contact, conformation VFR). This skill should be used when the user wants to edit, cut, dérusher, sous-titrer, étalonner, mixer ou exporter une vidéo dans FilmCraft, couper les « euh » et les silences, caler un montage sur une musique, ou vérifier la loudness / qualité d'un export. Déclencheurs : "FilmCraft", "monte cette vidéo", "dérush", "coupe les blancs", "sous-titres", "étalonnage", "mixage", "export YouTube/TikTok", "LUFS".
---

# FilmCraft — montage piloté par Claude

## Installation sur ce PC

| Élément | Emplacement |
|---|---|
| Appli + CLI (portable 0.13.0) | `%LOCALAPPDATA%\Programs\FilmCraft\` (`filmcraft.exe`, `filmcraft-cli.exe`, données dans `data\`) |
| Lanceur (canal de contrôle 127.0.0.1:9876 + jeton) | `{{DEPOT}}\filmcraft-mcp\launcher\FilmCraftClaude.exe` (raccourci bureau « FilmCraft ») |
| Jeton du canal de contrôle | `%LOCALAPPDATA%\FilmCraft-Claude\control.token` (ne jamais l'afficher ni le copier ailleurs) |
| MCP compagnon (Python, uv) | `{{DEPOT}}\filmcraft-mcp\server\` |
| Source FilmCraft (docs) | `{{DEPOT}}\filmcraft\docs\` (`agents.md`, `control-protocol.md`, `captions.md`, `graphics.md`) |

## Démarrage (toujours dans cet ordre)

1. `filmcraft_status` (MCP filmcraft-assist). Si `running=false` → `filmcraft_launch` (avec `files` = projet `.fcproj` ou médias si besoin).
2. Charger les outils MCP s'ils sont différés : ToolSearch `+filmcraft` (les deux serveurs).
3. Ne jamais monter le travail de l'utilisateur dans le projet démo : `command_run file.newProject {name}` puis `file.saveAs {path}` dans le dossier du projet, ou `file.open {path}`.

## Les deux MCP

| Besoin | Outil |
|---|---|
| État / lancer l'appli | `filmcraft_status`, `filmcraft_launch` (assist) |
| Lire le projet, les ids | `doc_inspect`, `project_inspect`, `sequence_inspect` (filmcraft) |
| Agir | `command_run {id, params}`, `command_batch {steps, stop_on_error}`, `media_import` (filmcraft) |
| Trouver une commande | `command_list {filter}` ou grep dans `references/commands.md` |
| Voir le résultat | `render_frame {seconds}`, `ui_screenshot {panel?}` (filmcraft) ; `contact_sheet` (assist) puis Read de l'image |
| Analyser un rush avant montage | `media_probe` → `media_conform` si VFR (assist) |
| Transcription mot à mot (FR) | `transcribe_media` (assist) — **jamais** `transcript.generate` (whisper-base, faible en français) |
| Caler sur la musique | `music_beats {add_markers, every, offset_seconds}` (assist) |
| Contrôle qualité final | `export_qc {path, platform}` (assist) |

Hors MCP, le CLI marche aussi en Bash (headless, sans fenêtre) : `filmcraft-cli --project p.fcproj --save exec <id> key=value`, `filmcraft-cli --project p.fcproj export out.mp4 --preset "YouTube 1080p Full HD"`.

## Boucle de travail

1. Inspecter (`sequence_inspect`) → récupérer les ids de clips/éléments. Les ids changent après un razor : ré-inspecter.
2. Agir avec des cibles **explicites** (`clips: [id]`, `item: id`) plutôt que la sélection.
3. Vérifier en regardant : `render_frame` sur les points clés, `scopes.read` pour l'étalonnage, `contact_sheet` pour le rythme.
4. Si c'est faux : `command_run edit.undo`. Sauvegarder souvent : `file.save`.

## Règles qui évitent les erreurs

- Temps : ticks (254 016 000 000 / s). La plupart des commandes acceptent `seconds`, `frame` ou `timecode` → préférer `seconds`. `markers.add` et `sequence.addEdit` veulent `time` en ticks.
- Séquence = format de sortie : `file.newSequence {name, width, height, fps, sampleRate: 48000}` réglée sur la diffusion (16:9 1920×1080, 9:16 1080×1920, 1:1 1080×1080), cadence = celle des rushes conformés.
- Tics de langage en français : `transcript.removeFillers` a une liste anglaise par défaut → toujours passer `fillers` (renvoyée par `transcribe_media`).
- Exports longs : `file.exportMedia {…, wait: true}`. Toujours finir par `export_qc` puis `contact_sheet` sur le fichier exporté.
- Le ffmpeg du PATH est une version de 2013 : passer par les outils assist (ffmpeg 8 WinGet) ou `%LOCALAPPDATA%\Microsoft\WinGet\Links\ffmpeg.exe`.
- Commande refusée « not available right now » : une condition manque (séquence ouverte, clip du bon type, cible). Lire `command_list {filter: "<id>"}` → champ `enabled`.

## Recettes

Recettes détaillées avec les paramètres exacts : `references/recipes.md`.
- **A. Tuto / face caméra** : probe → conform → transcription → couper « euh » et blancs → voix propre → sous-titres → étalonnage → export -14 LUFS → QC.
- **B. Short vertical 9:16** : séquence 1080×1920, recadrage, sous-titres gros et courts, préréglage « Social Vertical 1080×1920 ».
- **C. Montage sur musique** : `music_beats` → marqueurs de mesure → coupes sur marqueurs → ducking.
- **D. Étalonnage** : Lumetri (paramètres réels dans `references/effects.md`, effet `lumetri`), raccord de plans `lumetri.applyMatch`, contrôle `scopes.read`.
- **E. Mixage** : Essential Sound (dialogue/musique), ducking, limiteur true peak sur Mix.
- **F. Export + QC** : préréglages dans `references/export-presets.md`, `loudnessLufs`, `captionSidecar`, `burnCaptions`.

## Références

- `references/recipes.md` — pas-à-pas des recettes A–F avec charges JSON.
- `references/commands.md` — les 710 commandes par famille (grep : `` `timeline. ``, `` `captions. ``, `` `lumetri. ``, `` `essentialSound. ``, `` `export. ``, `` `transcript. ``).
- `references/effects.md` — 303 effets/transitions avec ids de paramètres, bornes et choix (grep `` `lumetri` ``, `` `hard_limiter` ``, `` `cross_dissolve` ``).
- `references/export-presets.md` — 39 préréglages d'export.
- `scripts/gen_reference.py` — régénère les trois références après une mise à jour de FilmCraft : `python -I scripts/gen_reference.py`.

## Mise à jour de FilmCraft

Télécharger `filmcraft-<ver>-windows-x64-portable.zip` depuis github.com/storytold/filmcraft/releases (vérifier `SHA256SUMS.txt`), fermer FilmCraft, remplacer `filmcraft.exe` et `filmcraft-cli.exe` dans `%LOCALAPPDATA%\Programs\FilmCraft\` (garder `data\` et `portable.txt`), puis relancer `scripts/gen_reference.py`.
