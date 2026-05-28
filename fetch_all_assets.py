"""
fetch_all_assets.py — fetches ALL Nuvio collection artwork into ./assets/.

Three sources:
  1. 41 genre/theme images from Pexels  (search-based)
  2.  8 franchise fallback images from Pexels (no branded art available)
  3. 11 branded franchise images copied from the rrevanth/nuvio-assets repo

Designed to run in GitHub Actions (reads PEXELS_API_KEY from env / secret),
but also runs locally the same way.

By default SKIPS files that already exist (safe to re-run). Set OVERWRITE=1
to force re-fetch everything.
"""

import os, sys, time
from pathlib import Path

try:
    import requests
except ImportError:
    sys.exit("Run: pip install requests")

API_KEY   = os.environ.get("PEXELS_API_KEY", "").strip()
OVERWRITE = os.environ.get("OVERWRITE", "0") == "1"

OUT_DIR = Path("assets")
OUT_DIR.mkdir(exist_ok=True)

# ---------------------------------------------------------------- Pexels themes
PEXELS = {
    # genre/theme rows
    "horror-new-movies": "dark forest fog moonlight horror",
    "horror-new-series": "abandoned hospital corridor dark horror",
    "horror-supernatural": "haunted house ghost paranormal dark",
    "horror-slasher": "bloody knife silhouette dark alley",
    "horror-creature": "monster silhouette dark cave fog",
    "thriller-new-movies": "neon city night thriller cinematic",
    "thriller-new-series": "shadowy figure rain noir thriller",
    "thriller-psychological": "dark mirror reflection psychological",
    "thriller-crime": "crime scene noir detective dark city",
    "thriller-action": "explosion action movie cinematic",
    "zombie-new-movies": "zombie apocalypse abandoned street dark",
    "zombie-new-series": "post apocalyptic ruins decay dark",
    "zombie-comedy": "zombie hand graveyard halloween",
    "zombie-survival": "survivor wasteland barricade dark",
    "space-new-movies": "galaxy nebula stars space cinematic",
    "space-new-series": "spaceship cockpit stars cinematic",
    "space-alien": "ufo alien spacecraft sky dark",
    "space-exploration": "astronaut planet surface exploration",
    "space-opera": "starfield battleship sci-fi cinematic",
    "mystery-new-movies": "magnifying glass map detective mystery",
    "mystery-new-series": "noir detective shadow window",
    "mystery-detective": "vintage detective office trench coat",
    "mystery-whodunit": "manor house library mystery candlelight",
    "mystery-conspiracy": "shadowy figures meeting conspiracy",
    "scifi-new-movies": "futuristic city neon cyberpunk",
    "scifi-new-series": "spaceship interior cinematic sci-fi",
    "scifi-dystopian": "dystopian city ruins cyberpunk dark",
    "scifi-ai": "robot artificial intelligence circuit board",
    "scifi-timetravel": "wormhole time portal swirl light",
    "apoc-new-movies": "post apocalyptic wasteland sunset",
    "apoc-new-series": "ruined city skyline apocalyptic",
    "apoc-post": "abandoned skyscrapers overgrown nature ruin",
    "apoc-pandemic": "biohazard virus laboratory dark",
    "apoc-nuclear": "nuclear explosion mushroom cloud",
    "apoc-dystopia": "dystopian future cyberpunk neon dark",
    "disaster-new-movies": "tornado lightning storm cinematic",
    "disaster-new-series": "tsunami wave storm dramatic",
    "disaster-earth": "volcano eruption lava dramatic",
    "disaster-water": "tsunami wave flood dramatic",
    "disaster-storm": "hurricane storm clouds lightning",
    "disaster-space": "asteroid earth space catastrophe",
    # franchise fallbacks (no branded art available)
    "fr-fast": "street racing cars neon night",
    "fr-matrix": "green code digital rain cyberpunk",
    "fr-terminator": "robot endoskeleton red eyes dark",
    "fr-alien": "dark spaceship corridor horror",
    "fr-predator": "jungle thermal vision hunter",
    "fr-madmax": "desert wasteland car chase post apocalyptic",
    "fr-planetapes": "ape forest dystopian",
    "fr-monsterverse": "giant monster city destruction",
}

