---
name: pourtant-cest-vrai
description: Produit de A à Z une vidéo TikTok faceless « Pourtant c'est vrai » (histoire vraie sourcée, 65-75 s, 9:16) avec le pipeline de ce projet — script JSON, images libres Wikimedia Commons, voix edge-tts, montage Remotion, son -14 LUFS, contrôle qualité, textes de publication. À utiliser quand l'utilisateur veut une nouvelle vidéo, une histoire du backlog, un nouvel épisode, retoucher une vidéo existante (hook, images, tampons, musique, durée) ou préparer la publication. Déclencheurs : "nouvelle vidéo", "fais l'histoire", "dossier n°", "épisode", "backlog", "TikTok", "Pourtant c'est vrai", "rendu", "QC".
---

# Pourtant c'est vrai : produire une vidéo (~15 min)

Toutes les commandes se lancent depuis la racine du projet (le dossier qui contient `pipeline/` et `studio/`).
macOS/Linux : `source .venv/bin/activate` d'abord (créé par `install.sh`).
Console Windows qui plante sur un emoji (`UnicodeEncodeError`) : ajouter `-X utf8` après `python -I`.

Avant la 1re vidéo, vérifier que `studio/node_modules/` existe et que `ffmpeg -version` répond. Sinon : lancer `install.ps1` (Windows) ou `install.sh`.

## 1. Choisir et vérifier l'histoire (~3 min)

- Prendre une idée non cochée (sans ✅) dans `docs/BACKLOG_100.md`, en alternant les 5 séries (`docs/STRATEGIE.md` §3).
- Vérifier chaque fait sur **2 sources indépendantes minimum** (WebSearch / WebFetch). Un point marqué ⚠️ ou douteux se dit avec prudence (« selon ses mémoires », « la légende raconte »).
- `id` : court, en minuscules, sans accent ni espace (ex. `macgregor`). `episode` : le plus grand numéro de `stories/*.json` + 1.

## 2. Écrire le script `stories/<id>.json` (~5 min)

Partir d'une copie de `stories/lustig.json` (mêmes clés). Repères mesurés sur les 3 vidéos existantes : **13-14 beats, 180-200 mots → 67-74 s** avec `"rate": "+15%"`.

