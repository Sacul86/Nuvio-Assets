"""
apply_all_portrait.py — every folder becomes a POSTER tile. Franchise
collections point at assets/poster/<slug>.jpg; everything else at
assets/portrait/<slug>.jpg.

Usage:
    python apply_all_portrait.py <profile_in.json> <profile_out.json> <base_url>
<base_url> = repo raw prefix up to /assets.
"""
import json
import re
import sys
from pathlib import Path

pin, pout, base = sys.argv[1], sys.argv[2], sys.argv[3].rstrip("/")
FRANCHISE = {"Film Collections", "TV Collections", "Anime Franchises"}
posters = {p.stem for p in Path("assets/poster").glob("*.jpg")}
portraits = {p.stem for p in Path("assets/portrait").glob("*.jpg")}
data = json.load(open(pin))

n = 0
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
            n += 1
        elif slug in portraits:
            fo["tileShape"] = "POSTER"
            fo["coverImageUrl"] = f"{base}/portrait/{slug}.jpg"
            n += 1

json.dump(data, open(pout, "w"), ensure_ascii=False, indent=2)
print(f"Repointed {n} folders to portrait tiles → {pout}")
