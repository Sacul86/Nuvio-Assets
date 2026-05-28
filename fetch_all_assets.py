"""
fetch_all_assets.py v3 — labeled landscape tiles for Nuvio collections.

Sources:
  1. 41 themed tiles      — Pexels backdrop + big folder-title text overlay
  2. 11 branded franchises — copied as-is from rrevanth/nuvio-assets (already labeled)
  3.  8 franchise fallbacks — TMDB collection backdrop + franchise-name overlay

Required env vars (set via workflow inputs):
  PEXELS_API_KEY  — for themed image backgrounds
  TMDB_API_KEY    — for franchise fallback backdrops

Optional:
  OVERWRITE=1     — regenerate existing files (default: skip)
"""

import os, sys, time
from io import BytesIO
from pathlib import Path

try:
    import requests
    from PIL import Image, ImageDraw, ImageFont, ImageOps
except ImportError:
    sys.exit("Run: pip install requests Pillow")

PEXELS_KEY = os.environ.get("PEXELS_API_KEY", "").strip()
TMDB_KEY   = os.environ.get("TMDB_API_KEY", "").strip()
OVERWRITE  = os.environ.get("OVERWRITE", "0") == "1"

OUT_DIR = Path("assets")
OUT_DIR.mkdir(exist_ok=True)

# 16:9 landscape tile
TILE_W, TILE_H = 1920, 1080

# Pre-installed bold font on Ubuntu GitHub runners
FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
if not Path(FONT_PATH).exists():
    FONT_PATH = None

# ─── Themed tiles: (slug, Pexels query, display label) ─────────────
THEMES = [
    # Horror
    ("horror-new-movies",      "haunted forest fog moonlight cinematic", "New Horror Movies"),
    ("horror-new-series",      "dark hospital abandoned empty hallway",  "New Horror Series"),
    ("horror-supernatural",    "haunted house ghost paranormal",         "Supernatural & Paranormal"),
    ("horror-slasher",         "bloody knife silhouette dark alley",     "Slasher & Serial Killer"),
    ("horror-creature",        "monster cave fog creature shadow",       "Creature Feature"),
    # Thriller
    ("thriller-new-movies",    "neon rain street night cinematic",       "New Thriller Movies"),
    ("thriller-new-series",    "shadowy figure rain noir",               "New Thriller Series"),
    ("thriller-psychological", "broken mirror reflection face dark",     "Psychological"),
    ("thriller-crime",         "crime scene tape detective dark",        "Crime Thriller"),
    ("thriller-action",        "explosion action movie fire",            "Action Thriller"),
    # Zombie
    ("zombie-new-movies",      "zombie apocalypse abandoned street",     "New Zombie Movies"),
    ("zombie-new-series",      "post apocalyptic ruins decay",           "New Zombie Series"),
    ("zombie-comedy",          "zombie hand graveyard halloween",        "Zombie Comedy"),
    ("zombie-survival",        "survivor wasteland barricade",           "Survival Horror"),
    # Space
    ("space-new-movies",       "galaxy nebula stars cinematic",          "New Space Movies"),
    ("space-new-series",       "spaceship cockpit stars",                "New Space Series"),
    ("space-alien",            "ufo flying saucer sky",                  "Alien Invasion"),
    ("space-exploration",      "astronaut planet surface exploration",   "Space Exploration"),
    ("space-opera",            "starfield battleship sci-fi",            "Space Opera"),
    # Mystery
    ("mystery-new-movies",     "detective case file dark desk",          "New Mystery Movies"),
    ("mystery-new-series",     "noir detective shadow window",           "New Mystery Series"),
    ("mystery-detective",      "vintage detective office trench coat",   "Detective"),
    ("mystery-whodunit",       "old mansion library candlelight",        "Whodunit"),
    ("mystery-conspiracy",     "shadowy figures meeting conspiracy",     "Conspiracy"),
    # Science Fiction
    ("scifi-new-movies",       "futuristic city neon cyberpunk",         "New Sci-Fi Movies"),
    ("scifi-new-series",       "spaceship interior cinematic",           "New Sci-Fi Series"),
    ("scifi-dystopian",        "dystopian city ruins cyberpunk",         "Dystopian"),
    ("scifi-ai",               "robot artificial intelligence circuit",  "AI & Robots"),
    ("scifi-timetravel",       "wormhole portal swirl light",            "Time Travel"),
    # Apocalyptic
    ("apoc-new-movies",        "post apocalyptic wasteland sunset",      "New Apocalyptic Movies"),
    ("apoc-new-series",        "ruined city skyline apocalyptic",        "New Apocalyptic Series"),
    ("apoc-post",              "abandoned skyscrapers overgrown nature", "Post-Apocalyptic"),
    ("apoc-pandemic",          "biohazard virus laboratory",             "Pandemic & Virus"),
    ("apoc-nuclear",           "nuclear explosion mushroom cloud",       "Nuclear War"),
    ("apoc-dystopia",          "dystopian future cyberpunk neon",        "Dystopian Future"),
    # Natural Disaster
    ("disaster-new-movies",    "tornado lightning storm cinematic",      "New Disaster Movies"),
    ("disaster-new-series",    "dark stormy sky dramatic clouds",        "New Disaster Series"),
    ("disaster-earth",         "volcano eruption lava dramatic",         "Earthquakes & Volcanoes"),
    ("disaster-water",         "ocean wave stormy crashing",             "Tsunamis & Floods"),
    ("disaster-storm",         "hurricane storm clouds lightning",       "Storms & Hurricanes"),
    ("disaster-space",         "asteroid earth space catastrophe",       "Asteroid & Cosmic"),
]

