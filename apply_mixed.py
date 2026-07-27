"""
apply_mixed.py — franchise collections use portrait posters (POSTER shape),
every other folder uses its landscape cover (LANDSCAPE shape).

Usage:
    python apply_mixed.py <profile_in.json> <profile_out.json> <base_url>
<base_url> is the repo raw prefix up to /assets (e.g.
    https://raw.githubusercontent.com/Sacul86/Nuvio-Assets/<sha>/assets )
"""
import json
import re
import sys
from pathlib import Path

pin, pout, base = sys.argv[1], sys.argv[2], sys.argv[3].rstrip("/")
FRANCHISE = {"Film Collections", "TV Collections", "Anime Franchises"}
posters = {p.stem for p in Path("assets/poster").glob("*.jpg")}
land = {p.stem for p in Path("assets/landscape").glob("*.jpg")}
data = json.load(open(pin))

n_poster = n_land = 0
for coll in data:
    franchise = coll["title"] in FRANCHISE
    for fo in coll["folders"]:
        m = re.search(r"/(?:covers|portrait|landscape|poster)/(?:[^/]+/)?([^/]+)\.(?:webp|jpg)",
                      fo.get("coverImageUrl", "") or "")
        slug = m.group(1) if m else None
        if not slug:
            continue
        if franchise and slug in posters:
            fo["tileShape"] = "POSTER"
            fo["coverImageUrl"] = f"{base}/poster/{slug}.jpg"
            n_poster += 1
        elif slug in land:
            fo["tileShape"] = "LANDSCAPE"
            fo["coverImageUrl"] = f"{base}/landscape/{slug}.jpg"
            n_land += 1

json.dump(data, open(pout, "w"), ensure_ascii=False, indent=2)
print(f"{n_poster} poster tiles, {n_land} landscape tiles → {pout}")
