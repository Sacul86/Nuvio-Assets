"""
fetch_all_assets.py v9 — themed AI tiles + franchises via fanart.tv → TMDB chain.

Sources:
  1. 41 themed tiles      — Pollinations (Flux) background + Bebas Neue title text
  2. 17 branded franchises — copied as-is from rrevanth (official logos already on art)
  3. 17 franchise fallbacks — fanart.tv background composited with hdmovielogo,
                              falling back to TMDB collection backdrop + Bebas Neue.

Priority chain for franchise fallbacks:
  a. fanart.tv moviebackground + hdmovielogo composite (best — looks like rrevanth)
  b. fanart.tv moviebackground + Bebas Neue title (no logo available)
  c. TMDB collection backdrop + Bebas Neue title (final fallback)

Required env vars (set via workflow inputs):
  TMDB_API_KEY   — for TMDB collection backdrops and movie enumeration
  FANART_API_KEY — for fanart.tv backgrounds and franchise logos

Optional:
  OVERWRITE=1   — regenerate existing files (default: skip)
  WORKERS=N     — parallel AI requests (default: 6)
  FONT_PATH=... — override the TTF location (default: /tmp/BebasNeue-Regular.ttf)
"""

import io
import os
import sys
import time
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

try:
    import requests
    from PIL import Image, ImageDraw, ImageFont, ImageOps
except ImportError:
    sys.exit("Run: pip install requests Pillow")

WORKERS = int(os.environ.get("WORKERS", "6"))
TMDB_KEY = os.environ.get("TMDB_API_KEY", "").strip()
FANART_KEY = os.environ.get("FANART_API_KEY", "").strip()
OVERWRITE = os.environ.get("OVERWRITE", "0") == "1"
OUT_DIR = Path("assets")
OUT_DIR.mkdir(exist_ok=True)

POLLINATIONS_BASE = "https://image.pollinations.ai/prompt/"
TILE_W, TILE_H = 1920, 1080

# Bebas Neue — downloaded by the workflow before this script runs.
FONT_PATH = os.environ.get("FONT_PATH", "/tmp/BebasNeue-Regular.ttf")
FALLBACK_FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

NEGATIVE = ("no anime, no manga, no cartoon, no illustration, no drawing, "
            "no digital painting, no 3d render, no chibi, no childish")
STYLE = ("photorealistic cinematic film still aesthetic, "
         "dramatic atmospheric lighting, professionally designed movie streaming banner, "
         "widescreen 16:9 landscape composition")

