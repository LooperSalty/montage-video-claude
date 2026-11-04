# Kit « Pourtant c'est vrai » : l'usine à TikToks d'histoires vraies

Avec ce kit, Claude Code produit tout seul des vidéos TikTok faceless (9:16, 65-75 s) : script sourcé, images d'archives libres, voix off, sous-titres karaoké, tampons, musique, son à -14 LUFS, contrôle qualité, légende et commentaire de sources. **Tout est gratuit**, sans clé API.

3 histoires d'exemple sont incluses : Victor Lustig (la tour Eiffel), Violet Jessop (3 naufrages) et la guerre des émeus. Les MP4 ne sont pas dans le kit (trop lourds) : ils se régénèrent en ~5 min chacun.

## 1. Installer (~10 min)

**Windows 10/11** : ouvrir PowerShell dans ce dossier, puis :

```powershell
powershell -ExecutionPolicy Bypass -File install.ps1
```

**macOS / Linux** :

```bash
bash install.sh
```

Le script installe ou vérifie Python 3.10+, Node.js 18+ et ffmpeg (via winget sous Windows), les paquets Python, le studio Remotion (`npm ci`), le navigateur de rendu et les skills Remotion officielles. Il faut ~3 Go d'espace libre et une connexion internet.

**Claude Code** (abonnement Claude Pro/Max ou clé API) :
- Windows : `irm https://claude.ai/install.ps1 | iex`
- macOS / Linux : `curl -fsSL https://claude.ai/install.sh | bash`

## 2. Vérifier que tout marche (~5 min)

```bash
python -I pipeline/build_story.py lustig
python -I pipeline/render.py lustig
python -I pipeline/qc.py lustig
```

→ `exports/lustig/lustig.mp4`, avec `planche.jpg` (aperçu en 12 images) à côté. Le QC doit afficher uniquement des `OK`.
(macOS/Linux : `source .venv/bin/activate` d'abord.)

## 3. Faire une vidéo avec Claude

```bash
claude   # lancé dans ce dossier
```

Puis demander par exemple :
- « Fais la vidéo de la prochaine histoire du backlog »
- « Fais l'histoire de Gregor MacGregor (n°2 du backlog) »
- « Le hook de lustig est trop long, raccourcis-le et refais le rendu »

Claude charge automatiquement la skill du projet `pourtant-cest-vrai` (ou la commande `/pourtant-cest-vrai`). Il vérifie les faits sur 2 sources, écrit le script, choisit les images, génère la voix, fait le rendu et le QC, puis prépare la légende.

## Ce qu'il y a dans le kit

| Élément | Rôle |
|---|---|
| `.claude/skills/pourtant-cest-vrai/` | La skill Claude Code : le mode d'emploi complet d'une vidéo |
| `CLAUDE.md` | Le contexte du projet, lu par Claude à chaque session |
| `docs/STRATEGIE.md` | Ligne éditoriale, format, plan de publication, monétisation |
| `docs/BACKLOG_100.md` | 100 idées d'histoires vraies (✅ = déjà faite) |
| `pipeline/` | Scripts Python : images (`commons.py`), voix et timeline (`build_story.py`), rendu (`render.py`), QC (`qc.py`) |
| `studio/` | Projet Remotion 4.0.532 : le montage en React (polices, sons et musiques inclus) |
| `stories/` + `studio_assets/` | Scripts et images des 3 histoires d'exemple |
| `install.ps1` / `install.sh` | Installation en une commande |

**Outils utilisés** (tous gratuits) : Remotion (montage), edge-tts (voix Microsoft `fr-FR-RemyMultilingualNeural`), Wikimedia Commons (images libres), ffmpeg (son et encodage), Claude Code (le chef d'orchestre).

## Faire sa propre chaîne

La marque « Pourtant c'est vrai » se change ici : texte de l'outro dans `pipeline/build_story.py` et `studio/src/components/Outro.tsx`, « DOSSIER Nº » dans `studio/src/components/Overlays.tsx`, couleurs dans `studio/src/theme.ts`, hashtag final dans la skill.

## Licences et crédits

- **Images** : Wikimedia Commons, domaine public ou CC (crédits dans `studio_assets/<id>/credits.json`, publiés automatiquement dans `post.txt`).
- **Musiques** : Kevin MacLeod (incompetech.com), CC BY 4.0. Le crédit est obligatoire et ajouté automatiquement dans `post.txt`.
- **Police** : Montserrat (SIL Open Font License).
- **Effets sonores** : extraits de « Mx6's Editing Pack » (pack gratuit pour monteurs), pour un usage personnel.
- **Voix** : edge-tts est gratuit, mais c'est une API Microsoft non officielle. Pour monétiser, ta propre voix reste l'option la plus sûre (voir `docs/STRATEGIE.md` §9).

## Dépannage

| Problème | Solution |
|---|---|
| `python` ouvre le Microsoft Store | Paramètres → Applications → Alias d'exécution → désactiver `python.exe`, puis relancer `install.ps1` |
| `install.ps1 ne peut pas être chargé` | Utiliser la commande exacte ci-dessus (`-ExecutionPolicy Bypass`) |
| Outil « introuvable après installation » | Fermer et rouvrir le terminal, puis relancer le script |
| `UnicodeEncodeError` dans la console | Ajouter `-X utf8` : `python -I -X utf8 pipeline/...` |
| Erreur 429 en téléchargeant les images | Relancer la même commande : elle reprend où elle s'est arrêtée |
