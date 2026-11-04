"""Construit la voix off (edge-tts) et la timeline Remotion d'une histoire.

Usage : python -I pipeline/build_story.py <id>
Entrée : stories/<id>.json + studio_assets/<id>/*.jpg (+ credits.json)
Sortie : studio/public/stories/<id>/{voice.wav, timeline.json, img/} + exports/<id>/post.txt
"""
import asyncio
import hashlib
import json
import re
import shutil
import subprocess
import sys
import unicodedata
import wave
from pathlib import Path

import edge_tts
from PIL import Image, ImageEnhance, ImageFilter, ImageOps

ROOT = Path(__file__).resolve().parent.parent
PUBLIC = ROOT / "studio" / "public"
SAMPLE_RATE = 48000
DEFAULT_GAP_S = 0.2       # silence après chaque phrase
TAIL_MS = 1900            # durée de l'outro « Pourtant c'est vrai »
DEFAULT_STAMP_DELAY_MS = 300
AUTO_WHOOSH_VOLUME = 0.28


def find_ffmpeg() -> str:
    """Préfère ffmpeg récent (WinGet) : une copie de 2013 traîne dans Python312/Scripts."""
    import os
    candidates = [os.environ.get("FFMPEG"),
                  str(Path.home() / "AppData/Local/Microsoft/WinGet/Links/ffmpeg.exe"),
                  shutil.which("ffmpeg")]
    for cand in candidates:
        if cand and Path(cand).exists():
            return cand
    sys.exit("ffmpeg introuvable : installer avec « winget install Gyan.FFmpeg »")


FFMPEG = find_ffmpeg()


def norm(text: str) -> str:
    text = unicodedata.normalize("NFKD", text.lower())
    return "".join(ch for ch in text if ch.isalnum())


async def _tts(text: str, voice: str, rate: str, mp3: Path) -> list[dict]:
    comm = edge_tts.Communicate(text, voice, rate=rate, boundary="WordBoundary")
    audio, words = bytearray(), []
    async for chunk in comm.stream():
        if chunk["type"] == "audio":
            audio.extend(chunk["data"])
        elif chunk["type"] == "WordBoundary":
            start = chunk["offset"] / 10_000  # unités de 100 ns -> ms
            words.append({"text": chunk["text"], "startMs": round(start),
                          "endMs": round(start + chunk["duration"] / 10_000)})
    if not audio or not words:
        raise RuntimeError(f"TTS vide pour : {text[:40]}…")
    mp3.write_bytes(bytes(audio))
    return words


def synth_beat(text: str, voice: str, rate: str, mp3: Path) -> list[dict]:
    """Synthèse avec cache (clé = voix + débit + texte) et 3 tentatives réseau."""
    key = hashlib.sha1(f"{voice}|{rate}|{text}".encode()).hexdigest()
    meta = mp3.with_suffix(".json")
    if mp3.exists() and meta.exists():
        cached = json.loads(meta.read_text("utf-8"))
        if cached.get("key") == key:
            return cached["words"]
    last_err = None
    for _ in range(3):
        try:
            words = asyncio.run(_tts(text, voice, rate, mp3))
            meta.write_text(json.dumps({"key": key, "words": words}, ensure_ascii=False), "utf-8")
            return words
        except Exception as err:  # réseau instable : on retente
            last_err = err
    raise RuntimeError(f"edge-tts a échoué 3 fois : {last_err}")


def decode_with_gap(mp3: Path, wav: Path, gap_s: float) -> None:
    cmd = [FFMPEG, "-y", "-loglevel", "error", "-i", str(mp3), "-ar", str(SAMPLE_RATE),
           "-ac", "1", "-af", f"apad=pad_dur={gap_s}", str(wav)]
    subprocess.run(cmd, check=True)


def concat_wavs(parts: list[Path], out: Path, tail_ms: int) -> list[int]:
    """Concatène à l'échantillon près et renvoie le début (ms) de chaque partie."""
    starts, total = [], 0
    with wave.open(str(out), "wb") as dst:
        dst.setnchannels(1)
        dst.setsampwidth(2)
        dst.setframerate(SAMPLE_RATE)
        for part in parts:
            with wave.open(str(part), "rb") as src:
                starts.append(round(total * 1000 / SAMPLE_RATE))
                frames = src.readframes(src.getnframes())
                dst.writeframes(frames)
                total += src.getnframes()
        silence = int(SAMPLE_RATE * tail_ms / 1000)
        dst.writeframes(b"\x00\x00" * silence)
        total += silence
    return starts + [round(total * 1000 / SAMPLE_RATE)]


def find_word_ms(words: list[dict], target: str | None, fallback: int) -> int:
    if not target:
        return fallback
    key = norm(re.split(r"[\s\-']", target)[0])
    for w in words:
        if norm(w["text"]) == key:
            return w["startMs"]
    for w in words:  # ex. edge-tts fusionne parfois « 7000 tonnes » en un seul mot
        token = norm(w["text"])
        if token.startswith(key) or key in token or key.startswith(token or "#"):
            return w["startMs"]
    print(f"  ! mot « {target} » introuvable, tampon placé par défaut", file=sys.stderr)
    return fallback


