# Recettes FilmCraft (charges vérifiées sur FilmCraft 0.13.0)

Notation : `cmd {params}` = `command_run {"id": "cmd", "params": {…}}` sur le MCP `filmcraft`.
Les ids (`item`, `clip`) viennent de `project_inspect` / `sequence_inspect` ou du résultat de la
commande précédente (`file.import` → `items`, `timeline.place` → `clips` [vidéo, audio liée]).
Pipeline A rejouable en headless : `filmcraft-mcp/server/tests/pipeline_tuto.py`.

## A. Tuto / face caméra (YouTube 16:9)

1. `media_probe {paths}` → si `probablyVFR` : `media_conform {path, codec: "prores_lt"}` et utiliser la sortie.
2. `file.newProject {name}` puis `file.saveAs {path: "<dossier>\\<nom>.fcproj"}`.
3. `file.newSequence {name, width: 1920, height: 1080, fps: <cadence des rushes>, sampleRate: 48000}`.
4. `file.import {paths: [...]}` → `items`. `timeline.place {item, track: "V1", seconds: 0}` (plusieurs : `items: [...]` bout à bout).
5. `transcribe_media {path, language: "fr", import_if_missing: false}` (MCP assist) → pose la transcription sur l'élément.
6. Couper : `transcript.removeFillers {fillers: ["euh","heu","euhm","hum","hmm","mmh","bah","ben","beh","hein"]}` puis `transcript.removePauses {minSeconds: 0.6, keepSeconds: 0.15}`. Rythme plus nerveux (short) : `minSeconds: 0.35, keepSeconds: 0.08`.
7. Relire : `transcript.inspect {}`, `transcript.search {query}` ; retirer une phrase ratée : `transcript.lift {from: <idx mot>, to: <idx mot>}` (ripple : `transcript.extract`).
8. Voix : `essentialSound.applyPreset {clips: [ids audio], preset: "Clean Up Noisy Dialogue", type: "dialogue"}` (autres : "Balanced Voice", "Podcast Voice", "Dry Up a Roomy Voice").
9. Sous-titres : `transcript.createCaptions {maxChars: 42, lines: 2}` → piste `C1`. Style lisible : `captions.setStyle {track: "C1", size: 54, color: "#ffffff", outline: 4, outlineColor: "#000000", background: false, anchor: "bottom", margin: 0.08}`.
10. Étalonnage léger (recette D) sur chaque clip vidéo.
11. Export (recette F) puis `export_qc {path, platform: "youtube"}` et `contact_sheet {path}` → Read de la planche.

## B. Short vertical 9:16 (TikTok / Reels / Shorts)