# ─── Themed tiles: (slug, scene description, title text) ───────────
THEMES = [
    # Horror
    ("horror-new-movies",      "haunted misty dark forest with eerie moonlight piercing through skeletal bare trees, fog rolling on ground", "New Horror Movies"),
    ("horror-new-series",      "abandoned dark hospital corridor with flickering fluorescent lights, peeling wallpaper, ominous shadows",     "New Horror Series"),
    ("horror-supernatural",    "victorian haunted manor at night, glowing ghostly figure visible in attic window, swirling fog",               "Supernatural"),
    ("horror-slasher",         "rain-soaked dark alley with neon reflection, ominous silhouette holding bloody blade, noir lighting",          "Slasher"),
    ("horror-creature",        "menacing monster silhouette emerging from dark cave entrance with glowing yellow eyes, dense fog",             "Creature Feature"),
    # Thriller
    ("thriller-new-movies",    "rain-drenched neon-lit city street at night with reflective wet asphalt, lone figure walking",                 "New Thriller Movies"),
    ("thriller-new-series",    "shadowy silhouetted figure under a flickering streetlamp in pouring rain, noir aesthetic",                     "New Thriller Series"),
    ("thriller-psychological", "fractured shattered mirror reflecting a partially obscured face, distorted reflection, dark mood",             "Psychological"),
    ("thriller-crime",         "crime scene perimeter at night with yellow police tape, red and blue police lights, gritty urban street",      "Crime Thriller"),
    ("thriller-action",        "massive cinematic explosion with debris and flames against dark night sky, action movie still",                "Action Thriller"),
    # Zombie
    ("zombie-new-movies",      "post-apocalyptic abandoned city street overrun with shambling decaying undead figures at dusk, debris",        "New Zombie Movies"),
    ("zombie-new-series",      "ruined overgrown city skyline with crumbling buildings, ash falling, desolate atmosphere",                     "New Zombie Series"),
    ("zombie-comedy",          "decaying zombie hand bursting out of moonlit cemetery grave, halloween theatrical atmosphere",                 "Zombie Comedy"),
    ("zombie-survival",        "wasteland survivor in tactical gear behind makeshift barricade, dust storm, desperate atmosphere",             "Survival Horror"),
    # Space
    ("space-new-movies",       "majestic colorful nebula and distant galaxy with bright stars, deep space cinematic vista",                    "New Space Movies"),
    ("space-new-series",       "interior of futuristic spaceship cockpit with starfield visible through curved windshield",                    "New Space Series"),
    ("space-alien",            "metallic flying saucer hovering ominously above dark farm landscape under stormy sky",                         "Alien Invasion"),
    ("space-exploration",      "lone astronaut standing on alien planet surface with rings and distant stars overhead",                        "Space Exploration"),
    ("space-opera",            "epic capital starship battle with laser beams and debris in deep space, cinematic sci-fi",                     "Space Opera"),
    # Mystery
    ("mystery-new-movies",     "dimly lit detective desk with scattered case files, magnifying glass, vintage typewriter, low warm lamp",      "New Mystery Movies"),
    ("mystery-new-series",     "noir detective silhouette in trench coat through venetian blinds shadows, smoky atmosphere",                   "New Mystery Series"),
    ("mystery-detective",      "vintage 1940s detective office at night with desk lamp, file folders, fedora hat on coat rack",                "Detective"),
    ("mystery-whodunit",       "elegant old mansion library at night with candlelight, leather armchairs, antique books, fireplace",           "Whodunit"),
    ("mystery-conspiracy",     "shadowy silhouettes of suited figures in a smoke-filled room with hanging single bulb, secret meeting",        "Conspiracy"),
    # Science Fiction
    ("scifi-new-movies",       "neon-soaked futuristic cyberpunk megacity skyline at night with flying vehicles and holograms",                "New Sci-Fi Movies"),
    ("scifi-new-series",       "sleek polished interior of advanced spaceship corridor with glowing console panels and viewports",             "New Sci-Fi Series"),
    ("scifi-dystopian",        "rain-drenched dystopian cyberpunk city with crumbling neon-lit megastructures and smog",                       "Dystopian"),
    ("scifi-ai",               "humanoid android face with glowing circuitry beneath translucent skin, cool blue lighting",                    "AI & Robots"),
    ("scifi-timetravel",       "swirling glowing time vortex portal in dark room, energy ripples, cinematic sci-fi",                           "Time Travel"),
    # Apocalyptic
    ("apoc-new-movies",        "post-apocalyptic desolate wasteland at fiery sunset with ruined freeway and abandoned cars",                   "New Apocalyptic"),
    ("apoc-new-series",        "ruined collapsed city skyline at dusk with smoke columns rising and ash falling, desolate",                    "Apocalyptic Series"),
    ("apoc-post",              "abandoned skyscrapers reclaimed by overgrown nature and vines, deserted cityscape, eerie quiet",               "Post-Apocalyptic"),
    ("apoc-pandemic",          "ominous laboratory with glowing biohazard containment chambers and hazmat suits, dark atmosphere",             "Pandemic"),
    ("apoc-nuclear",           "distant nuclear mushroom cloud rising over desolate desert horizon, dramatic atmosphere",                      "Nuclear War"),
    ("apoc-dystopia",          "totalitarian dystopian future cityscape with massive screens, surveillance drones, oppressive neon",           "Dystopian Future"),
    # Natural Disaster
    ("disaster-new-movies",    "massive tornado funnel with lightning over dark stormy plains, dramatic cinematic disaster",                   "New Disaster Movies"),
    ("disaster-new-series",    "dramatic dark stormy sky with rolling thunderclouds and lightning, foreboding atmosphere",                     "Disaster Series"),
    ("disaster-earth",         "erupting volcano spewing red glowing lava and ash into night sky, dramatic geological catastrophe",            "Earthquakes & Volcanoes"),
    ("disaster-water",         "enormous towering tsunami wave crashing toward dark coastline at sunset, dramatic ocean disaster",             "Tsunamis & Floods"),
    ("disaster-storm",         "swirling massive hurricane cyclone with rain and lightning over angry ocean, aerial view",                     "Storms & Hurricanes"),
    ("disaster-space",         "giant asteroid streaking through atmosphere toward earth horizon, fire trail, dramatic cosmic",                "Asteroid & Cosmic"),
]

