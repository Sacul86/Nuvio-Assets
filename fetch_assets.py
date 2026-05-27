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

# Track used backdrops so every theme gets a unique image
used_backdrops = set()

# ── Theme definitions ─────────────────────────────────────────────
# Each entry: (slug, method, media_type, params)
#   method:     "discover" or "search"
#   media_type: "movie" or "tv"
#   params:     dict passed to the TMDB endpoint
#
# TMDB movie genre IDs: Horror=27, Thriller=53, Sci-Fi=878,
#   Mystery=9648, Action=28, Crime=80
# TMDB TV genre IDs differ — using search for TV themes instead.

THEMES = [
    # ── Horror ────────────────────────────────────────────────────
    ("horror-new-movies",      "discover", "movie",
     {"with_genres": "27", "sort_by": "popularity.desc",
      "vote_count.gte": "200"}),
    ("horror-new-series",      "search", "tv",
     {"query": "horror dark"}),
    ("horror-supernatural",    "search", "movie",
     {"query": "conjuring supernatural haunting"}),
    ("horror-slasher",         "search", "movie",
     {"query": "scream slasher halloween"}),
    ("horror-creature",        "search", "movie",
     {"query": "creature monster horror"}),

    # ── Thriller ──────────────────────────────────────────────────
    ("thriller-new-movies",    "discover", "movie",
     {"with_genres": "53", "sort_by": "popularity.desc",
      "vote_count.gte": "200"}),
    ("thriller-new-series",    "search", "tv",
     {"query": "thriller suspense dark"}),
    ("thriller-psychological", "search", "movie",
     {"query": "psychological thriller mind"}),
    ("thriller-crime",         "discover", "movie",
     {"with_genres": "53,80", "sort_by": "popularity.desc",
      "vote_count.gte": "100"}),
    ("thriller-action",        "discover", "movie",
     {"with_genres": "53,28", "sort_by": "popularity.desc",
      "vote_count.gte": "100"}),

    # ── Zombie ────────────────────────────────────────────────────
    ("zombie-new-movies",      "search", "movie",
     {"query": "zombie undead apocalypse"}),
    ("zombie-new-series",      "search", "tv",
     {"query": "zombie walking dead undead"}),
    ("zombie-comedy",          "search", "movie",
     {"query": "zombie comedy shaun zombieland"}),
    ("zombie-survival",        "search", "movie",
     {"query": "zombie survival last"}),

    # ── Space ─────────────────────────────────────────────────────
    ("space-new-movies",       "discover", "movie",
     {"with_genres": "878", "sort_by": "popularity.desc",
      "vote_count.gte": "300"}),
    ("space-new-series",       "search", "tv",
     {"query": "space sci-fi stars galaxy"}),
    ("space-alien",            "search", "movie",
     {"query": "alien extraterrestrial UFO"}),
    ("space-exploration",      "search", "movie",
     {"query": "astronaut space exploration interstellar"}),
    ("space-opera",            "search", "movie",
     {"query": "star wars guardians galaxy epic space"}),

    # ── Mystery ───────────────────────────────────────────────────
    ("mystery-new-movies",     "discover", "movie",
     {"with_genres": "9648", "sort_by": "popularity.desc",
      "vote_count.gte": "100"}),
    ("mystery-new-series",     "search", "tv",
     {"query": "mystery detective crime investigation"}),
    ("mystery-detective",      "search", "movie",
     {"query": "detective sherlock investigation clue"}),
    ("mystery-whodunit",       "search", "movie",
     {"query": "whodunit murder mystery knives out"}),
    ("mystery-conspiracy",     "search", "movie",
     {"query": "conspiracy cover-up secret government"}),

    # ── Science Fiction ───────────────────────────────────────────
    ("scifi-new-movies",       "discover", "movie",
     {"with_genres": "878", "sort_by": "release_date.desc",
      "vote_count.gte": "50"}),
    ("scifi-new-series",       "search", "tv",
     {"query": "science fiction futuristic technology"}),
    ("scifi-dystopian",        "search", "movie",
     {"query": "dystopian future blade runner cyberpunk"}),
    ("scifi-ai",               "search", "movie",
     {"query": "artificial intelligence robot android"}),
    ("scifi-timetravel",       "search", "movie",
     {"query": "time travel back future temporal"}),

    # ── Apocalyptic ───────────────────────────────────────────────
    ("apoc-new-movies",        "search", "movie",
     {"query": "apocalypse end world doomsday"}),
    ("apoc-new-series",        "search", "tv",
     {"query": "apocalypse post-apocalyptic survival"}),
    ("apoc-post",              "search", "movie",
     {"query": "post-apocalyptic wasteland mad max"}),
    ("apoc-pandemic",          "search", "movie",
     {"query": "pandemic virus outbreak contagion"}),
    ("apoc-nuclear",           "search", "movie",
     {"query": "nuclear fallout radiation wasteland"}),
    ("apoc-dystopia",          "search", "movie",
     {"query": "dystopia hunger games totalitarian"}),

    # ── Natural Disaster ──────────────────────────────────────────
    ("disaster-new-movies",    "search", "movie",
     {"query": "disaster catastrophe destruction"}),
    ("disaster-new-series",    "search", "tv",
     {"query": "disaster storm nature catastrophe"}),
    ("disaster-earth",         "search", "movie",
     {"query": "earthquake volcano eruption pompeii"}),
    ("disaster-water",         "search", "movie",
     {"query": "tsunami flood tidal wave poseidon"}),
    ("disaster-storm",         "search", "movie",
     {"query": "tornado hurricane twister storm"}),
    ("disaster-space",         "search", "movie",
     {"query": "asteroid meteor comet armageddon impact"}),
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
                print(f"  [ok]   {slug:<30}  ← {title}")
                return True

        print(f"  [miss] {slug} — no unique backdrop found")
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
