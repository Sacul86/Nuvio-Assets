"""
build_franchise_landscape.py — landscape covers for the franchise collections
using TMDB backdrops that have the TITLE baked in (iso_639_1 == 'en'), so no
gold label is needed. Overwrites assets/landscape/<slug>.jpg.

Usage: python build_franchise_landscape.py <profile.json>
"""
import sys
import time
import json
from pathlib import Path
from PIL import Image

import build_portrait as bp
import build_portrait_clean as c
import build_landscape as L

FRANCHISE = {"Film Collections", "TV Collections", "Anime Franchises"}
W1280 = "https://image.tmdb.org/t/p/w1280"
# umbrella "universe" folders with no single titled backdrop -> flagship film
FALLBACK_ID = {"Marvel Cinematic Universe": ("movie", 299534),   # Avengers: Endgame
               "DC Universe": ("movie", 141052)}                 # Justice League
used = set()


def titled_backdrop(mt, tid):
    d = c.get_json(f"{mt}/{tid}/images")
    en = [b for b in d.get("backdrops", [])
          if b.get("iso_639_1") == "en" and b["file_path"] not in used]
    en.sort(key=lambda x: -x.get("vote_average", 0))
    if en:
        used.add(en[0]["file_path"])
        return en[0]["file_path"]
    return None


def resolve(coll, title):
    if title in FALLBACK_ID:
        return FALLBACK_ID[title]
    if coll == "Film Collections":
        for ep in ("search/collection", "search/movie"):
            r = c.items(ep, query=title)
            if r:
                mt = "movie"
                # collection id needs the collection images endpoint
                if ep == "search/collection":
                    cid = r[0]["id"]
                    if titled_backdrop("collection", cid):
                        return ("collection", cid)
                return ("movie", r[0]["id"])
        return None
    q = title.replace(" Universe", "").replace(" TV", "").strip()
    r = c.items("search/tv", query=q) or c.items("search/multi", query=q)
    return ("tv", r[0]["id"]) if r else None


def main():
    data = json.load(open(sys.argv[1]))
    jobs = [(cc["title"], f["title"], bp.slug_of(f))
            for cc in data for f in cc["folders"]
            if cc["title"] in FRANCHISE and bp.slug_of(f)]
    print(f"Building {len(jobs)} franchise landscape titled covers\n")
    ok = miss = 0
    for coll, ttl, slug in jobs:
        try:
            res = resolve(coll, ttl)
            fp = None
            if res:
                fp = titled_backdrop(*res)
                if not fp and res[0] == "collection":            # retry via flagship movie
                    r = c.items("search/movie", query=ttl)
                    if r:
                        fp = titled_backdrop("movie", r[0]["id"])
            if not fp:
                print(f"  [MISS] {coll}/{ttl}")
                miss += 1
                continue
            raw = bp.S.get(W1280 + fp, timeout=30)
            raw.raise_for_status()
            tmp = L.OUT / f".{slug}.src"
            tmp.write_bytes(raw.content)
            L.cover_crop(Image.open(tmp)).save(L.OUT / f"{slug}.jpg", "JPEG", quality=90)  # no label
            tmp.unlink(missing_ok=True)
            ok += 1
        except Exception as e:
            print(f"  [err] {slug}: {e}")
            miss += 1
        time.sleep(0.12)
    print(f"\nDone. {ok} ready, {miss} missed.")


if __name__ == "__main__":
    main()