# ─── Branded franchises (copied as-is from rrevanth) ────────────────
# 17 franchises with official key art. No text overlay applied (logos baked in).
RREV = "https://raw.githubusercontent.com/rrevanth/nuvio-assets/main/franchises"
BRANDED = {
    "fr-starwars":    (f"{RREV}/star-wars/star-wars-landscape.jpg",                  "jpg"),
    "fr-mcu":         (f"{RREV}/mcu/mcu-landscape.gif",                              "gif"),
    "fr-harrypotter": (f"{RREV}/wizarding-world/wizarding-world-landscape.png",      "png"),
    "fr-middleearth": (f"{RREV}/lord-of-the-rings/lord-of-the-rings-landscape.jpg",  "jpg"),
    "fr-jurassic":    (f"{RREV}/jurassic-world/jurassic-world-landscape.jpg",        "jpg"),
    "fr-bond":        (f"{RREV}/007/007-landscape.jpg",                              "jpg"),
    "fr-mi":          (f"{RREV}/mission-impossible/mission-impossible-landscape.jpg","jpg"),
    "fr-johnwick":    (f"{RREV}/john-wick/john-wick-landscape.jpg",                  "jpg"),
    "fr-hungergames": (f"{RREV}/hunger-games/hunger-games-landscape.jpg",            "jpg"),
    "fr-pirates":     (f"{RREV}/pirates-caribbean/pirates-caribbean-landscape.jpg",  "jpg"),
    "fr-indianajones":(f"{RREV}/indiana-jones/indiana-jones-landscape.jpg",          "jpg"),
    "fr-avatar":      (f"{RREV}/avatar/avatar-landscape.jpg",                        "jpg"),
    "fr-dc":          (f"{RREV}/dc-universe/dc-universe-landscape.jpg",              "jpg"),
    "fr-dune":        (f"{RREV}/dune/dune-landscape.jpg",                            "jpg"),
    "fr-godfather":   (f"{RREV}/godfather/godfather-landscape.jpg",                  "jpg"),
    "fr-transformers":(f"{RREV}/transformers/transformers-landscape.jpg",            "jpg"),
    "fr-xmen":        (f"{RREV}/x-men/x-men-landscape.jpg",                          "jpg"),
}