- Séquence : `file.newSequence {name, width: 1080, height: 1920, fps: 30, sampleRate: 48000}` (ou `sequence.settings {width: 1080, height: 1920}` sur une séquence existante).
- Recadrer un rush 16:9 : `clip.fillFrame {clips: [id]}` (remplit en recadrant ; renvoie l'échelle). Décaler le cadre : `effects.setParam {clip, effect: "motion", param: "position", value: [x, y]}`.
- Rythme : recette A étape 6 avec `minSeconds: 0.35, keepSeconds: 0.08`.
- Sous-titres courts et gros : `transcript.createCaptions {maxChars: 18, lines: 2, maxSeconds: 2}` puis `captions.setStyle {track: "C1", size: 80, outline: 6, outlineColor: "#000000", anchor: "middle", margin: 0.0}`.
- Export : préréglage `Social Vertical 1080×1920`, `loudnessLufs: -14`, puis `export_qc {platform: "tiktok"}`.

## C. Montage calé sur la musique (clip, trailer, montage photo)

1. Placer la musique : `timeline.place {item: <musique>, track: "A2", seconds: 0}`.
2. `music_beats {path: <musique>, add_markers: true, every: "bar", offset_seconds: 0, color: "Mango"}` → `bpm`, `times` (débuts de mesure) et marqueurs posés. `every: "half_bar"` pour un rythme plus rapide.
3. Monter plan par plan sur les mesures : pour la mesure i (début `t[i]`, fin `t[i+1]`) :
   `timeline.place {item, track: "V1", seconds: t[i], sourceIn: <ticks du début utile>, duration: <(t[i+1]-t[i]) × 254016000000>, audio: false}`.
   Une coupe sur un plan déjà posé : `timeline.razor {time: <ticks>, track: "V1"}`.
4. Transitions avec parcimonie : `sequence.applyVideoTransition {clip, effect: "cross_dissolve", frames: 12, edge: "in"}`.
5. Musique sous la voix : `essentialSound.setType {clips: [musique], type: "music"}`, `essentialSound.set {clips: [musique], values: {"ducking.enabled": true, "ducking.against": ["Dialogue"], "ducking.reduceDb": -15, "ducking.fadeS": 0.5}}`, puis `essentialSound.generateDucking {clips: [musique]}` (écrit les images clés de volume). Attention : `"Dialogue"` avec majuscule.

## D. Étalonnage (Lumetri)

- `effects.apply {clips: [id], effect: "lumetri"}` puis `effects.setParam {clip, effect: "lumetri", param, value}`.
- Paramètres (bornes) : `temperature`, `tint` [-100..100] ; `exposure` [-5..5] ; `contrast`, `highlights`, `shadows`, `whites`, `blacks` [-100..100] ; `saturation` [0..200, neutre 100] ; `vibrance` [-100..100] ; `look` (choix : None, Teal & Orange, Warm Film, Cool Blue, Bleach Bypass, Faded Matte, Monochrome, Golden Hour, Night) + `look_intensity` [0..200] ; `faded_film` ; `sharpen` ; courbes `curve_luma`, `curve_red`… valeur `[[0,0],[0.25,0.21],[0.75,0.82],[1,1]]` (S douce). Liste complète : grep `` `lumetri` `` dans `effects.md`.
- Point de départ face caméra : `contrast 10–15`, `saturation 105–112`, `vibrance 8–12`, `highlights -10`, `shadows +5`. Peau trop froide : `temperature +5..+10`.
- Raccorder les plans sur une référence : `lumetri.applyMatch {clip, referenceTime: <ticks>, faceDetection: true}`.
- Vérifier, ne pas deviner : `scopes.read {scopes: ["waveform","vectorscopeYuv"], time: <ticks>}` (luma entre ~5 et ~95 %, peaux sur la ligne chair) et `render_frame {seconds}`.
- Diffusion TV : effet `video_limiter` (`clip_level: "100 IRE"`).

## E. Mixage

- Types : `essentialSound.setType {clips, type: "dialogue"|"music"|"sfx"|"ambience"}` puis préréglage `essentialSound.applyPreset`.
- Niveaux relatifs : voix vers -16 à -20 LUFS court terme, musique 15 à 20 dB sous la voix (ducking ci-dessus), effets ponctuels selon le ressenti.
- Gain : `clip.audioGain {clips, mode: "set"|"adjust"|"normalizeMax"|"normalizeAll", db}`.
- Limiteur true peak sur le Mix : `mixer.addInsert {strip: "Mix", effect: "hard_limiter"}` → `{slot}` puis `mixer.setInsert {strip: "Mix", slot, params: {max: -1.0}}`.
- Loudness finale : la régler à l'export (`loudnessLufs`), pas à la main.

## F. Export + contrôle qualité

- `file.exportMedia {path, preset: "YouTube 1080p Full HD", loudnessLufs: -14, wait: true}` (préréglages : `export-presets.md`). Sans préréglage : `format: "h264", crf: 18` ; master : `format: "prores", proresProfile: "hq"`.
- Sous-titres : incrustés `burnCaptions: true`, ou fichier à côté `captionSidecar: "srt"` (préférable pour YouTube : SEO + désactivables).
- Plage : `range: "inOut"|"workArea"|"custom"` + `startSeconds`/`endSeconds`.
- Toujours : `export_qc {path, platform}` → corriger ce qui est « à corriger » → ré-exporter ; puis `contact_sheet {path, count: 12}` et lire l'image.
- Cibles : YouTube/TikTok/Instagram -14 LUFS, podcast -16, TV (EBU R128) -23 ; true peak ≤ -1 dBTP.
