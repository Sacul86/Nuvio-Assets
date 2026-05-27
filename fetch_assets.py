"""
fetch_assets.py — downloads themed cinematic backdrop images from TMDB
for Nuvio media app collection headers.

Usage:
    export TMDB_API_KEY=your_key_here
    pip install requests
    python fetch_assets.py

To replace existing images, delete the assets/ folder first and re-run.

Outputs:
    ./assets/<theme-slug>.jpg — 41 landscape backdrops (1280px wide).

TMDB attribution required: https://www.themoviedb.org/about/logos-attribution
"""

import os
import sys
import time
from pathlib import Path

try:
    import requests
except ImportError:
    sys.exit("Run: pip install requests")

API_KEY = os.environ.get("TMDB_API_KEY") or "PASTE_YOUR_KEY_HERE"
if API_KEY == "PASTE_YOUR_KEY_HERE":
    sys.exit("Set TMDB_API_KEY env var.")

BASE_URL = "https://api.themoviedb.org/3"
IMG_BASE = "https://image.tmdb.org/t/p/w1280"
OUT_DIR = Path("assets")
OUT_DIR.mkdir(exist_ok=True)

used_backdrops = set()

# ── TMDB Genre IDs ────────────────────────────────────────────────
# Movie: Horror=27 Thriller=53 SciFi=878 Mystery=9648 Action=28
#         Crime=80 Adventure=12 Fantasy=14 Drama=18
# TV:    Action&Adventure=10759 Crime=80 Mystery=9648
#        SciFi&Fantasy=10765 Drama=18

# ── Theme definitions ─────────────────────────────────────────────
# (slug, method, media_type, params)
#
# Strategy: use discover (reliable, always has backdrops) wherever
# a genre ID maps cleanly. Use simple 1-2 word search queries only
# for niche sub-themes. Different sort orders / genre combos / pages
# ensure variety. Deduplication guarantees unique images.

THEMES = [
    # ── Horror (genre 27) ────────────────────────────────────────
    ("horror-new-movies",
     "discover", "movie",
     {"with_genres": "27", "sort_by": "popularity.desc"}),
    ("horror-new-series",
     "search", "tv",
     {"query": "horror"}),
    ("horror-supernatural",
     "discover", "movie",
     {"with_genres": "27", "sort_by": "vote_average.desc",
      "vote_count.gte": "500"}),
    ("horror-slasher",
     "discover", "movie",
     {"with_genres": "27,53", "sort_by": "popularity.desc"}),
    ("horror-creature",
     "discover", "movie",
     {"with_genres": "27,878", "sort_by": "popularity.desc"}),

    # ── Thriller (genre 53) ──────────────────────────────────────
    ("thriller-new-movies",
     "discover", "movie",
     {"with_genres": "53", "sort_by": "popularity.desc"}),
    ("thriller-new-series",
     "search", "tv",
     {"query": "thriller"}),
    ("thriller-psychological",
     "discover", "movie",
     {"with_genres": "53", "sort_by": "vote_average.desc",
      "vote_count.gte": "500"}),
    ("thriller-crime",
     "discover", "movie",
     {"with_genres": "53,80", "sort_by": "popularity.desc"}),
    ("thriller-action",
     "discover", "movie",
     {"with_genres": "53,28", "sort_by": "popularity.desc"}),

    # ── Zombie ───────────────────────────────────────────────────
    ("zombie-new-movies",
     "search", "movie",
     {"query": "zombie"}),
    ("zombie-new-series",
     "search", "tv",
     {"query": "zombie"}),
    ("zombie-comedy",
     "search", "movie",
     {"query": "zombieland"}),
    ("zombie-survival",
     "search", "movie",
     {"query": "dead survival"}),

    # ── Space (genre 878 = Sci-Fi) ───────────────────────────────
    ("space-new-movies",
     "discover", "movie",
     {"with_genres": "878", "sort_by": "popularity.desc"}),
    ("space-new-series",
     "search", "tv",
     {"query": "space"}),
    ("space-alien",
     "search", "movie",
     {"query": "alien"}),
    ("space-exploration",
     "search", "movie",
     {"query": "astronaut"}),
    ("space-opera",
     "discover", "movie",
     {"with_genres": "878,12", "sort_by": "popularity.desc"}),

    # ── Mystery (genre 9648) ─────────────────────────────────────
    ("mystery-new-movies",
     "discover", "movie",
     {"with_genres": "9648", "sort_by": "popularity.desc"}),
    ("mystery-new-series",
     "discover", "tv",
     {"with_genres": "9648", "sort_by": "popularity.desc"}),
    ("mystery-detective",
     "search", "movie",
     {"query": "detective"}),
    ("mystery-whodunit",
     "discover", "movie",
     {"with_genres": "9648,80", "sort_by": "popularity.desc"}),
    ("mystery-conspiracy",
     "search", "movie",
     {"query": "conspiracy"}),

    # ── Science Fiction (genre 878) ──────────────────────────────
    ("scifi-new-movies",
     "discover", "movie",
     {"with_genres": "878", "sort_by": "popularity.desc", "page": "2"}),
    ("scifi-new-series",
     "discover", "tv",
     {"with_genres": "10765", "sort_by": "popularity.desc"}),
    ("scifi-dystopian",
     "search", "movie",
     {"query": "dystopia"}),
    ("scifi-ai",
     "search", "movie",
     {"query": "robot"}),
    ("scifi-timetravel",
     "search", "movie",
     {"query": "time travel"}),

    # ── Apocalyptic ──────────────────────────────────────────────
    ("apoc-new-movies",
     "search", "movie",
     {"query": "apocalypse"}),
    ("apoc-new-series",
     "search", "tv",
     {"query": "apocalypse"}),
    ("apoc-post",
     "search", "movie",
     {"query": "wasteland"}),
    ("apoc-pandemic",
     "search", "movie",
     {"query": "pandemic"}),
    ("apoc-nuclear",
     "search", "movie",
     {"query": "nuclear"}),
    ("apoc-dystopia",
     "discover", "movie",
     {"with_genres": "878,18", "sort_by": "popularity.desc"}),

    # ── Natural Disaster ─────────────────────────────────────────
    ("disaster-new-movies",
     "search", "movie",
     {"query": "disaster"}),
    ("disaster-new-series",
     "search", "tv",
     {"query": "disaster"}),
    ("disaster-earth",
     "search", "movie",
     {"query": "earthquake"}),
    ("disaster-water",
     "search", "movie",
     {"query": "tsunami"}),
    ("disaster-storm",
     "search", "movie",
     {"query": "tornado"}),
    ("disaster-space",
     "search", "movie",
     {"query": "asteroid"}),
]


