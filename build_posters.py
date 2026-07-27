"""
build_posters.py — real official posters (title already printed on them, no
gold label) for the franchise collections: Film Collections, TV Collections,
Anime Franchises. Portrait 2:3, saved to assets/poster/<slug>.jpg.

Usage:
    export TMDB_API_KEY=your_key
    python build_posters.py <profile.json>
"""
import sys
import time
import json
from pathlib import Path
from PIL import Image

import build_portrait as bp
import build_portrait_clean as c

OUT = Path("assets/poster")
OUT.mkdir(parents=True, exist_ok=True)
W780 = "https://image.tmdb.org/t/p/w780"
PW, PH = 1000, 1500
FRANCHISE = {"Film Collections", "TV Collections", "Anime Franchises"}
used = set()


def first_poster(results):
    for it in results:
        p = it.get("poster_path")
        if p and p not in used:
            used.add(p)
            return p
    return None


def resolve_poster(coll, title):
    if coll == "Film Collections":
        return (first_poster(c.items("search/collection", query=title))
                or first_poster(c.items("search/movie", query=title))
                or first_poster(c.items("search/multi", query=title)))
    q = title.replace(" Universe", "").replace(" TV", "").strip()
    return (first_poster(c.items("search/tv", query=q))
            or first_poster(c.items("search/collection", query=q))
            or first_poster(c.items("search/multi", query=q)))


def fit(im):
    im = im.convert("RGB")
    sw, sh = im.size
    s = max(PW / sw, PH / sh)
    im = im.resize((round(sw * s), round(sh * s)), Image.LANCZOS)
    w, h = im.size
    return im.crop(((w - PW) // 2, (h - PH) // 2, (w - PW) // 2 + PW, (h - PH) // 2 + PH))


def main():
    data = json.load(open(sys.argv[1]))
    jobs = [(cc["title"], f["title"], bp.slug_of(f))
            for cc in data for f in cc["folders"]
            if cc["title"] in FRANCHISE and bp.slug_of(f)]
    print(f"Building {len(jobs)} franchise posters → {OUT}/\n")
    ok = miss = 0
    for coll, ttl, slug in jobs:
        try:
            pp = resolve_poster(coll, ttl)
            if not pp:
                print(f"  [MISS] {coll}/{ttl}")
                miss += 1
                continue
            raw = bp.S.get(W780 + pp, timeout=30)
            raw.raise_for_status()
            tmp = OUT / f".{slug}.src"
            tmp.write_bytes(raw.content)
            fit(Image.open(tmp)).save(OUT / f"{slug}.jpg", "JPEG", quality=90)
            tmp.unlink(missing_ok=True)
            ok += 1
        except Exception as e:
            print(f"  [err] {slug}: {e}")
            miss += 1
        time.sleep(0.1)
    print(f"\nDone. {ok} ready, {miss} missed.")


if __name__ == "__main__":
    main()
