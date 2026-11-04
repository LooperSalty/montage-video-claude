"""Rend une histoire avec Remotion puis normalise le son à -14 LUFS (cible TikTok).

Usage : python -I pipeline/render.py <id> [<id> ...] [--skip-render]
Sortie : exports/<id>/<id>.mp4 (H.264 + AAC 48 kHz, faststart)
"""
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STUDIO = ROOT / "studio"
TARGET_LUFS = -14.0
TRUE_PEAK = -2.0  # marge : l'encodage AAC remonte le pic de ~0,3 dB
LRA = 11.0
VIDEO_MAXRATE = "12M"  # ~100 Mo pour 70 s, sous la limite d'upload de l'appli TikTok
VIDEO_BUFSIZE = "24M"

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_story import FFMPEG  # noqa: E402  (même résolution de ffmpeg récent)


def remotion_render(story_id: str) -> Path:
    raw = STUDIO / "out" / f"{story_id}_raw.mp4"
    raw.parent.mkdir(exist_ok=True)
    cmd = ["npx", "remotion", "render", "src/index.ts", story_id, str(raw),
           "--codec=h264", "--crf=17", "--audio-bitrate=320k", "--log=error"]
    subprocess.run(cmd, cwd=STUDIO, check=True, shell=sys.platform == "win32")
    return raw


def measure_loudness(src: Path) -> dict:
    af = f"loudnorm=I={TARGET_LUFS}:TP={TRUE_PEAK}:LRA={LRA}:print_format=json"
    proc = subprocess.run([FFMPEG, "-hide_banner", "-i", str(src), "-af", af, "-f", "null", "-"],
                          capture_output=True, text=True, encoding="utf-8", errors="replace")
    match = re.search(r"\{[^{}]*\"input_i\"[^{}]*\}", proc.stderr)
    if not match:
        raise RuntimeError(f"Mesure loudnorm impossible :\n{proc.stderr[-800:]}")
    return json.loads(match.group(0))


def resample_filter() -> str:
    """loudnorm sort en 192 kHz : le rééchantillonneur par défaut recrée un pic (~-0,9 dBTP mesuré),
    soxr haute précision le garde sous -1,5 dBTP. Repli sur le défaut si ffmpeg est compilé sans soxr."""
    build = subprocess.run([FFMPEG, "-hide_banner", "-version"], capture_output=True, text=True, check=False,
                           encoding="utf-8", errors="replace").stdout
    soxr = ":resampler=soxr:precision=28" if "--enable-libsoxr" in build else ""
    if not soxr:
        print("  ! ffmpeg sans libsoxr : true peak possiblement au-dessus de -1 dBTP", file=sys.stderr)
    return f",aresample=48000{soxr}"


def normalize(src: Path, dest: Path) -> None:
    m = measure_loudness(src)
    af = (f"loudnorm=I={TARGET_LUFS}:TP={TRUE_PEAK}:LRA={LRA}:measured_I={m['input_i']}"
          f":measured_TP={m['input_tp']}:measured_LRA={m['input_lra']}"
          f":measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true"
          f"{resample_filter()}")
    dest.parent.mkdir(parents=True, exist_ok=True)
    # Débit plafonné : le grain argentique fait exploser la taille (450 Mo en CRF 17).
    video = ["-c:v", "libx264", "-preset", "slow", "-crf", "19", "-maxrate", VIDEO_MAXRATE,
             "-bufsize", VIDEO_BUFSIZE, "-pix_fmt", "yuv420p", "-profile:v", "high"]
    cmd = [FFMPEG, "-y", "-hide_banner", "-loglevel", "error", "-i", str(src), *video,
           "-af", af, "-ar", "48000", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(dest)]
    subprocess.run(cmd, check=True)
    print(f"  loudness avant : {m['input_i']} LUFS -> cible {TARGET_LUFS} LUFS")


def main() -> None:
    skip_render = "--skip-render" in sys.argv  # ré-encode seulement studio/out/<id>_raw.mp4
    ids = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not ids:
        sys.exit(__doc__)
    for story_id in ids:
        print(f"== rendu {story_id}")
        raw = STUDIO / "out" / f"{story_id}_raw.mp4" if skip_render else remotion_render(story_id)
        if not raw.exists():
            sys.exit(f"Rendu brut introuvable : {raw} (relancer sans --skip-render)")
        final = ROOT / "exports" / story_id / f"{story_id}.mp4"
        normalize(raw, final)
        print(f"OK {final}")


if __name__ == "__main__":
    main()
