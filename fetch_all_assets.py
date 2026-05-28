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

v2 changes:
  - dedup by Pexels photo ID across all themes (no two slugs share the same image)
  - iterate through up to 15 results per query if the top result is already used
  - use 'large2x' size variant (1880px wide) instead of 'large' (940px)
  - rejects results narrower than 1200px (avoids tiny thumbnail-only entries)
  - tweaked the queries that were causing duplicates / low-quality hits
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
# Queries tweaked to be distinct from neighbours and avoid stock-photo overlap.
PEXELS = {
    # ── Horror ───────────────────────────────────
    "horror-new-movies":      "haunted forest fog moonlight cinematic",
    "horror-new-series":      "dark hospital abandoned empty hallway",
    "horror-supernatural":    "haunted house ghost paranormal",
    "horror-slasher":         "bloody knife silhouette dark alley",
    "horror-creature":        "monster cave fog creature shadow",
    # ── Thriller ──────────────────────────────────
    "thriller-new-movies":    "neon rain street night cinematic",
    "thriller-new-series":    "shadowy figure rain noir",
    "thriller-psychological": "broken mirror reflection face dark",
    "thriller-crime":         "crime scene tape detective dark",
    "thriller-action":        "explosion action movie fire",
    # ── Zombie ───────────────────────────────────
    "zombie-new-movies":      "zombie apocalypse abandoned street",
    "zombie-new-series":      "post apocalyptic ruins decay",
    "zombie-comedy":          "zombie hand graveyard halloween",
    "zombie-survival":        "survivor wasteland barricade",
    # ── Space ────────────────────────────────────
    "space-new-movies":       "galaxy nebula stars cinematic",
    "space-new-series":       "spaceship cockpit stars",
    "space-alien":            "ufo flying saucer sky",
    "space-exploration":      "astronaut planet surface exploration",
    "space-opera":            "starfield battleship sci-fi",
    # ── Mystery ───────────────────────────────────
    "mystery-new-movies":     "detective case file dark desk",
    "mystery-new-series":     "noir detective shadow window",
    "mystery-detective":      "vintage detective office trench coat",
    "mystery-whodunit":       "old mansion library candlelight",
    "mystery-conspiracy":     "shadowy figures meeting conspiracy",
    # ── Science Fiction ───────────────────────────────
    "scifi-new-movies":       "futuristic city neon cyberpunk",
    "scifi-new-series":       "spaceship interior cinematic",
    "scifi-dystopian":        "dystopian city ruins cyberpunk",
    "scifi-ai":               "robot artificial intelligence circuit",
    "scifi-timetravel":       "wormhole portal swirl light",
    # ── Apocalyptic ─────────────────────────────────
    "apoc-new-movies":        "post apocalyptic wasteland sunset",
    "apoc-new-series":        "ruined city skyline apocalyptic",
    "apoc-post":              "abandoned skyscrapers overgrown nature",
    "apoc-pandemic":          "biohazard virus laboratory",
    "apoc-nuclear":           "nuclear explosion mushroom cloud",
    "apoc-dystopia":          "dystopian future cyberpunk neon",
    # ── Natural Disaster ──────────────────────────────
    "disaster-new-movies":    "tornado lightning storm cinematic",
    "disaster-new-series":    "dark stormy sky dramatic clouds",
    "disaster-earth":         "volcano eruption lava dramatic",
    "disaster-water":         "ocean wave stormy crashing",
    "disaster-storm":         "hurricane storm clouds lightning",
    "disaster-space":         "asteroid earth space catastrophe",
    # ── Franchise fallbacks (no branded art available) ───────
    "fr-fast":                "street racing cars neon night",
    "fr-matrix":              "green code digital rain cyberpunk",
    "fr-terminator":          "robot machine red glow dark metal",
    "fr-alien":               "dark sci-fi spaceship interior lights",
    "fr-predator":            "jungle thermal vision hunter",
    "fr-madmax":              "desert wasteland car chase dust",
    "fr-planetapes":          "ape forest dystopian",
    "fr-monsterverse":        "giant monster city destruction",
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
MIN_WIDTH  = 1200          # skip Pexels results narrower than this
PER_PAGE   = 15            # how many results to consider per query

# Tracks Pexels photo IDs already assigned to a slug this run, so no two
# slugs ever share the same photo.
used_photo_ids = set()

def already(slug, ext="jpg"):
    return (OUT_DIR / f"{slug}.{ext}").exists() and not OVERWRITE

def fetch_pexels(slug, query):
    if already(slug):
        print(f"  [skip] {slug}")
        return True
    params = {
        "query": query,
        "orientation": "landscape",
        "size": "large",
        "per_page": PER_PAGE,
    }
    try:
        r = requests.get(PEXELS_URL, headers={"Authorization": API_KEY},
                         params=params, timeout=20)
        r.raise_for_status()
        photos = r.json().get("photos", [])
        if not photos:
            print(f"  [miss] {slug} -- no results for '{query}'")
            return False

        # Find first usable photo: not a duplicate, and wide enough.
        chosen = None
        for p in photos:
            if p["id"] in used_photo_ids:
                continue
            if p.get("width", 0) < MIN_WIDTH:
                continue
            chosen = p
            break

        # Fallback 1: ignore width if nothing wide enough is unique
        if chosen is None:
            for p in photos:
                if p["id"] not in used_photo_ids:
                    chosen = p
                    break

        # Fallback 2: accept a duplicate rather than nothing
        if chosen is None:
            chosen = photos[0]
            print(f"  [warn] {slug} -- all results are duplicates, accepting one")

        used_photo_ids.add(chosen["id"])
        # large2x is ~1880px wide, much better than 'large' (~940px)
        img_url = chosen["src"].get("large2x") or chosen["src"]["large"]
        img_data = requests.get(img_url, timeout=30).content
        (OUT_DIR / f"{slug}.jpg").write_bytes(img_data)
        print(f"  [ok]   {slug:<22} {chosen['photographer']} "
              f"({chosen.get('width','?')}x{chosen.get('height','?')})")
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
