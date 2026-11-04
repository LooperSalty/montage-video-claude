# Montage vidéo avec Claude Code

Mon environnement complet pour monter des vidéos avec [Claude Code](https://claude.com/claude-code) : skills, MCP, outils, et un kit TikTok prêt à produire des vidéos.

## Démarrage rapide (Windows 10/11, ~15 min)

Prérequis : [Claude Code](https://docs.claude.com/fr/docs/claude-code) (`irm https://claude.ai/install.ps1 | iex`) et git.

```powershell
git clone https://github.com/LooperSalty/montage-video-claude.git
cd montage-video-claude
powershell -ExecutionPolicy Bypass -File setup\install.ps1    # skills de montage + skills Remotion
powershell -ExecutionPolicy Bypass -File tiktok\install.ps1   # kit TikTok : Python, Node, ffmpeg, studio Remotion
```

Options de `setup\install.ps1` :

| Option | Ajoute |
|---|---|
| `-WithFilmCraft` | FilmCraft 0.13.0 (NLE), son lanceur, le raccourci bureau et les MCP `filmcraft` + `filmcraft-assist` (~3 Go, GPU NVIDIA conseillé pour Whisper) |
| `-WithHyperFrames` | Le plugin HyperFrames (motion graphics HTML/GSAP) |
| `-SkipRemotionSkills` | N'installe pas les skills Remotion officielles |

Les skills déjà présentes sont sauvegardées dans `~/.claude/skills-backup/` avant d'être remplacées. Redémarrer Claude Code ensuite.

## Première vidéo (~15 min)

```powershell
cd tiktok
claude
```

Puis : « Fais la vidéo de la prochaine histoire du backlog ». Le détail est dans [`tiktok/LISEZ-MOI.md`](tiktok/LISEZ-MOI.md).

## Contenu

| Dossier | Contenu |
|---|---|
| [`tiktok/`](tiktok/) | Kit « Pourtant c'est vrai » : usine à TikToks d'histoires vraies (Remotion + edge-tts + Wikimedia Commons, 100 % gratuit), avec sa skill, sa stratégie, 100 idées et 3 histoires d'exemple |
| [`skills/filmcraft/`](skills/filmcraft/) | Skill de montage NLE dans FilmCraft : méthode, recettes vérifiées, référence des 710 commandes, 303 effets et 39 préréglages |
| [`skills/anakin-video-creator/`](skills/anakin-video-creator/) | Skill de vidéos YouTube Remotion à ma charte (devlog, tutos, shorts). C'est un exemple de skill de marque, à adapter à la tienne |
| [`filmcraft-mcp/`](filmcraft-mcp/) | Lanceur FilmCraft (canal de contrôle + jeton) et MCP compagnon `filmcraft-assist` : Whisper large GPU, beats musicaux, QC d'export, planches contact, conformation VFR |
| [`docs/`](docs/) | Guide de prompts Remotion |
| [`setup/`](setup/) | Installeur |

## Les outils et quand les utiliser

| Outil | Stack | Quand | Installation |
|---|---|---|---|
| **Remotion** | React/TS | Vidéos composées par code : intros, slides, shorts | `setup\install.ps1` (skills) ; un projet : `npm create video@latest` |
| **HyperFrames** (HeyGen) | HTML + GSAP | Motion graphics, sous-titres karaoké, explainers | `-WithHyperFrames`, ou dans Claude : `/plugin marketplace add heygen-com/hyperframes` puis `/plugin install hyperframes@hyperframes` |
| **motion-design** (howseen-ai) | HTML `seek(t)` + Playwright + ffmpeg | Films de lancement calés sur le beat, motion blur | Voir [howseen-ai/claude-motion-design](https://github.com/howseen-ai/claude-motion-design). Écrit pour la marque Howseen et macOS : garder le pipeline, changer la charte |
| **video-use** (browser-use) | Python + ffmpeg + ElevenLabs Scribe | Montage de rushes réels : coupe des « euh » et des blancs, étalonnage, sous-titres | `git clone https://github.com/browser-use/video-use`, puis `mklink /J "%USERPROFILE%\.claude\skills\video-use" <chemin>\video-use` ; clé `ELEVENLABS_API_KEY` dans `video-use\.env` |
| **FilmCraft** | NLE Rust + 2 MCP | Montage classique : timeline, dérush par transcription, Lumetri, mixage, export -14 LUFS | `-WithFilmCraft` (détails dans [`filmcraft-mcp/README.md`](filmcraft-mcp/README.md)) |

## Mises à jour

- Skills Remotion : `npx skills update -g`
- Remotion dans un projet : `npm i --save-exact remotion@latest @remotion/cli@latest @remotion/transitions@latest` (`npx remotion upgrade` plante sous Windows)
- HyperFrames : mise à jour automatique via `/plugin` → Marketplaces
- video-use : `git -C video-use pull --ff-only`
- FilmCraft : voir la section « Mise à jour » de `skills/filmcraft/SKILL.md` (la skill est écrite pour la 0.13.0)

## Pièges connus (Windows)

- **Vieux ffmpeg sur le PATH** (certains paquets Python en installent un de 2013, sans libx264) : installer `winget install Gyan.FFmpeg`. Les pipelines prennent celui de WinGet en priorité, et la variable `FFMPEG=` en impose un autre.
- **FilmCraft** n'ouvre son canal de contrôle que lancé par le raccourci « FilmCraft » (`FilmCraftClaude.exe`). Après un changement de jeton : `/mcp` → reconnecter `filmcraft`.
- **Console en cp1252** : `UnicodeEncodeError` sur un emoji → `python -X utf8`.

## Sécurité

Aucun secret dans ce dépôt. Le jeton FilmCraft est généré en local (`%LOCALAPPDATA%\FilmCraft-Claude\control.token`), et les clés API (ElevenLabs…) vont dans des `.env` ignorés par git.

## Crédits

[Remotion](https://www.remotion.dev) · [HyperFrames](https://github.com/heygen-com/hyperframes) · [claude-motion-design](https://github.com/howseen-ai/claude-motion-design) · [video-use](https://github.com/browser-use/video-use) · [FilmCraft](https://github.com/storytold/filmcraft) · musiques de Kevin MacLeod (CC BY 4.0) · images de Wikimedia Commons (crédits par vidéo).