- **Structure** : hook (le fait le plus improbable, dès la 1re phrase) → qui → contexte (1 phrase) → 3 escalades → twist → punchline finale qui fait écho au hook (ça donne envie de revoir). Jamais de « abonne-toi » à la voix.
- `hook` : 2 lignes en MAJUSCULES, 15 caractères max chacune (`"IL A VENDU"`, `"LA TOUR EIFFEL"`), affichées pendant la 1re phrase.
- `beats[].text` : 1 ou 2 phrases = 1 plan de 4 à 6 s. Chiffres écrits en chiffres (edge-tts les lit bien).
- `stamp` : un tampon rouge sur chaque chiffre clé. `on` = un mot réellement prononcé dans la phrase, qui déclenche le tampon.
- `label` : étiquette en MAJUSCULES, format « SUJET · LIEU/DATE » (ex. `"CERTIFICAT DE DÉCÈS · 1947"`).
- `mode` : `cover` pour une grande photo lisible en 9:16 (régler `focus` `[x, y]` entre 0 et 1 sur le visage ou le sujet) ; `card` pour les documents, les unes de journaux et les photos petites ou horizontales (automatique si l'image est trop petite).
- `grade` : `archive` (défaut : sépia et grain). `natural` pour une photo couleur moderne.
- `sfx` (volume 0.4 à 0.55, `on` facultatif) : `sfx/impact.mp3` (révélation, 1er beat), `sfx/cash.mp3` (argent), `sfx/whoosh2.mp3`, `sfx/hit.mp3`, `sfx/stamp.mp3`. Le whoosh entre deux images et le son des tampons sont ajoutés automatiquement.
- `music` : `music/investigations.mp3` (enquête, arnaque, volume 0.10), `music/lightless_dawn.mp3` (drame, survie, 0.13), `music/sneaky_snitch.mp3` (absurde, humour, 0.09).
- Dernier beat : `"gap": 0.1`. Réutiliser l'image du début pour la chute est un bon écho.
- `post` : `caption` (2-3 lignes, une question finale, 1-2 emojis), `hashtags` (~10, finir par `#pourtantcestvrai`), `sources` (les URLs vérifiées à l'étape 1).
- `voice` : `fr-FR-RemyMultilingualNeural`.

Puis ajouter `'<id>'` dans `STORIES` de `studio/src/Root.tsx`.

## 3. Trouver les images libres (~5 min)

```bash
python -I pipeline/commons.py search <dossier_temp>/cands/<id> "requête 1" "requête 2" "requête 3"
```

- 4 à 8 requêtes, en anglais et en français : noms propres, lieux, objets, dates.
- Ouvrir les planches `planche_XX.jpg` avec l'outil Read (vignettes numérotées) ; `candidats.json` donne titre, taille et licence de chaque numéro.
- Écrire `stories/sel/<id>.json` : `[{"title": "File:Exemple.jpg", "name": "nom_court"}, ...]`, 9 à 13 images. Chaque `name` = une valeur `img` des beats.
- Télécharger : `python -I pipeline/commons.py fetch studio_assets/<id> stories/sel/<id>.json`. En cas d'erreur 429, relancer la même commande : elle reprend là où elle s'est arrêtée.
- Seules les licences libres passent (domaine public, CC0, CC BY, CC BY-SA). Les crédits vont dans `studio_assets/<id>/credits.json`, puis dans `post.txt`.

## 4. Voix et timeline (~1 min)

```bash
python -I pipeline/build_story.py <id>
```

- Affiche la durée. Hors de 65-75 s : raccourcir ou rallonger le texte (≈ 2,7 mots/s) et relancer. La voix est en cache par phrase, donc seules les phrases modifiées sont régénérées.
- `! mot « X » introuvable` : changer le `on` du tampon ou du sfx pour un mot réellement prononcé.

## 5. Aperçu (optionnel)

`cd studio && npm run dev`, puis http://localhost:3000. Vérifier les cadrages (`focus`) et le moment des tampons.

## 6. Rendu (~3-6 min)

```bash
python -I pipeline/render.py <id>
```

Sortie : `exports/<id>/<id>.mp4` (H.264, AAC 48 kHz, -14 LUFS). `--skip-render` refait seulement la normalisation du son. Au 1er rendu, Remotion télécharge Chrome Headless Shell (~100 Mo).

## 7. Contrôle qualité

```bash
python -I pipeline/qc.py <id>
```

- Aucune ligne `ECHEC` autorisée. `ATTENTION` sur la durée : à corriger si possible.
- Ouvrir `exports/<id>/planche.jpg` avec Read : aucune image noire ou vide, sous-titres lisibles, hook visible sur la 1re vignette, rien d'important coupé par le cadrage.

## 8. Publier

- Légende : `exports/<id>/description.txt`. Commentaire à épingler juste après la publication : `exports/<id>/post.txt` (sources et crédits, obligatoires pour les licences CC BY).
- Cocher « Contenu généré par l'IA » (la voix est synthétique).
- Marquer l'histoire ✅ dans `docs/BACKLOG_100.md`.

## Règles d'or

1. Que du vrai : 2 sources minimum, formulations prudentes sur les points contestés.
2. Pas de faits divers récents avec des victimes identifiables.
3. Images libres uniquement (le filtre de `commons.py` s'en charge), crédits toujours publiés.
4. Scripts originaux, jamais de repost du contenu d'autrui.

## Dépannage

| Symptôme | Correctif |
|---|---|
| `timeline.json introuvable` dans le Studio | Lancer `build_story.py <id>` et vérifier que l'id est dans `STORIES` (`Root.tsx`) |
| `ffmpeg introuvable` ou vieux ffmpeg sans libx264 | Installer un ffmpeg récent, ou forcer un binaire avec la variable `FFMPEG=` |
| `edge-tts a échoué 3 fois` | Connexion internet requise : relancer |
| `Image manquante` | Le `img` du beat ne correspond à aucun `name` de `stories/sel/<id>.json` : corriger, puis relancer `fetch` |