# ─── Franchise fallbacks: TMDB collection backdrop + Bebas Neue title ──
# 17 franchises rrevanth doesn't have. TMDB backdrop quality varies — some are
# proper franchise key art, some are just a movie still. Title overlay is added.
TMDB_COLLECTIONS = [
    # Live-action sci-fi / action franchises
    ("fr-fast",         "9485",   "Fast & Furious"),
    ("fr-matrix",       "2344",   "The Matrix"),
    ("fr-terminator",   "528",    "Terminator"),
    ("fr-alien",        "8091",   "Alien"),
    ("fr-predator",     "399",    "Predator"),
    ("fr-madmax",       "8945",   "Mad Max"),
    ("fr-planetapes",   "173710", "Planet of the Apes"),
    ("fr-monsterverse", "535313", "MonsterVerse"),
    ("fr-startrek",     "115575", "Star Trek"),
    # Animation franchises (Pixar / DreamWorks / Illumination / Blue Sky)
    ("fr-toystory",     "10194",  "Toy Story"),
    ("fr-cars",         "87118",  "Cars"),
    ("fr-shrek",        "2150",   "Shrek"),
    ("fr-httyd",        "89137",  "How to Train Your Dragon"),
    ("fr-kungfupanda",  "77816",  "Kung Fu Panda"),
    ("fr-madagascar",   "14740",  "Madagascar"),
    ("fr-despicableme", "86066",  "Despicable Me"),
    ("fr-iceage",       "8354",   "Ice Age"),
]


def already(slug, ext="jpg"):
    return (OUT_DIR / f"{slug}.{ext}").exists() and not OVERWRITE


def font_at(size):
    """Return Bebas Neue at the given size, falling back to DejaVu Sans Bold."""
    path = FONT_PATH if Path(FONT_PATH).exists() else FALLBACK_FONT
    return ImageFont.truetype(path, size)


def fit_font(text, max_width, max_size=220):
    """Pick the largest Bebas Neue size that keeps `text` within max_width."""
    for size in range(max_size, 50, -4):
        font = font_at(size)
        bbox = font.getbbox(text)
        if bbox[2] - bbox[0] <= max_width:
            return font
    return font_at(50)


def apply_text_overlay(img_bytes, label):
    """Resize to 16:9, darken bottom area, overlay big Bebas Neue title."""
    img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
    img = ImageOps.fit(img, (TILE_W, TILE_H), Image.LANCZOS)

    # Vertical gradient: transparent top → ~88% black bottom for text legibility.
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    odraw = ImageDraw.Draw(overlay)
    for y in range(TILE_H):
        t = max(0.0, (y - TILE_H * 0.40) / (TILE_H * 0.60))
        a = int(225 * (t ** 1.5))
        odraw.line([(0, y), (TILE_W, y)], fill=(0, 0, 0, a))
    img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")

    draw = ImageDraw.Draw(img)
    text = label.upper()
    font = fit_font(text, max_width=int(TILE_W * 0.85), max_size=220)
    bbox = draw.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    x = (TILE_W - tw) // 2
    y = TILE_H - th - 110

    # White text with bold black stroke for legibility on any background.
    draw.text((x, y), text, font=font, fill="white",
              stroke_width=6, stroke_fill="black")

    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=90)
    return buf.getvalue()


def build_prompt(scene):
    return (
        f"Movie streaming app collection banner art. "
        f"{STYLE}. "
        f"Scene: {scene}. "
        f"Atmospheric and evocative, no text, no title, no letters, no words, "
        f"no logos, no captions, no signage. "
        f"{NEGATIVE}."
    )


def fetch_pollinations(prompt, seed=None):
    if seed is None:
        seed = abs(hash(prompt)) % 1_000_000
    p = urllib.parse.quote(prompt, safe="")
    url = (f"{POLLINATIONS_BASE}{p}"
           f"?width={TILE_W}&height={TILE_H}"
           f"&model=flux&seed={seed}&nologo=true&private=true&enhance=true")
    r = requests.get(url, timeout=180)
    r.raise_for_status()
    return r.content


def make_ai_tile(slug, scene, title):
    if already(slug):
        print(f"  [skip] {slug}")
        return True
    prompt = build_prompt(scene)
    try:
        img = fetch_pollinations(prompt)
        labeled = apply_text_overlay(img, title)
        (OUT_DIR / f"{slug}.jpg").write_bytes(labeled)
        print(f"  [ok]   {slug:<22} '{title}'")
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


