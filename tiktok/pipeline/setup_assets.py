"""Prépare les assets partagés du studio Remotion (à lancer une fois).

Copie polices, effets sonores et musiques (CC BY, Kevin MacLeod) depuis le PackMontage,
et génère la texture de grain argentique.
Usage : python -I pipeline/setup_assets.py
"""
import json
import random
import shutil
import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
PUBLIC = ROOT / "studio" / "public"
PACK = ROOT.parent / "PackMontage" / "Mx6's Editing Pack"
AUDIO = PACK / "Audio"
MUSICS = AUDIO / "Musics (credit the music, highly recommended)"
SFX = AUDIO / "Sounds Effects"

FONTS = {
    "Montserrat-Black.ttf": PACK / "Fonts" / "Montserrat" / "Montserrat-Black.ttf",
    "Montserrat-ExtraBold.ttf": PACK / "Fonts" / "Montserrat" / "Montserrat-ExtraBold.ttf",
}
SOUNDS = {
    "whoosh.mp3": SFX / "3 - Transitions & Whoosh" / "Whoosh" / "Normal Whoosh" / "Whoosh - Fast (3).mp3",
    "whoosh2.mp3": SFX / "3 - Transitions & Whoosh" / "Whoosh" / "Normal Whoosh" / "Whoosh - Fast - Reverb.mp3",
    "impact.mp3": SFX / "2 - Appearance" / "Impacts" / "Impact - Boom - Cinematic.mp3",
    "hit.mp3": SFX / "2 - Appearance" / "Hits" / "Hit - Long - Reverb.mp3",
    "stamp.mp3": SFX / "2 - Appearance" / "Hits" / "Tap - Reverb.mp3",
    "cash.mp3": SFX / "Objects" / "Money - Cash" / "Money - Cash Register.mp3",
}
# Musiques Kevin MacLeod : licence CC BY 4.0, crédit obligatoire (repris dans post.txt).
MUSIC = {
    "investigations.mp3": (MUSICS / "Lively" / "Artists" / "Kevin MacLeod" / "Kevin MacLeod - Investigations.mp3", "Investigations"),
    "lightless_dawn.mp3": (MUSICS / "Horror & Stress" / "Kevin MacLeod" / "Horror - Kevin MacLeod - Lightless Dawn.mp3", "Lightless Dawn"),
    "sneaky_snitch.mp3": (MUSICS / "Lively" / "Artists" / "Kevin MacLeod" / "Kevin MacLeod -  Sneaky Snitch.mp3", "Sneaky Snitch"),
}


def copy_all(mapping: dict, dest_dir: Path) -> list[str]:
    dest_dir.mkdir(parents=True, exist_ok=True)
    missing = []
    for name, src in mapping.items():
        if (dest_dir / name).exists():
            continue  # déjà fourni (kit partagé) : le PackMontage n'est pas nécessaire
        if not src.exists():
            missing.append(str(src))
            continue
        shutil.copy2(src, dest_dir / name)
    return missing


def make_grain(path: Path, size: int = 512, seed: int = 7) -> None:
    rng = random.Random(seed)
    img = Image.new("L", (size, size))
    img.putdata([max(0, min(255, int(rng.gauss(128, 42)))) for _ in range(size * size)])
    img.save(path)


def main() -> None:
    missing = copy_all(FONTS, PUBLIC / "fonts")
    missing += copy_all(SOUNDS, PUBLIC / "sfx")
    missing += copy_all({k: v[0] for k, v in MUSIC.items()}, PUBLIC / "music")
    credits = {k: f"« {v[1]} » – Kevin MacLeod (incompetech.com), licence CC BY 4.0" for k, v in MUSIC.items()}
    (PUBLIC / "music" / "credits.json").write_text(json.dumps(credits, ensure_ascii=False, indent=1), "utf-8")
    (PUBLIC / "fx").mkdir(parents=True, exist_ok=True)
    make_grain(PUBLIC / "fx" / "grain.png")
    if missing:
        sys.exit("Fichiers introuvables :\n" + "\n".join(missing))
    print("Assets partagés prêts dans", PUBLIC)


if __name__ == "__main__":
    main()
