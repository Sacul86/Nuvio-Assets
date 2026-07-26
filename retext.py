"""
retext.py — re-apply gold-caps labels from the pre-text cache in
assets/.srccache, without re-fetching from TMDB. Fast; use after tweaking
the label renderer in build_portrait.title().

Usage:
    python retext.py <profile.json>
"""
import sys
import json
from pathlib import Path
from PIL import Image

import build_portrait as bp

CACHE = Path("assets/.srccache")


def main():
    data = json.load(open(sys.argv[1]))
    jobs = [(c["title"], f["title"], bp.slug_of(f))
            for c in data for f in c["folders"] if bp.slug_of(f)]
    size = bp.fit_size([t for _, t, _ in jobs])
    n = 0
    for coll, ttl, slug in jobs:
        src = CACHE / f"{slug}.jpg"
        if not src.exists():
            continue
        im = Image.open(src).convert("RGB")
        if coll != "Streaming":          # streaming tiles carry their own branding
            im = bp.title(im, ttl, size)
        im.save(bp.OUT / f"{slug}.jpg", "JPEG", quality=88)
        n += 1
    print(f"Re-texted {n} tiles @ font {size}")


if __name__ == "__main__":
    main()
