"""
build_all_portrait.py — take every non-franchise collection portrait.

  Networks/Studios/Streaming -> brand logo on a portrait canvas (no label)
  Genres/Themes/Decades      -> curated iconic title, textless portrait + gold
  Actors/Directors           -> headshot portrait + gold
  Anime/Trending/New/Kids    -> representative textless portrait + gold
Franchise collections (Film/TV/Anime Franchises) are left untouched — they
already use real posters in assets/poster/.

Writes assets/portrait/<slug>.jpg.  Usage: python build_all_portrait.py <profile.json>
"""
import sys
import time
import json
from PIL import Image

import build_portrait as bp
import build_portrait_clean as c
import build_final as F

BRAND = {"Networks", "Studios", "Streaming"}
FRANCHISE = {"Film Collections", "TV Collections", "Anime Franchises"}
BRAND_COVER = "https://cdn.xperience-app.com/covers/default/{slug}.webp"


def main():
    data = json.load(open(sys.argv[1]))
    jobs = [(cc["title"], f["title"], bp.slug_of(f))
            for cc in data for f in cc["folders"] if bp.slug_of(f)]
    size = bp.fit_size([t for _, t, _ in jobs])
    todo = [j for j in jobs if j[0] not in FRANCHISE]
    print(f"Building {len(todo)} portrait covers @ font {size}\n")
    ok = miss = 0
    for coll, ttl, slug in todo:
        try:
            if coll in BRAND:
                raw = bp.S.get(BRAND_COVER.format(slug=slug), timeout=30)
                raw.raise_for_status()
                tmp = bp.OUT / f".{slug}.src"
                tmp.write_bytes(raw.content)
                tile = bp.streaming_tile(Image.open(tmp))
                tmp.unlink(missing_ok=True)
            else:
                res = F.curated_pick(*F.CURATED[slug]) if slug in F.CURATED else c.resolve(coll, ttl, slug)
                if not res:
                    print(f"  [MISS] {coll}/{ttl}")
                    miss += 1
                    continue
                url, note = c.image_url(res)
                if not url:
                    print(f"  [MISS] {coll}/{ttl} (no image)")
                    miss += 1
                    continue
                raw = bp.S.get(url, timeout=30)
                raw.raise_for_status()
                tmp = bp.OUT / f".{slug}.src"
                tmp.write_bytes(raw.content)
                base = bp.grade(bp.cover_crop(Image.open(tmp)))
                tmp.unlink(missing_ok=True)
                tile = bp.title(base, ttl, size)
            tile.save(bp.OUT / f"{slug}.jpg", "JPEG", quality=88)
            ok += 1
            if ok % 40 == 0:
                print(f"  ... {ok} done")
        except Exception as e:
            print(f"  [err] {slug}: {e}")
            miss += 1
        time.sleep(0.12)
    print(f"\nDone. {ok} ready, {miss} missed.")


if __name__ == "__main__":
    main()