def prepare_image(story_id: str, name: str, cache: dict) -> dict:
    if name in cache:
        return cache[name]
    src = ROOT / "studio_assets" / story_id / f"{name}.jpg"
    if not src.exists():
        raise FileNotFoundError(f"Image manquante : {src} (relancer commons.py fetch)")
    dest_dir = PUBLIC / "stories" / story_id / "img"
    dest_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest_dir / f"{name}.jpg")
    with Image.open(src) as img:
        w, h = img.size
        bg = ImageOps.fit(img.convert("RGB"), (540, 960)).filter(ImageFilter.GaussianBlur(18))
        ImageEnhance.Brightness(bg).enhance(0.5).save(dest_dir / f"{name}_bg.jpg", quality=85)
    base = f"stories/{story_id}/img/{name}"
    cache[name] = {"src": f"{base}.jpg", "bg": f"{base}_bg.jpg", "w": w, "h": h}
    return cache[name]


def build_beats(story: dict, voice_dir: Path) -> tuple[list[dict], list[int]]:
    words_per_beat, wavs = [], []
    for i, beat in enumerate(story["beats"]):
        mp3 = voice_dir / f"beat_{i:02d}.mp3"
        print(f"  voix {i + 1}/{len(story['beats'])}")
        words_per_beat.append(synth_beat(beat["text"], story["voice"], story.get("rate", "+0%"), mp3))
        wav = mp3.with_suffix(".wav")
        decode_with_gap(mp3, wav, beat.get("gap", DEFAULT_GAP_S))
        wavs.append(wav)
    starts = concat_wavs(wavs, voice_dir.parent / "voice.wav", TAIL_MS)
    return words_per_beat, starts


def make_timeline(story: dict, words_per_beat: list[list[dict]], starts: list[int]) -> dict:
    sid, images, beats = story["id"], {}, []
    for i, beat in enumerate(story["beats"]):
        t0 = starts[i]
        words = [{**w, "startMs": w["startMs"] + t0, "endMs": w["endMs"] + t0} for w in words_per_beat[i]]
        default_at = t0 + DEFAULT_STAMP_DELAY_MS
        stamp = beat.get("stamp")
        sfx = [{"src": s["src"], "volume": s.get("volume", 0.5),
                "atMs": find_word_ms(words, s.get("on"), t0)} for s in beat.get("sfx", [])]
        if i > 0 and beat["img"] != story["beats"][i - 1]["img"]:
            sfx.append({"src": "sfx/whoosh.mp3", "volume": AUTO_WHOOSH_VOLUME, "atMs": max(0, t0 - 120)})
        beats.append({
            "i": i, "startMs": t0, "endMs": starts[i + 1] if i + 1 < len(story["beats"]) else starts[-1] - TAIL_MS,
            "img": prepare_image(sid, beat["img"], images), "mode": beat.get("mode", "cover"),
            "focus": beat.get("focus", [0.5, 0.5]), "label": beat.get("label"),
            "grade": beat.get("grade", story.get("grade", "archive")),
            "stamp": {"text": stamp["text"], "atMs": find_word_ms(words, stamp.get("on"), default_at)} if stamp else None,
            "sfx": sfx, "words": words,
        })
    duration = starts[-1]
    return {
        "id": sid, "episode": story["episode"], "title": story["title"], "fps": 30,
        "durationMs": duration, "grade": story.get("grade", "archive"),
        "hook": {"lines": story["hook"], "endMs": beats[0]["endMs"]},
        "music": story["music"], "voice": f"stories/{sid}/voice.wav",
        "outro": {"startMs": duration - TAIL_MS, "text": "POURTANT C'EST VRAI"},
        "beats": beats,
    }


def write_post(story: dict) -> Path:
    sid = story["id"]
    img_credits = json.loads((ROOT / "studio_assets" / sid / "credits.json").read_text("utf-8"))
    music_credits = json.loads((PUBLIC / "music" / "credits.json").read_text("utf-8"))
    used = {b["img"] for b in story["beats"]}
    lines = [f"{story['post']['caption']}", "", " ".join(story["post"]["hashtags"]), "",
             "— COMMENTAIRE ÉPINGLÉ —", "📚 Sources :", *story["post"]["sources"], "",
             "🎵 " + music_credits[Path(story["music"]["src"]).name], "📷 Images (Wikimedia Commons) :"]
    for c in img_credits:
        if Path(c["file"]).stem in used:
            artist = (c["artist"] or "auteur inconnu")[:60]
            lines.append(f"- {c['title'][5:]} – {artist} – {c['license']}")
    out = ROOT / "exports" / sid / "post.txt"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines) + "\n", "utf-8")
    description = f"{story['post']['caption']}\n\n📌 Sources en commentaire\n\n{' '.join(story['post']['hashtags'])}\n"
    (out.parent / "description.txt").write_text(description, "utf-8")
    return out


def main() -> None:
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    story = json.loads((ROOT / "stories" / f"{sys.argv[1]}.json").read_text("utf-8"))
    voice_dir = PUBLIC / "stories" / story["id"] / "voice"
    voice_dir.mkdir(parents=True, exist_ok=True)
    words_per_beat, starts = build_beats(story, voice_dir)
    timeline = make_timeline(story, words_per_beat, starts)
    out = PUBLIC / "stories" / story["id"] / "timeline.json"
    out.write_text(json.dumps(timeline, ensure_ascii=False, indent=1), "utf-8")
    print(f"OK {out} — durée {timeline['durationMs'] / 1000:.1f} s — post : {write_post(story)}")


if __name__ == "__main__":
    main()
