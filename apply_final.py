"""
apply_final.py — concept rows are portrait real posters (assets/poster,
POSTER); brands and franchises stay landscape (assets/landscape, LANDSCAPE).

Usage: python apply_final.py <profile_in.json> <profile_out.json> <base_url>
<base_url> = repo raw prefix up to /assets.
"""
import json
import re
import sys
from pathlib import Path

pin, pout, base = sys.argv[1], sys.argv[2], sys.argv[3].rstrip("/")
LANDSCAPE = {"Networks", "Studios", "Streaming",
             "Film Collections", "TV Collections", "Anime Franchises"}
posters = {p.stem for p in Path("assets/poster").glob("*.jpg")}
land = {p.stem for p in Path("assets/landscape").glob("*.jpg")}
data = json.load(open(pin))

n_p = n_l = 0
for coll in data:
    is_land = coll["title"] in LANDSCAPE
    for fo in coll["folders"]:
        m = re.search(r"/(?:covers|portrait|landscape|poster)/(?:[^/]+/)?([^/]+)\.(?:webp|jpg)",
                      fo.get("coverImageUrl", "") or "")
        slug = m.group(1) if m else None
        if not slug:
            continue
        if is_land and slug in land:
            fo["tileShape"] = "LANDSCAPE"
            fo["coverImageUrl"] = f"{base}/landscape/{slug}.jpg"
            n_l += 1
        elif not is_land and slug in posters:
            fo["tileShape"] = "POSTER"
            fo["coverImageUrl"] = f"{base}/poster/{slug}.jpg"
            n_p += 1

json.dump(data, open(pout, "w"), ensure_ascii=False, indent=2)
print(f"{n_p} portrait poster rows, {n_l} landscape rows → {pout}")