def pick_best_fanart(items, prefer_lang="en"):
    """Pick the best fanart.tv asset: prefer matching language, then most likes."""
    if not items:
        return None
    def score(it):
        lang = (it.get("lang") or "").lower()
        lang_match = 2 if lang == prefer_lang else (1 if lang in ("", "00") else 0)
        try:
            likes = int(it.get("likes") or "0")
        except (TypeError, ValueError):
            likes = 0
        return (lang_match, likes)
    return max(items, key=score).get("url")


def fetch_fanart_data(tmdb_id):
    """Get fanart.tv data for a TMDB id (movie or collection). Returns None on miss."""
    if not FANART_KEY:
        return None
    try:
        r = requests.get(
            f"https://webservice.fanart.tv/v3/movies/{tmdb_id}",
            params={"api_key": FANART_KEY},
            timeout=20,
        )
        if r.status_code == 404:
            return None
        r.raise_for_status()
        return r.json()
    except Exception:
        return None


def fetch_tmdb_collection(collection_id):
    """Get TMDB collection metadata (for backdrop + member movie IDs)."""
    if not TMDB_KEY:
        return None
    try:
        r = requests.get(
            f"https://api.themoviedb.org/3/collection/{collection_id}",
            params={"api_key": TMDB_KEY}, timeout=20,
        )
        r.raise_for_status()
        return r.json()
    except Exception:
        return None


def composite_logo_on_bg(bg_bytes, logo_bytes):
    """Resize bg to 16:9, paste hdmovielogo centered in the lower portion."""
    img = Image.open(io.BytesIO(bg_bytes)).convert("RGB")
    img = ImageOps.fit(img, (TILE_W, TILE_H), Image.LANCZOS)

    # Soft vertical gradient so the logo reads cleanly even on busy backgrounds.
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    odraw = ImageDraw.Draw(overlay)
    for y in range(TILE_H):
        t = max(0.0, (y - TILE_H * 0.30) / (TILE_H * 0.70))
        a = int(140 * (t ** 1.4))
        odraw.line([(0, y), (TILE_W, y)], fill=(0, 0, 0, a))
    img_rgba = Image.alpha_composite(img.convert("RGBA"), overlay)

    logo = Image.open(io.BytesIO(logo_bytes)).convert("RGBA")
    max_w = int(TILE_W * 0.60)
    max_h = int(TILE_H * 0.32)
    logo.thumbnail((max_w, max_h), Image.LANCZOS)
    lx = (TILE_W - logo.width) // 2
    ly = int(TILE_H * 0.62) - logo.height // 2
    img_rgba.paste(logo, (lx, ly), logo)

    out = img_rgba.convert("RGB")
    buf = io.BytesIO()
    out.save(buf, "JPEG", quality=92)
    return buf.getvalue()