def fetch_one(slug, method, media_type, params):
    out_path = OUT_DIR / f"{slug}.jpg"
    if out_path.exists():
        print(f"  [skip] {slug} (exists)")
        return True

    if method == "discover":
        url = f"{BASE_URL}/discover/{media_type}"
    else:
        url = f"{BASE_URL}/search/{media_type}"

    api_params = {"api_key": API_KEY, **params}

    try:
        for page in range(1, 4):
            api_params["page"] = api_params.get("page", str(page))
            r = requests.get(url, params=api_params, timeout=20)
            r.raise_for_status()
            results = r.json().get("results", [])

            for item in results:
                backdrop = item.get("backdrop_path")
                if backdrop and backdrop not in used_backdrops:
                    used_backdrops.add(backdrop)
                    img_url = IMG_BASE + backdrop
                    img_resp = requests.get(img_url, timeout=30)
                    img_resp.raise_for_status()
                    out_path.write_bytes(img_resp.content)
                    title = item.get("title") or item.get("name", "?")
                    print(f"  [ok]   {slug:<30}  <- {title}")
                    return True

            api_params["page"] = str(page + 1)

        print(f"  [miss] {slug} -- no backdrop found after 3 pages")
        return False
    except Exception as e:
        print(f"  [err]  {slug}: {e}")
        return False


def main():
    print(f"Fetching {len(THEMES)} themed backdrops from TMDB...")
    print(f"Output:  {OUT_DIR.absolute()}")
    print(f"Images:  1280px wide cinematic backdrops\n")
    ok = 0
    for slug, method, media_type, params in THEMES:
        if fetch_one(slug, method, media_type, params):
            ok += 1
        time.sleep(0.25)
    print(f"\nDone. {ok}/{len(THEMES)} images saved to {OUT_DIR}/")
    if ok < len(THEMES):
        print("Re-run to retry misses (existing files are skipped).")


if __name__ == "__main__":
    main()