# ─── Branded franchises (copied as-is from rrevanth, no label added) ──
RREV = "https://raw.githubusercontent.com/rrevanth/nuvio-assets/main/franchises"
BRANDED = {
    "fr-starwars":    (f"{RREV}/star-wars/star-wars-landscape.jpg",                 "jpg"),
    "fr-mcu":         (f"{RREV}/mcu/mcu-landscape.gif",                             "gif"),
    "fr-harrypotter": (f"{RREV}/wizarding-world/wizarding-world-landscape.png",     "png"),
    "fr-middleearth": (f"{RREV}/lord-of-the-rings/lord-of-the-rings-landscape.jpg", "jpg"),
    "fr-jurassic":    (f"{RREV}/jurassic-world/jurassic-world-landscape.jpg",       "jpg"),
    "fr-bond":        (f"{RREV}/007/007-landscape.jpg",                             "jpg"),
    "fr-mi":          (f"{RREV}/mission-impossible/mission-impossible-landscape.jpg","jpg"),
    "fr-johnwick":    (f"{RREV}/john-wick/john-wick-landscape.jpg",                 "jpg"),
    "fr-hungergames": (f"{RREV}/hunger-games/hunger-games-landscape.jpg",           "jpg"),
    "fr-pirates":     (f"{RREV}/pirates-caribbean/pirates-caribbean-landscape.jpg", "jpg"),
    "fr-indianajones":(f"{RREV}/indiana-jones/indiana-jones-landscape.jpg",         "jpg"),
}

# ─── Franchise fallbacks: (slug, TMDB collection ID, label) ────────
# Collection IDs match the tmdbId values already used in the v10 JSON.
TMDB_COLLECTIONS = [
    ("fr-fast",         "9485",   "Fast & Furious"),
    ("fr-matrix",       "2344",   "The Matrix"),
    ("fr-terminator",   "528",    "Terminator"),
    ("fr-alien",        "8091",   "Alien"),
    ("fr-predator",     "399",    "Predator"),
    ("fr-madmax",       "8945",   "Mad Max"),
    ("fr-planetapes",   "173710", "Planet of the Apes"),
    ("fr-monsterverse", "535313", "MonsterVerse"),
]

# Tracks Pexels photo IDs already used so no two themed tiles share a background.
used_photo_ids = set()


def already(slug, ext="jpg"):
    return (OUT_DIR / f"{slug}.{ext}").exists() and not OVERWRITE


def fit_font(draw, text, max_width, max_size=130):
    """Return the largest font where `text` fits in `max_width` pixels."""
    font = (ImageFont.truetype(FONT_PATH, max_size)
            if FONT_PATH else ImageFont.load_default())
    for size in range(max_size, 30, -5):
        font = (ImageFont.truetype(FONT_PATH, size)
                if FONT_PATH else ImageFont.load_default())
        bbox = draw.textbbox((0, 0), text, font=font)
        if bbox[2] - bbox[0] <= max_width:
            return font
    return font


