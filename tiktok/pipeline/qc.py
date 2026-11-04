"""Contrôle qualité d'un export TikTok + planche contact (sans outil externe, juste ffmpeg).

Usage : python -I pipeline/qc.py <id> [<id> ...]
Vérifie exports/<id>/<id>.mp4 : 1080x1920, 30 i/s, durée, H.264/AAC 48 kHz, -14 LUFS, true peak, poids.
Sortie : verdict dans le terminal + exports/<id>/planche.jpg (12 images réparties sur la vidéo).
Code de sortie 1 si au moins un contrôle bloquant échoue.
"""
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_story import FFMPEG  # noqa: E402
from render import TARGET_LUFS, measure_loudness  # noqa: E402

WIDTH, HEIGHT, FPS = 1080, 1920, 30
MIN_S, IDEAL_MIN_S, IDEAL_MAX_S = 61.0, 65.0, 75.0  # Creator Rewards : plus d'1 min
LUFS_TOLERANCE = 1.0
MAX_TRUE_PEAK = -1.0
MAX_SIZE_MB = 250  # marge sous la limite d'upload de l'appli TikTok
SHEET_TILES = 12


def find_ffprobe() -> str:
    sibling = Path(FFMPEG).with_name(Path(FFMPEG).name.replace("ffmpeg", "ffprobe"))
    found = str(sibling) if sibling.exists() else shutil.which("ffprobe")
    if not found:
        sys.exit("ffprobe introuvable (il est livré avec ffmpeg)")
    return found


def probe(video: Path) -> dict:
    cmd = [find_ffprobe(), "-v", "error", "-print_format", "json", "-show_streams", "-show_format", str(video)]
    out = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", check=True).stdout
    data = json.loads(out)
    streams = data.get("streams", [])
    return {
        "video": next((s for s in streams if s.get("codec_type") == "video"), {}),
        "audio": next((s for s in streams if s.get("codec_type") == "audio"), {}),
        "duration": float(data.get("format", {}).get("duration", 0)),
        "size_mb": video.stat().st_size / 1_000_000,
    }


def _fps(rate: str) -> float:
    num, _, den = (rate or "0/1").partition("/")
    return float(num) / float(den or 1) if float(den or 1) else 0.0


def run_checks(info: dict, loud: dict) -> list[tuple[str, str, str]]:
    """Renvoie (statut, contrôle, détail) avec statut OK / ATTENTION / ECHEC."""
    v, a, dur = info["video"], info["audio"], info["duration"]
    lufs, peak = float(loud["input_i"]), float(loud["input_tp"])

    def check(ok: bool, name: str, detail: str, blocking: bool = True) -> tuple[str, str, str]:
        return ("OK" if ok else ("ECHEC" if blocking else "ATTENTION"), name, detail)

    return [
        check((v.get("width"), v.get("height")) == (WIDTH, HEIGHT), "Format 9:16", f"{v.get('width')}x{v.get('height')}"),
        check(abs(_fps(v.get("r_frame_rate")) - FPS) < 0.01, "Images/s", v.get("r_frame_rate", "?")),
        # yuvj420p = yuv420p en plage pleine (images JPEG de Remotion) : accepté par TikTok.
        check(v.get("codec_name") == "h264" and v.get("pix_fmt") in ("yuv420p", "yuvj420p"), "Vidéo H.264",
              f"{v.get('codec_name')} {v.get('pix_fmt')}"),
        check(a.get("codec_name") == "aac" and a.get("sample_rate") == "48000", "Audio AAC 48 kHz",
              f"{a.get('codec_name')} {a.get('sample_rate')} Hz"),
        check(dur >= MIN_S, "Durée > 1 min", f"{dur:.1f} s"),
        check(IDEAL_MIN_S <= dur <= IDEAL_MAX_S, "Durée idéale 65-75 s", f"{dur:.1f} s", blocking=False),
        check(abs(lufs - TARGET_LUFS) <= LUFS_TOLERANCE, "Loudness -14 LUFS", f"{lufs:.1f} LUFS"),
        check(peak <= MAX_TRUE_PEAK, "True peak <= -1 dBTP", f"{peak:.1f} dBTP"),
        check(info["size_mb"] <= MAX_SIZE_MB, f"Poids <= {MAX_SIZE_MB} Mo", f"{info['size_mb']:.0f} Mo", blocking=False),
    ]


def contact_sheet(video: Path, duration: float, dest: Path) -> None:
    rate = SHEET_TILES / max(duration, 1.0)
    vf = f"fps={rate:.5f},scale=270:-2,tile=6x2:padding=6:color=white"
    cmd = [FFMPEG, "-y", "-hide_banner", "-loglevel", "error", "-i", str(video), "-vf", vf,
           "-frames:v", "1", "-q:v", "3", str(dest)]
    subprocess.run(cmd, check=True)


def qc(story_id: str) -> bool:
    video = ROOT / "exports" / story_id / f"{story_id}.mp4"
    if not video.exists():
        print(f"ECHEC {story_id} : {video} introuvable (lancer pipeline/render.py {story_id})")
        return False
    info = probe(video)
    results = run_checks(info, measure_loudness(video))
    print(f"== QC {story_id}")
    for status, name, detail in results:
        print(f"  [{status:9}] {name:24} {detail}")
    sheet = video.with_name("planche.jpg")
    contact_sheet(video, info["duration"], sheet)
    print(f"  planche contact : {sheet}")
    return all(status != "ECHEC" for status, _, _ in results)


def main() -> None:
    ids = sys.argv[1:]
    if not ids:
        sys.exit(__doc__)
    verdicts = [qc(story_id) for story_id in ids]
    sys.exit(0 if all(verdicts) else 1)


if __name__ == "__main__":
    main()
