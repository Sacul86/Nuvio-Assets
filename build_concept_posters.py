"""
build_concept_posters.py — portrait real posters (title already printed, no
gold) for the concept collections. Brands and franchises are left landscape.

  Genres/Themes/Decades      -> curated iconic title's official poster
  Anime/Trending/New/Kids    -> representative title's official poster
  Actors/Directors           -> clean headshot portrait (name shows as caption)
Writes assets/poster/<slug>.jpg.  Usage: python build_concept_posters.py <profile.json>
"""
import sys
import time
import json
from pathlib import Path
from PIL import Image

import build_portrait as bp
import build_portrait_clean as c
import build_final as F

OUT = Path("assets/poster")
OUT.mkdir(parents=True, exist_ok=True)
W780 = "https://image.tmdb.org/t/p/w780"
PEOPLE = {"Actors", "Directors"}
SKIP = {"Networks", "Studios", "Streaming",
        "Film Collections", "TV Collections", "Anime Franchises"}
used = set()


def default_poster(mt, tid):
    """The primary poster (has the title printed on it)."""
    try:
        pp = c.get_json(f"{mt}/{tid}").get("poster_path")
    except Exception:
        pp = None
    if pp and pp not in used:
        used.add(pp)
        return pp
    # fall back to any poster for that title
    try:
        for p in c.get_json(f"{mt}/{tid}/images").get("posters", []):
            if p["file_path"] not in used:
                used.add(p["file_path"])
                return p["file_path"]
    except Exception:
        pass
    return None


def resolve_img(coll, ttl, slug):
    if coll in PEOPLE:
        r = c.person_profile(ttl)          # ('profile', path) — clean headshot
        return r[1] if r else None
    res = F.curated_pick(*F.CURATED[slug]) if slug in F.CURATED else c.resolve(coll, ttl, slug)
    if not res:
        return None
    if res[0] == "profile":
        return res[1]
    return default_poster(*res)


def main():
    data = json.load(open(sys.argv[1]))
    jobs = [(cc["title"], f["title"], bp.slug_of(f))
            for cc in data for f in cc["folders"]
            if cc["title"] not in SKIP and bp.slug_of(f)]
    print(f"Building {len(jobs)} concept posters → {OUT}/\n")
    ok = miss = 0
    for coll, ttl, slug in jobs:
        try:
            path = resolve_img(coll, ttl, slug)
            if not path:
                print(f"  [MISS] {coll}/{ttl}")
                miss += 1
                continue
            raw = bp.S.get(W780 + path, timeout=30)
            raw.raise_for_status()
            tmp = OUT / f".{slug}.src"
            tmp.write_bytes(raw.content)
            bp.cover_crop(Image.open(tmp)).save(OUT / f"{slug}.jpg", "JPEG", quality=90)  # no label
            tmp.unlink(missing_ok=True)
            ok += 1
            if ok % 40 == 0:
                print(f"  ... {ok} done")
        except Exception as e:
            print(f"  [err] {slug}: {e}")
            miss += 1
        time.sleep(0.1)
    print(f"\nDone. {ok} ready, {miss} missed.")


if __name__ == "__main__":
    main()
