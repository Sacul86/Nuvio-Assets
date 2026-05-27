"""
fetch_assets.py — downloads themed landscape images from Pexels for Carl's Nuvio collections.

Usage:
    1. Sign up free at https://www.pexels.com/api/ to get an API key (instant)
    2. Set the key:  export PEXELS_API_KEY=your_key_here  (or just paste it below)
    3. pip install requests
    4. python fetch_assets.py

Outputs:
    ./assets/<theme-slug>.jpg  — 41 landscape images, one per folder.

Pexels licence: free for personal and commercial use, no attribution required.
"""

import os
import sys
import time
from pathlib import Path

try:
    import requests
except ImportError:
    sys.exit("Run: pip install requests")

API_KEY = os.environ.get("PEXELS_API_KEY") or "PASTE_YOUR_KEY_HERE"
if API_KEY == "PASTE_YOUR_KEY_HERE":
    sys.exit("Set PEXELS_API_KEY env var or paste it in the script.")

# theme slug  -> Pexels search query (tuned per theme for best cinematic match)
THEMES = {
    # Horror
    "horror-new-movies":       "dark forest fog moonlight horror",
    "horror-new-series":       "abandoned hospital corridor dark horror",
    "horror-supernatural":     "haunted house ghost paranormal dark",
    "horror-slasher":          "bloody knife silhouette dark alley",
    "horror-creature":         "monster silhouette dark cave fog",
    # Thriller
    "thriller-new-movies":     "neon city night thriller cinematic",
    "thriller-new-series":     "shadowy figure rain noir thriller",
    "thriller-psychological":  "dark mirror reflection psychological",
    "thriller-crime":          "crime scene noir detective dark city",
    "thriller-action":         "explosion action movie cinematic",
    # Zombie
    "zombie-new-movies":       "zombie apocalypse abandoned street dark",
    "zombie-new-series":       "post apocalyptic ruins decay dark",
    "zombie-comedy":           "zombie hand graveyard halloween",
    "zombie-survival":         "survivor wasteland barricade dark",
    # Space
    "space-new-movies":        "galaxy nebula stars space cinematic",
    "space-new-series":        "spaceship cockpit stars cinematic",
    "space-alien":             "ufo alien spacecraft sky dark",
    "space-exploration":       "astronaut planet surface exploration",
    "space-opera":             "starfield battleship sci-fi cinematic",
    # Mystery
    "mystery-new-movies":      "magnifying glass map detective mystery",
    "mystery-new-series":      "noir detective shadow window",
    "mystery-detective":       "vintage detective office trench coat",
    "mystery-whodunit":        "manor house library mystery candlelight",
    "mystery-conspiracy":      "shadowy figures meeting conspiracy",
    # Science Fiction
    "scifi-new-movies":        "futuristic city neon cyberpunk",
    "scifi-new-series":        "spaceship interior cinematic sci-fi",
    "scifi-dystopian":         "dystopian city ruins cyberpunk dark",
    "scifi-ai":                "robot artificial intelligence circuit board",
    "scifi-timetravel":        "wormhole time portal swirl light",
    # Apocalyptic
    "apoc-new-movies":         "post apocalyptic wasteland sunset",
    "apoc-new-series":         "ruined city skyline apocalyptic",
    "apoc-post":               "abandoned skyscrapers overgrown nature ruin",
    "apoc-pandemic":           "biohazard virus laboratory dark",
    "apoc-nuclear":            "nuclear explosion mushroom cloud",
    "apoc-dystopia":           "dystopian future cyberpunk neon dark",
    # Natural Disaster
    "disaster-new-movies":     "tornado lightning storm cinematic",
    "disaster-new-series":     "tsunami wave storm dramatic",
    "disaster-earth":          "volcano eruption lava dramatic",
    "disaster-water":          "tsunami wave flood dramatic",
    "disaster-storm":          "hurricane storm clouds lightning",
    "disaster-space":          "asteroid earth space catastrophe",
}

OUT_DIR = Path("assets")
OUT_DIR.mkdir(exist_ok=True)

HEADERS = {"Authorization": API_KEY}
URL = "https://api.pexels.com/v1/search"

def fetch_one(slug: str, query: str) -> bool:
    """Search Pexels, download the best landscape result, save as assets/<slug>.jpg."""
    out_path = OUT_DIR / f"{slug}.jpg"
    if out_path.exists():
        print(f"  [skip] {slug} (exists)")
        return True

    params = {
        "query": query,
        "orientation": "landscape",
        "size": "large",     # 24MP+ — plenty for a tile
        "per_page": 5,        # grab top 5, pick first
    }
    try:
        r = requests.get(URL, headers=HEADERS, params=params, timeout=20)
        r.raise_for_status()
        photos = r.json().get("photos", [])
        if not photos:
            print(f"  [miss] {slug} — no results for '{query}'")
            return False
        # Use the 'large' size variant (~1880 wide) — good for landscape tiles
        img_url = photos[0]["src"]["large"]
        img_data = requests.get(img_url, timeout=30).content
        out_path.write_bytes(img_data)
        print(f"  [ok]   {slug:<30}  {photos[0]['photographer']}")
        return True
    except Exception as e:
        print(f"  [err]  {slug}: {e}")
        return False

def main():
    print(f"Fetching {len(THEMES)} themed landscape images from Pexels...")
    print(f"Output: {OUT_DIR.absolute()}")
    print()
    ok = 0
    for slug, query in THEMES.items():
        if fetch_one(slug, query):
            ok += 1
        time.sleep(0.3)  # gentle rate limit
    print()
    print(f"Done. {ok}/{len(THEMES)} images saved to {OUT_DIR}/")
    if ok < len(THEMES):
        print("For misses: edit the search query in this script and re-run; existing files are skipped.")

if __name__ == "__main__":
    main()