def fetch_franchise(slug, collection_id, label):
    """fanart.tv (bg+logo) → fanart.tv (bg+text) → TMDB (backdrop+text)."""
    if already(slug):
        print(f"  [skip] {slug}")
        return True

    # Pull collection data once so we can enumerate member movies if needed.
    tmdb_data = fetch_tmdb_collection(collection_id)

    # Try fanart.tv directly with the TMDB collection ID first.
    fart = fetch_fanart_data(collection_id)

    # If the collection ID had no fanart.tv data, walk member movies.
    if FANART_KEY and (not fart or not (fart.get("moviebackground") or fart.get("hdmovielogo"))):
        for movie in (tmdb_data.get("parts") if tmdb_data else [])[:6]:
            mv = fetch_fanart_data(movie.get("id"))
            if mv and (mv.get("moviebackground") or mv.get("hdmovielogo")):
                fart = mv
                break

    bg_bytes = None
    logo_bytes = None
    source = "?"

    if fart:
        bg_url = pick_best_fanart(fart.get("moviebackground", []))
        logo_url = pick_best_fanart(fart.get("hdmovielogo", []))
        if bg_url:
            try:
                bg_bytes = requests.get(bg_url, timeout=30).content
                source = "fanart.tv"
            except Exception as e:
                print(f"  [warn] {slug}: fanart bg download failed: {e}")
        if logo_url:
            try:
                logo_bytes = requests.get(logo_url, timeout=30).content
            except Exception as e:
                print(f"  [warn] {slug}: fanart logo download failed: {e}")

    # Fall back to TMDB collection backdrop if fanart.tv had nothing.
    if not bg_bytes and tmdb_data:
        backdrop = tmdb_data.get("backdrop_path")
        if not backdrop:
            for movie in (tmdb_data.get("parts") or []):
                if movie.get("backdrop_path"):
                    backdrop = movie["backdrop_path"]
                    break
        if backdrop:
            try:
                bg_bytes = requests.get(
                    f"https://image.tmdb.org/t/p/original{backdrop}", timeout=30,
                ).content
                source = "TMDB"
            except Exception as e:
                print(f"  [warn] {slug}: TMDB bg download failed: {e}")

    if not bg_bytes:
        print(f"  [miss] {slug} -- no art from fanart.tv or TMDB")
        return False

    if logo_bytes:
        try:
            result = composite_logo_on_bg(bg_bytes, logo_bytes)
            kind = "bg+logo"
        except Exception as e:
            print(f"  [warn] {slug}: logo composite failed ({e}), falling back to text")
            result = apply_text_overlay(bg_bytes, label)
            kind = "bg+text"
    else:
        result = apply_text_overlay(bg_bytes, label)
        kind = "bg+text"

    (OUT_DIR / f"{slug}.jpg").write_bytes(result)
    print(f"  [ok]   {slug:<22} ({label}, {source} {kind})")
    return True


def run_parallel_ai(label, items):
    print(f"\n== {label} ({len(items)} AI-generated, {WORKERS} workers) ==")
    ok = 0
    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        futs = {pool.submit(make_ai_tile, s, sc, t): s for s, sc, t in items}
        for fut in as_completed(futs):
            try:
                if fut.result():
                    ok += 1
            except Exception as e:
                print(f"  [err]  {futs[fut]}: {e}")
    return ok


def main():
    print(f"Output: {OUT_DIR.absolute()}   OVERWRITE={OVERWRITE}   WORKERS={WORKERS}")
    print(f"AI:     Pollinations.ai (Flux model, free, no key)")
    print(f"TMDB:   {'configured' if TMDB_KEY else 'NO KEY — franchise fallbacks will skip'}")
    print(f"FanArt: {'configured' if FANART_KEY else 'NO KEY — TMDB only for fallback art'}")
    print(f"Font:   {FONT_PATH if Path(FONT_PATH).exists() else FALLBACK_FONT + ' (Bebas Neue not found)'}")

    print("\n== Branded franchise art (from rrevanth) ==")
    b_ok = sum(copy_branded(s, u, e) for s, (u, e) in BRANDED.items())

    print(f"\n== Franchise fallbacks ({len(TMDB_COLLECTIONS)} via fanart.tv → TMDB) ==")
    if not TMDB_KEY and not FANART_KEY:
        print("  Neither TMDB_API_KEY nor FANART_API_KEY set — skipping franchise fallbacks.")
        f_ok = 0
    else:
        f_ok = 0
        for slug, cid, label in TMDB_COLLECTIONS:
            if fetch_franchise(slug, cid, label):
                f_ok += 1
            time.sleep(0.2)

    t_ok = run_parallel_ai("Themed tiles", THEMES)

    print(f"\nDone. Branded {b_ok}/{len(BRANDED)}, "
          f"Franchise {f_ok}/{len(TMDB_COLLECTIONS)}, "
          f"Themed AI {t_ok}/{len(THEMES)}.")


if __name__ == "__main__":
    main()
