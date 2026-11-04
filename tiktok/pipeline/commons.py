"""Recherche et téléchargement d'images libres sur Wikimedia Commons (sans clé API).

Usage :
  python -I commons.py search <dossier_sortie> "requête 1" "requête 2" ...
      -> candidats.json + planche_XX.jpg (vignettes numérotées) pour choisir.
  python -I commons.py fetch <dossier_sortie> <fichier_selection.json>
      selection = [{"title": "File:...", "name": "lustig"}, ...]
      -> <name>.jpg (1600 px de large max) + credits.json
"""
import json
import sys
import time
from io import BytesIO
from pathlib import Path

import requests
from PIL import Image, ImageDraw, ImageFont

API = "https://commons.wikimedia.org/w/api.php"
HEADERS = {"User-Agent": "PourtantCestVraiPipeline/1.0 (personal video project; python-requests)"}
FREE_HINTS = ("public domain", "pd", "cc0", "cc by", "cc-by", "no restrictions")
THUMB_W = 300


def _strip_html(text: str) -> str:
    out, depth = [], 0
    for ch in text or "":
        if ch == "<":
            depth += 1
        elif ch == ">":
            depth = max(0, depth - 1)
        elif depth == 0:
            out.append(ch)
    return "".join(out).strip()


MAX_WAIT_S = 60  # au-delà, on abandonne ce lien plutôt que d'attendre 10 min
# Tailles de vignettes pré-générées par Wikimedia : bien moins limitées que les originaux.
STANDARD_WIDTHS = (1920, 1280, 960, 500, 330)


def _get(url: str, params: dict | None = None, timeout: int = 60, attempts: int = 6) -> requests.Response:
    """GET avec attente progressive sur 429 (respecte Retry-After, plafonné)."""
    for attempt in range(attempts):
        resp = requests.get(url, params=params, headers=HEADERS, timeout=timeout)
        if resp.status_code != 429:
            resp.raise_for_status()
            return resp
        wait = int(resp.headers.get("Retry-After", 0) or 0) or 5 * (attempt + 1)
        if wait > MAX_WAIT_S:
            break
        print(f"  429, attente {wait}s…", file=sys.stderr)
        time.sleep(wait)
    raise RuntimeError(f"Trop de requêtes (429) : {url}")


def _best_width(width: int) -> int | None:
    """Plus grande vignette standard strictement plus petite que l'original."""
    return next((w for w in STANDARD_WIDTHS if w < width), None)


def _fetch_best(title: str) -> tuple[dict, Image.Image]:
    """Original pour les petites images (1 essai), sinon vignette standard la plus grande."""
    base = {"action": "query", "titles": title, "prop": "imageinfo", "iiprop": "url|extmetadata|size"}
    pages = _api(base).get("query", {}).get("pages", [])
    desc = _describe(pages[0]) if pages else None
    if not desc:
        raise ValueError("introuvable ou licence non libre")
    if desc["width"] <= 1280:
        try:
            return desc, Image.open(BytesIO(_get(desc["url"], attempts=1).content)).convert("RGB")
        except Exception as err:
            print(f"  original refusé ({err}), repli sur vignette", file=sys.stderr)
    width = _best_width(desc["width"])
    if width is None:
        raise ValueError("image trop petite et original indisponible")
    pages = _api({**base, "iiurlwidth": str(width)}).get("query", {}).get("pages", [])
    return desc, _download(pages[0]["imageinfo"][0]["thumburl"])


def _api(params: dict) -> dict:
    base = {"format": "json", "formatversion": "2"}
    return _get(API, {**base, **params}, timeout=30).json()


def _describe(page: dict) -> dict | None:
    infos = page.get("imageinfo") or []
    if not infos:
        return None
    info = infos[0]
    meta = info.get("extmetadata", {})
    license_name = meta.get("LicenseShortName", {}).get("value", "")
    if not any(h in license_name.lower() for h in FREE_HINTS):
        return None
    return {
        "title": page["title"],
        "width": info.get("width"),
        "height": info.get("height"),
        "thumb": info.get("thumburl"),
        "url": info.get("url"),
        "license": license_name,
        "artist": _strip_html(meta.get("Artist", {}).get("value", "")),
        "page": info.get("descriptionurl"),
    }


