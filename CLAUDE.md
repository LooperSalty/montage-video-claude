# CLAUDE.md

Environnement de montage vidéo piloté par Claude Code : skills, MCP, outils et un kit TikTok prêt à produire.

## Quel outil pour quelle vidéo

| Besoin | Outil | Skill / MCP |
|---|---|---|
| TikTok « histoire vraie » faceless de bout en bout | Kit `tiktok/` (Remotion + edge-tts + Wikimedia) | `pourtant-cest-vrai` (lancer Claude dans `tiktok/`) |
| Vidéo composée par code (intro, slides, shorts, showcase) | Remotion | `/remotion-best-practices` (routeur), `anakin-video-creator` (exemple de skill de marque) |
| Motion graphics HTML/GSAP, sous-titres karaoké, explainers | HyperFrames (plugin) | `/hyperframes` |
| Film de lancement calé sur le beat, motion blur | motion-design (howseen-ai) | `/motion-design` |
| Montage de rushes réels : coupe des « euh », étalonnage, sous-titres | video-use (browser-use) | `/video-use` |
| Montage NLE classique : timeline, dérush, Lumetri, mixage, export -14 LUFS | FilmCraft | skill `filmcraft` + MCP `filmcraft` et `filmcraft-assist` |

## Carte du dépôt

- `tiktok/` : kit autonome, avec son propre `CLAUDE.md`, sa skill et son installeur (`tiktok/LISEZ-MOI.md`).
- `skills/` : skills globales, copiées dans `~/.claude/skills/` par `setup/install.ps1`. `{{DEPOT}}` y est remplacé par le chemin du dépôt à l'installation.
- `filmcraft-mcp/` : lanceur C# (canal de contrôle + jeton) et serveur MCP Python `filmcraft-assist` (uv).
- `docs/instructions_montage.txt` : guide de prompts pour Remotion.

## Conventions

- Français pour les prompts, les commentaires et les messages.
- Formats : 16:9 (YouTube), 9:16 (Reels/TikTok), 1:1 (Instagram). Par défaut : 1920x1080, 30 i/s.
- Mettre les assets (images, audio, logos) dans un dossier `assets/` du projet avant de coder.
- Remotion : versions figées (`--save-exact`). `npx remotion upgrade` plante sous Windows : utiliser `npm i --save-exact remotion@latest @remotion/cli@latest`. Le MCP Remotion est déprécié : utiliser `/remotion-docs`.
- Jamais de secret dans le dépôt : les clés vont dans des `.env` ignorés par git.
