"""
fetch_all_assets.py v6 — themed tiles via AI (no text), franchise tiles via TMDB.

Sources:
  1. 41 themed tiles      — Pollinations (Flux), no text, cinematic genre scenes
  2. 11 branded franchises — copied as-is from rrevanth (official key art with logos)
  3.  8 franchise fallbacks — TMDB collection backdrops (real franchise marketing art)

Required env vars (set via workflow inputs):
  TMDB_API_KEY  — for franchise fallback backdrops (Pollinations is keyless)

Optional:
  OVERWRITE=1   — regenerate existing files (default: skip)
  WORKERS=N     — parallel AI requests (default: 6)
"""

import os, sys, time, urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

try:
    import requests
except ImportError:
    sys.exit("Run: pip install requests")

WORKERS = int(os.environ.get("WORKERS", "6"))
TMDB_KEY = os.environ.get("TMDB_API_KEY", "").strip()
OVERWRITE = os.environ.get("OVERWRITE", "0") == "1"
OUT_DIR = Path("assets")
OUT_DIR.mkdir(exist_ok=True)

POLLINATIONS_BASE = "https://image.pollinations.ai/prompt/"
TILE_W, TILE_H = 1920, 1080

NEGATIVE = ("no anime, no manga, no cartoon, no illustration, no drawing, "
            "no digital painting, no 3d render, no chibi, no childish")
STYLE = ("photorealistic cinematic film still aesthetic, "
         "dramatic atmospheric lighting, professionally designed movie streaming banner, "
         "widescreen 16:9 landscape composition")

# ─── Themed tiles: (slug, scene description, title - for logging only) ──
THEMES = [
    # Horror
    ("horror-new-movies",      "haunted misty dark forest with eerie moonlight piercing through skeletal bare trees, fog rolling on ground", "NEW HORROR MOVIES"),
    ("horror-new-series",      "abandoned dark hospital corridor with flickering fluorescent lights, peeling wallpaper, ominous shadows",     "NEW HORROR SERIES"),
    ("horror-supernatural",    "victorian haunted manor at night, glowing ghostly figure visible in attic window, swirling fog",               "SUPERNATURAL"),
    ("horror-slasher",         "rain-soaked dark alley with neon reflection, ominous silhouette holding bloody blade, noir lighting",          "SLASHER"),
    ("horror-creature",        "menacing monster silhouette emerging from dark cave entrance with glowing yellow eyes, dense fog",             "CREATURE FEATURE"),
    # Thriller
    ("thriller-new-movies",    "rain-drenched neon-lit city street at night with reflective wet asphalt, lone figure walking",                 "NEW THRILLER MOVIES"),
    ("thriller-new-series",    "shadowy silhouetted figure under a flickering streetlamp in pouring rain, noir aesthetic",                     "NEW THRILLER SERIES"),
    ("thriller-psychological", "fractured shattered mirror reflecting a partially obscured face, distorted reflection, dark mood",             "PSYCHOLOGICAL"),
    ("thriller-crime",         "crime scene perimeter at night with yellow police tape, red and blue police lights, gritty urban street",      "CRIME THRILLER"),
    ("thriller-action",        "massive cinematic explosion with debris and flames against dark night sky, action movie still",                "ACTION THRILLER"),
    # Zombie
    ("zombie-new-movies",      "post-apocalyptic abandoned city street overrun with shambling decaying undead figures at dusk, debris",        "NEW ZOMBIE MOVIES"),
    ("zombie-new-series",      "ruined overgrown city skyline with crumbling buildings, ash falling, desolate atmosphere",                     "NEW ZOMBIE SERIES"),
    ("zombie-comedy",          "decaying zombie hand bursting out of moonlit cemetery grave, halloween theatrical atmosphere",                 "ZOMBIE COMEDY"),
    ("zombie-survival",        "wasteland survivor in tactical gear behind makeshift barricade, dust storm, desperate atmosphere",             "SURVIVAL HORROR"),
    # Space
    ("space-new-movies",       "majestic colorful nebula and distant galaxy with bright stars, deep space cinematic vista",                    "NEW SPACE MOVIES"),
    ("space-new-series",       "interior of futuristic spaceship cockpit with starfield visible through curved windshield",                    "NEW SPACE SERIES"),
    ("space-alien",            "metallic flying saucer hovering ominously above dark farm landscape under stormy sky",                         "ALIEN INVASION"),
    ("space-exploration",      "lone astronaut standing on alien planet surface with rings and distant stars overhead",                        "SPACE EXPLORATION"),
    ("space-opera",            "epic capital starship battle with laser beams and debris in deep space, cinematic sci-fi",                     "SPACE OPERA"),
    # Mystery
    ("mystery-new-movies",     "dimly lit detective desk with scattered case files, magnifying glass, vintage typewriter, low warm lamp",      "NEW MYSTERY MOVIES"),
    ("mystery-new-series",     "noir detective silhouette in trench coat through venetian blinds shadows, smoky atmosphere",                   "NEW MYSTERY SERIES"),
    ("mystery-detective",      "vintage 1940s detective office at night with desk lamp, file folders, fedora hat on coat rack",                "DETECTIVE"),
    ("mystery-whodunit",       "elegant old mansion library at night with candlelight, leather armchairs, antique books, fireplace",           "WHODUNIT"),
    ("mystery-conspiracy",     "shadowy silhouettes of suited figures in a smoke-filled room with hanging single bulb, secret meeting",        "CONSPIRACY"),
    # Science Fiction
    ("scifi-new-movies",       "neon-soaked futuristic cyberpunk megacity skyline at night with flying vehicles and holograms",                "NEW SCI-FI MOVIES"),
    ("scifi-new-series",       "sleek polished interior of advanced spaceship corridor with glowing console panels and viewports",             "NEW SCI-FI SERIES"),
    ("scifi-dystopian",        "rain-drenched dystopian cyberpunk city with crumbling neon-lit megastructures and smog",                       "DYSTOPIAN"),
    ("scifi-ai",               "humanoid android face with glowing circuitry beneath translucent skin, cool blue lighting",                    "AI AND ROBOTS"),
    ("scifi-timetravel",       "swirling glowing time vortex portal in dark room, energy ripples, cinematic sci-fi",                           "TIME TRAVEL"),
    # Apocalyptic
    ("apoc-new-movies",        "post-apocalyptic desolate wasteland at fiery sunset with ruined freeway and abandoned cars",                   "NEW APOCALYPTIC"),
    ("apoc-new-series",        "ruined collapsed city skyline at dusk with smoke columns rising and ash falling, desolate",                    "APOCALYPTIC SERIES"),
    ("apoc-post",              "abandoned skyscrapers reclaimed by overgrown nature and vines, deserted cityscape, eerie quiet",               "POST-APOCALYPTIC"),
    ("apoc-pandemic",          "ominous laboratory with glowing biohazard containment chambers and hazmat suits, dark atmosphere",             "PANDEMIC"),
    ("apoc-nuclear",           "distant nuclear mushroom cloud rising over desolate desert horizon, dramatic atmosphere",                      "NUCLEAR WAR"),
    ("apoc-dystopia",          "totalitarian dystopian future cityscape with massive screens, surveillance drones, oppressive neon",           "DYSTOPIAN FUTURE"),
    # Natural Disaster
    ("disaster-new-movies",    "massive tornado funnel with lightning over dark stormy plains, dramatic cinematic disaster",                   "NEW DISASTER MOVIES"),
    ("disaster-new-series",    "dramatic dark stormy sky with rolling thunderclouds and lightning, foreboding atmosphere",                     "DISASTER SERIES"),
    ("disaster-earth",         "erupting volcano spewing red glowing lava and ash into night sky, dramatic geological catastrophe",            "EARTHQUAKES"),
    ("disaster-water",         "enormous towering tsunami wave crashing toward dark coastline at sunset, dramatic ocean disaster",             "TSUNAMIS"),
    ("disaster-storm",         "swirling massive hurricane cyclone with rain and lightning over angry ocean, aerial view",                     "STORMS"),
    ("disaster-space",         "giant asteroid streaking through atmosphere toward earth horizon, fire trail, dramatic cosmic",                "ASTEROID"),
]