def search(query: str, limit: int = 12) -> list[dict]:
    data = _api({
        "action": "query", "generator": "search", "gsrsearch": f"{query} filetype:bitmap",
        "gsrnamespace": "6", "gsrlimit": str(limit), "prop": "imageinfo",
        "iiprop": "url|extmetadata|size", "iiurlwidth": str(THUMB_W),
    })
    pages = data.get("query", {}).get("pages", [])
    pages = sorted(pages, key=lambda p: p.get("index", 0))
    return [d for d in (_describe(p) for p in pages) if d]


def _download(url: str) -> Image.Image:
    return Image.open(BytesIO(_get(url).content)).convert("RGB")


def contact_sheet(cands: list[dict], out: Path, cols: int = 6) -> None:
    cell_h = 340
    rows = (len(cands) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * THUMB_W, rows * cell_h), "black")
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.load_default(size=28)
    for i, cand in enumerate(cands):
        time.sleep(0.2)  # politesse envers l'API (évite les 429)
        try:
            img = _download(cand["thumb"])
        except Exception as err:  # vignette illisible : on la signale et on continue
            print(f"  vignette {cand['i']} ignorée : {err}", file=sys.stderr)
            continue
        img.thumbnail((THUMB_W, cell_h - 10))
        x, y = (i % cols) * THUMB_W, (i // cols) * cell_h
        sheet.paste(img, (x, y))
        draw.rectangle([x, y, x + 56, y + 36], fill="red")
        draw.text((x + 6, y + 2), str(cand["i"]), fill="white", font=font)
    sheet.save(out, quality=85)


def cmd_search(out_dir: Path, queries: list[str]) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    seen, cands = set(), []
    for q in queries:
        for cand in search(q):
            if cand["title"] not in seen:
                seen.add(cand["title"])
                cands.append({**cand, "query": q})
    indexed = [{**c, "i": i} for i, c in enumerate(cands)]
    (out_dir / "candidats.json").write_text(json.dumps(indexed, ensure_ascii=False, indent=1), "utf-8")
    for start in range(0, len(indexed), 36):
        chunk = indexed[start:start + 36]
        sheet = out_dir / f"planche_{start // 36:02d}.jpg"
        contact_sheet(chunk, sheet)
        print(sheet)
    for c in indexed:
        print(f"{c['i']:3d} | {c['width']}x{c['height']} | {c['license'][:14]:14} | {c['title'][5:80]}")


def cmd_fetch(out_dir: Path, selection_file: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    selection = json.loads(selection_file.read_text("utf-8"))
    credits_path = out_dir / "credits.json"
    previous = json.loads(credits_path.read_text("utf-8")) if credits_path.exists() else []
    done = {c["file"]: c for c in previous if (out_dir / c["file"]).exists()}
    failures = []
    for item in selection:
        dest = out_dir / f"{item['name']}.jpg"
        if dest.name in done:
            continue  # reprise : déjà téléchargé avec ses crédits
        try:
            desc, img = _fetch_best(item["title"])
        except Exception as err:
            failures.append(item["title"])
            print(f"ÉCHEC {item['title']} : {err}", file=sys.stderr)
            continue
        img.save(dest, quality=92)
        done[dest.name] = {"file": dest.name, **{k: desc[k] for k in ("title", "license", "artist", "page")}}
        print(f"OK {dest.name} {img.size} {desc['license']}")
        time.sleep(1.5)
    credits_path.write_text(json.dumps(list(done.values()), ensure_ascii=False, indent=1), "utf-8")
    if failures:
        sys.exit(f"{len(failures)} échec(s) : relancer la même commande pour reprendre.")


if __name__ == "__main__":
    if len(sys.argv) < 4 or sys.argv[1] not in ("search", "fetch"):
        sys.exit(__doc__)
    target = Path(sys.argv[2])
    if sys.argv[1] == "search":
        cmd_search(target, sys.argv[3:])
    else:
        cmd_fetch(target, Path(sys.argv[3]))
