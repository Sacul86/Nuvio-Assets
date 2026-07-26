"""
apply_landscape.py — make a Nuvio profile all-landscape and point every
folder at its assets/landscape/<slug>.jpg cover.

Usage:
    python apply_landscape.py <profile_in.json> <profile_out.json> <base_url>
"""
import json
import re
import sys
from pathlib import Path

pin, pout, base = sys.argv[1], sys.argv[2], sys.argv[3].rstrip("/")
built = {p.stem for p in Path("assets/landscape").glob("*.jpg")}
data = json.load(open(pin))

repointed = shaped = 0
for coll in data:
    for fo in coll["folders"]:
        if fo.get("tileShape") != "LANDSCAPE":
            fo["tileShape"] = "LANDSCAPE"
            shaped += 1
        m = re.search(r"/(?:covers|portrait|landscape)/(?:[^/]+/)?([^/]+)\.(?:webp|jpg)", fo.get("coverImageUrl", "") or "")
        slug = m.group(1) if m else None
        if slug and slug in built:
            fo["coverImageUrl"] = f"{base}/{slug}.jpg"
            repointed += 1

json.dump(data, open(pout, "w"), ensure_ascii=False, indent=2)
print(f"LANDSCAPE shape on {shaped} folders; repointed {repointed} covers → {pout}")