# --------------------------------------------- Branded art copied from rrevanth
RREV = "https://raw.githubusercontent.com/rrevanth/nuvio-assets/main/franchises"
BRANDED = {
    "fr-starwars":    f"{RREV}/star-wars/star-wars-landscape.jpg",
    "fr-mcu":         f"{RREV}/mcu/mcu-landscape.gif",
    "fr-harrypotter": f"{RREV}/wizarding-world/wizarding-world-landscape.png",
    "fr-middleearth": f"{RREV}/lord-of-the-rings/lord-of-the-rings-landscape.jpg",
    "fr-jurassic":    f"{RREV}/jurassic-world/jurassic-world-landscape.jpg",
    "fr-bond":        f"{RREV}/007/007-landscape.jpg",
    "fr-mi":          f"{RREV}/mission-impossible/mission-impossible-landscape.jpg",
    "fr-johnwick":    f"{RREV}/john-wick/john-wick-landscape.jpg",
    "fr-hungergames": f"{RREV}/hunger-games/hunger-games-landscape.jpg",
    "fr-pirates":     f"{RREV}/pirates-caribbean/pirates-caribbean-landscape.jpg",
    "fr-indianajones":f"{RREV}/indiana-jones/indiana-jones-landscape.jpg",
}
# branded files keep their source extension so the JSON can point at the right one
BRANDED_EXT = {"fr-mcu": "gif", "fr-harrypotter": "png"}

PEXELS_URL = "https://api.pexels.com/v1/search"

def already(slug, ext="jpg"):
    return (OUT_DIR / f"{slug}.{ext}").exists() and not OVERWRITE

def fetch_pexels(slug, query):
    if already(slug):
        print(f"  [skip] {slug}")
        return True
    params = {"query": query, "orientation": "landscape", "size": "large", "per_page": 5}
    try:
        r = requests.get(PEXELS_URL, headers={"Authorization": API_KEY}, params=params, timeout=20)
        r.raise_for_status()
        photos = r.json().get("photos", [])
        if not photos:
            print(f"  [miss] {slug} -- '{query}'")
            return False
        (OUT_DIR / f"{slug}.jpg").write_bytes(
            requests.get(photos[0]["src"]["large"], timeout=30).content)
        print(f"  [ok]   {slug:<22} {photos[0]['photographer']}")
        return True
    except Exception as e:
        print(f"  [err]  {slug}: {e}")
        return False

def copy_branded(slug, url):
    ext = BRANDED_EXT.get(slug, "jpg")
    if already(slug, ext):
        print(f"  [skip] {slug}")
        return True
    try:
        data = requests.get(url, timeout=30).content
        (OUT_DIR / f"{slug}.{ext}").write_bytes(data)
        print(f"  [ok]   {slug:<22} (branded {ext})")
        return True
    except Exception as e:
        print(f"  [err]  {slug}: {e}")
        return False

def main():
    print(f"Output: {OUT_DIR.absolute()}   OVERWRITE={OVERWRITE}\n")

    print("== Branded franchise art (from rrevanth) ==")
    b_ok = sum(copy_branded(s, u) for s, u in BRANDED.items())

    print("\n== Pexels images (genres + franchise fallbacks) ==")
    if not API_KEY:
        print("  PEXELS_API_KEY not set -- skipping Pexels fetches.")
        p_ok = 0
    else:
        p_ok = 0
        for s, q in PEXELS.items():
            if fetch_pexels(s, q):
                p_ok += 1
            time.sleep(0.25)

    print(f"\nDone. Branded {b_ok}/{len(BRANDED)}, Pexels {p_ok}/{len(PEXELS)}.")

if __name__ == "__main__":
    main()
