"""
apply_covers.py — repoint the 72 concept-folder covers in a Nuvio profile
at the newly built assets/covers/<slug>.jpg images.

Usage:
    python apply_covers.py <profile.json> <out.json> <base_url>

<base_url> is the raw prefix the images are served from, e.g.
    https://raw.githubusercontent.com/sacul86/nuvio-assets/<sha>/assets/covers
Only folders whose current cover slug has a matching built image are changed.
"""
import json
import re
import sys
from pathlib import Path

profile_in, profile_out, base = sys.argv[1], sys.argv[2], sys.argv[3].rstrip("/")
built = {p.stem for p in Path("assets/covers").glob("*.jpg")}
data = json.load(open(profile_in))

changed = 0
for coll in data:
    if coll["title"] not in ("Genres", "Themes", "Decades"):
        continue
    for fo in coll["folders"]:
        m = re.search(r"/covers/default/([^/]+)\.webp", fo.get("coverImageUrl", "") or "")
        slug = m.group(1) if m else None
        if slug and slug in built:
            fo["coverImageUrl"] = f"{base}/{slug}.jpg"
            changed += 1

json.dump(data, open(profile_out, "w"), ensure_ascii=False, indent=2)
print(f"Repointed {changed} covers → {profile_out}")
