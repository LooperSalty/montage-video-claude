# Pourtant c'est vrai : usine à TikToks (100 % gratuite)

Chaîne TikTok faceless d'histoires vraies. Stratégie : `docs/STRATEGIE.md` · 100 idées : `docs/BACKLOG_100.md`.

## Stack (tout est gratuit)

| Étape | Outil |
|---|---|
| Script | Claude → `stories/<id>.json` |
| Images | Wikimedia Commons (domaine public / CC), sans clé API → `pipeline/commons.py` |
| Voix off | edge-tts, voix `fr-FR-RemyMultilingualNeural` +15 %, avec horodatage mot à mot |
| Montage | Remotion 4.0.532 (`studio/`) : Ken Burns, cartes d'archive, sous-titres karaoké, tampons, grain |
| Musique / SFX | Kevin MacLeod (CC BY 4.0) + PackMontage |
| Son | ffmpeg 8 loudnorm 2 passes → -14 LUFS |
| QC | `pipeline/qc.py` : format, durée, codecs, loudness, true peak + planche contact |

## Produire une vidéo (~15 min)

```bash
cd tiktok
# 1. Images : chercher, regarder la planche, puis télécharger la sélection
python -I pipeline/commons.py search "$TEMP/cands/<id>" "requête 1" "requête 2"
python -I pipeline/commons.py fetch studio_assets/<id> stories/sel/<id>.json
# 2. Script : écrire stories/<id>.json (copier un existant), et ajouter <id> dans STORIES de studio/src/Root.tsx
# 3. Voix + timeline + post.txt
python -I pipeline/build_story.py <id>
# 4. Rendu + normalisation -14 LUFS → exports/<id>/<id>.mp4
python -I pipeline/render.py <id>
# 5. Contrôle qualité + planche contact → exports/<id>/planche.jpg
python -I pipeline/qc.py <id>
```

Aperçu interactif : `cd studio && npm run dev` (Remotion Studio).

Installation : `install.ps1` (Windows) ou `install.sh` (macOS/Linux), voir `LISEZ-MOI.md`. Les polices, SFX et musiques sont déjà dans `studio/public/`.

## Format d'un `stories/<id>.json`

- `hook` : 2 lignes de titre affichées pendant la 1re phrase.
- `beats[]` : une phrase (ou deux) = un plan.
  - `img` : nom de l'image dans `studio_assets/<id>/`.
  - `mode` : `cover` (plein écran) ou `card` (photo d'archive encadrée). Les images trop petites passent automatiquement en `card`.
  - `focus` : point de cadrage `[x, y]` entre 0 et 1.
  - `label` : étiquette tapée à la machine.
  - `stamp` : `{ "text", "on": "mot déclencheur" }`.
  - `sfx` : effets sonores ponctuels.
  - `grade` : `archive` ou `natural`.
- `post` : légende, hashtags, sources (→ `exports/<id>/post.txt`, avec les crédits images et musique ajoutés automatiquement).

## Pièges connus

- ffmpeg : le pipeline prend celui de WinGet s'il existe, sinon celui du PATH. Variable `FFMPEG=` pour en imposer un autre (un ffmpeg trop vieux n'a pas libx264).
- Wikimedia renvoie des erreurs 429 sur les originaux : `commons.py` passe par les vignettes standard (1920/1280/960 px). Relancer la commande reprend là où elle s'est arrêtée.
