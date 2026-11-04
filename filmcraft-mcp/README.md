# filmcraft-mcp — FilmCraft piloté par Claude Code

[FilmCraft](https://github.com/storytold/filmcraft) (NLE open source en Rust) installé sous Windows,
plus de quoi le piloter depuis Claude Code avec une qualité de montage pro.

## Ce qui est en place

| Pièce | Rôle |
|---|---|
| `%LOCALAPPDATA%\Programs\FilmCraft\` | FilmCraft 0.13.0 portable (`filmcraft.exe`, `filmcraft-cli.exe`) |
| Raccourci bureau **FilmCraft** | → `launcher\FilmCraftClaude.exe` : lance FilmCraft avec le canal de contrôle `127.0.0.1:9876` + jeton. Glisser un `.fcproj` ou des médias dessus les ouvre (dans l'instance déjà ouverte si besoin). |
| MCP **`filmcraft`** | Serveur MCP officiel de FilmCraft en mode pont (`launcher\filmcraft-bridge.cmd`) : 700+ commandes, inspection, rendu d'image, clics/captures de l'UI |
| MCP **`filmcraft-assist`** | `server\` (Python, uv) : ce qui manque à FilmCraft — voir ci-dessous |
| Skill **`filmcraft`** | `~\.claude\skills\filmcraft\` : méthode de travail, recettes vérifiées, référence des 710 commandes / 303 effets / 39 préréglages |

### Outils de `filmcraft-assist`

| Outil | Apport |
|---|---|
| `filmcraft_status` / `filmcraft_launch` | État de l'install, lancement de l'appli |
| `media_probe` | Codec, cadence, **VFR** de téléphone, HDR, rotation, 44,1 kHz |
| `media_conform` | Rush VFR → intermédiaire CFR ProRes/DNxHR + PCM 48 kHz (coupes à l'image près) |
| `transcribe_media` | **Whisper large-v3-turbo sur GPU** (faster-whisper), garde les « euh », recolle les élisions, pose la transcription mot à mot dans FilmCraft → `transcript.removeFillers` / `removePauses` / `createCaptions` + SRT |
| `music_beats` | BPM, temps, débuts de mesure (librosa) → marqueurs dans la séquence |
| `export_qc` | Loudness EBU R128, true peak, noirs, images figées, silences, avec la correction à faire |
| `contact_sheet` | Planche contact horodatée d'une vidéo, à relire en une image |

## Utilisation

Dans Claude Code : « monte cette vidéo dans FilmCraft », « coupe les euh et les blancs », « sous-titre et exporte pour YouTube »… La skill `filmcraft` s'active et suit les recettes.

## Tests

```sh
cd server
uv run --group dev pytest -q                                     # fonctions pures
uv run python tests/smoke_mcp.py <video.mp4> <musique.wav> <voix.wav>   # tous les outils via MCP (FilmCraft lancé)
uv run python tests/pipeline_tuto.py <video.mp4> <transcript.json> <sortie>  # recette A complète en headless
```

## Dépannage

- **`filmcraft` déconnecté / « connection refused »** : FilmCraft n'est pas lancé par le raccourci (ou `filmcraft_launch`). Lancé autrement, il n'ouvre pas le canal de contrôle.
- **Jeton** : `%LOCALAPPDATA%\FilmCraft-Claude\control.token` (lisible par ton compte seulement). Pour le changer : le supprimer, relancer FilmCraft par le raccourci, puis `/mcp` → reconnecter `filmcraft`.
- **FilmCraft ne s'ouvre pas** : journal `%LOCALAPPDATA%\Programs\FilmCraft\data\Logs\filmcraft.log` ; essai `$env:WGPU_BACKEND="dx12"`.
- **Recompiler le lanceur** : `C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe /codepage:65001 /target:winexe /win32icon:filmcraft.ico /out:FilmCraftClaude.exe /r:System.Windows.Forms.dll Launcher.cs` dans `launcher\`.
- **Mettre à jour FilmCraft** : voir la skill (`SKILL.md`, section « Mise à jour »).