def add_label(img_bytes, label):
    """Resize to 1920x1080, darken bottom, overlay big white label centered low."""
    img = Image.open(BytesIO(img_bytes)).convert("RGB")
    img = ImageOps.fit(img, (TILE_W, TILE_H), Image.LANCZOS)

    # Gradient overlay — transparent at top, ~85% black at bottom.
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    odraw = ImageDraw.Draw(overlay)
    for y in range(TILE_H):
        t = max(0.0, (y - TILE_H * 0.35) / (TILE_H * 0.65))
        a = int(220 * (t ** 1.4))
        odraw.line([(0, y), (TILE_W, y)], fill=(0, 0, 0, a))
    img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")

    # Draw label centered, low on the tile
    draw = ImageDraw.Draw(img)
    font = fit_font(draw, label, max_width=int(TILE_W * 0.85), max_size=130)
    bbox = draw.textbbox((0, 0), label, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    x = (TILE_W - tw) // 2
    y = TILE_H - th - 90
    # Shadow + main text for legibility on any background
    draw.text((x + 5, y + 5), label, font=font, fill=(0, 0, 0))
    draw.text((x, y), label, font=font, fill=(255, 255, 255))

    buf = BytesIO()
    img.save(buf, "JPEG", quality=88)
    return buf.getvalue()


def fetch_pexels_bytes(query):
    """Return (bytes, photographer) of an unused Pexels photo for `query`."""
    r = requests.get(
        "https://api.pexels.com/v1/search",
        headers={"Authorization": PEXELS_KEY},
        params={"query": query, "orientation": "landscape",
                "size": "large", "per_page": 15},
        timeout=20,
    )
    r.raise_for_status()
    photos = r.json().get("photos", [])

    chosen = None
    for p in photos:
        if p["id"] in used_photo_ids:
            continue
        if p.get("width", 0) < 1200:
            continue
        chosen = p
        break
    if chosen is None:
        for p in photos:
            if p["id"] not in used_photo_ids:
                chosen = p
                break
    if chosen is None and photos:
        chosen = photos[0]
    if chosen is None:
        return None, None

    used_photo_ids.add(chosen["id"])
    img_url = chosen["src"].get("large2x") or chosen["src"]["large"]
    img_bytes = requests.get(img_url, timeout=30).content
    return img_bytes, chosen.get("photographer", "?")


def make_themed(slug, query, label):
    if already(slug):
        print(f"  [skip] {slug}")
        return True
    try:
        img_bytes, photographer = fetch_pexels_bytes(query)
        if img_bytes is None:
            print(f"  [miss] {slug} -- no Pexels result for '{query}'")
            return False
        labeled = add_label(img_bytes, label)
        (OUT_DIR / f"{slug}.jpg").write_bytes(labeled)
        print(f"  [ok]   {slug:<22} '{label}' (bg: {photographer})")
        return True
    except Exception as e:
        print(f"  [err]  {slug}: {e}")
        return False


def copy_branded(slug, url, ext):
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


def make_franchise_fallback(slug, collection_id, label):
    if already(slug):
        print(f"  [skip] {slug}")
        return True
    try:
        r = requests.get(
            f"https://api.themoviedb.org/3/collection/{collection_id}",
            params={"api_key": TMDB_KEY}, timeout=20,
        )
        r.raise_for_status()
        data = r.json()
        backdrop_path = data.get("backdrop_path")
        if not backdrop_path:
            for movie in (data.get("parts") or []):
                if movie.get("backdrop_path"):
                    backdrop_path = movie["backdrop_path"]
                    break
        if not backdrop_path:
            print(f"  [miss] {slug} -- no backdrop in TMDB collection {collection_id}")
            return False
        img_url = f"https://image.tmdb.org/t/p/original{backdrop_path}"
        img_bytes = requests.get(img_url, timeout=30).content
        labeled = add_label(img_bytes, label)
        (OUT_DIR / f"{slug}.jpg").write_bytes(labeled)
        print(f"  [ok]   {slug:<22} '{label}' (TMDB collection {collection_id})")
        return True
    except Exception as e:
        print(f"  [err]  {slug}: {e}")
        return False


def main():
    print(f"Output: {OUT_DIR.absolute()}   OVERWRITE={OVERWRITE}")
    print(f"Font:   {FONT_PATH or 'PIL default (small)'}\n")

    print("== Branded franchise art (from rrevanth) ==")
    b_ok = sum(copy_branded(s, u, e) for s, (u, e) in BRANDED.items())

    print("\n== Franchise fallbacks (TMDB collection backdrops + label) ==")
    if not TMDB_KEY:
        print("  TMDB_API_KEY not set -- skipping franchise fallbacks.")
        t_ok = 0
    else:
        t_ok = 0
        for slug, cid, label in TMDB_COLLECTIONS:
            if make_franchise_fallback(slug, cid, label):
                t_ok += 1
            time.sleep(0.2)

    print("\n== Themed tiles (Pexels backdrop + folder title) ==")
    if not PEXELS_KEY:
        print("  PEXELS_API_KEY not set -- skipping themed tiles.")
        p_ok = 0
    else:
        p_ok = 0
        for slug, query, label in THEMES:
            if make_themed(slug, query, label):
                p_ok += 1
            time.sleep(0.25)

    print(f"\nDone. Branded {b_ok}/{len(BRANDED)}, "
          f"TMDB {t_ok}/{len(TMDB_COLLECTIONS)}, "
          f"Pexels {p_ok}/{len(THEMES)}.")


if __name__ == "__main__":
    main()