# ─── Branded franchises (copied as-is from rrevanth) ────────────────
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

# ─── Franchise fallbacks: TMDB collection ID → real franchise key art ──
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


def already(slug, ext="jpg"):
    return (OUT_DIR / f"{slug}.{ext}").exists() and not OVERWRITE


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
        (OUT_DIR / f"{slug}.jpg").write_bytes(img)
        print(f"  [ok]   {slug:<22} ({title})")
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


def fetch_tmdb_franchise(slug, collection_id, label):
    """Fetch a franchise's TMDB collection backdrop and save as-is (no overlay)."""
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
        # Prefer the collection-level backdrop (usually franchise key art).
        backdrop = data.get("backdrop_path")
        if not backdrop:
            # Fall back to the first movie's backdrop.
            for movie in (data.get("parts") or []):
                if movie.get("backdrop_path"):
                    backdrop = movie["backdrop_path"]
                    break
        if not backdrop:
            print(f"  [miss] {slug} -- no backdrop in TMDB collection {collection_id}")
            return False
        img_url = f"https://image.tmdb.org/t/p/original{backdrop}"
        img_bytes = requests.get(img_url, timeout=30).content
        (OUT_DIR / f"{slug}.jpg").write_bytes(img_bytes)
        print(f"  [ok]   {slug:<22} ({label}, TMDB col {collection_id})")
        return True
    except Exception as e:
        print(f"  [err]  {slug}: {e}")
        return False


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

    print("\n== Branded franchise art (from rrevanth) ==")
    b_ok = sum(copy_branded(s, u, e) for s, (u, e) in BRANDED.items())

    print(f"\n== Franchise fallbacks ({len(TMDB_COLLECTIONS)} TMDB collection backdrops) ==")
    if not TMDB_KEY:
        print("  TMDB_API_KEY not set — skipping franchise fallbacks.")
        f_ok = 0
    else:
        f_ok = 0
        for slug, cid, label in TMDB_COLLECTIONS:
            if fetch_tmdb_franchise(slug, cid, label):
                f_ok += 1
            time.sleep(0.2)

    t_ok = run_parallel_ai("Themed tiles", THEMES)

    print(f"\nDone. Branded {b_ok}/{len(BRANDED)}, "
          f"Franchise TMDB {f_ok}/{len(TMDB_COLLECTIONS)}, "
          f"Themed AI {t_ok}/{len(THEMES)}.")


if __name__ == "__main__":
    main()
