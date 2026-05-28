"""
fetch_all_assets.py v5 — AI-generated tiles via Pollinations.ai (free, no API key).

Pollinations.ai is a free, no-signup AI image gen service backed by Flux models.
Each tile is a pure cinematic scene with NO baked-in title text — Nuvio's row
header provides the label, so the tile is just visual mood/imagery.

Sources:
  1. 41 themed tiles      — Pollinations (Flux), no text, cinematic genre scenes
  2. 11 branded franchises — copied as-is from rrevanth (official logos on the art)
  3.  8 franchise fallbacks — Pollinations (Flux), no text, iconic franchise scenes

Optional env vars:
  OVERWRITE=1   — regenerate existing files (default: skip)
  WORKERS=N     — parallel AI requests (default: 6)
"""

import os, sys, urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

try:
    import requests
except ImportError:
    sys.exit("Run: pip install requests")

WORKERS = int(os.environ.get("WORKERS", "6"))

OVERWRITE = os.environ.get("OVERWRITE", "0") == "1"
OUT_DIR = Path("assets")
OUT_DIR.mkdir(exist_ok=True)

POLLINATIONS_BASE = "https://image.pollinations.ai/prompt/"
TILE_W, TILE_H = 1920, 1080

# Hard constraints stamped into every prompt to keep style consistent.
NEGATIVE = ("no anime, no manga, no cartoon, no illustration, no drawing, "
            "no digital painting, no 3d render, no chibi, no childish")
STYLE = ("photorealistic cinematic film still aesthetic, "
         "dramatic atmospheric lighting, professionally designed movie streaming banner, "
         "widescreen 16:9 landscape composition")

# ─── Themed tiles: (slug, scene description, title text to render) ──
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

# ─── Branded franchises (copied as-is from rrevanth, no AI needed) ──
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

# ─── Franchise fallbacks: scene prompts crafted around iconic visuals ──
# Avoid copyright-named characters; describe style/atmosphere instead.
FRANCHISE_PROMPTS = [
    ("fr-fast",         "underground street racing scene with neon-lit modified sports cars on rain-slicked nighttime asphalt, dramatic action",   "FAST AND FURIOUS"),
    ("fr-matrix",       "vertical streams of glowing green digital code raining down dark background, cyberpunk computer terminal aesthetic",       "THE MATRIX"),
    ("fr-terminator",   "menacing chrome metallic humanoid robot endoskeleton with glowing red eyes in dark industrial setting, sci-fi",            "TERMINATOR"),
    ("fr-alien",        "dark biomechanical spaceship corridor with dripping condensation, claustrophobic horror sci-fi atmosphere",                "ALIEN"),
    ("fr-predator",     "dense humid jungle scene viewed through heat thermal vision filter, predator perspective, hunter aesthetic",               "PREDATOR"),
    ("fr-madmax",       "post-apocalyptic desert wasteland with armored modified vehicles in dust storm, fire and chaos, dramatic action",          "MAD MAX"),
    ("fr-planetapes",   "intelligent ape silhouette on horseback in misty post-apocalyptic forest, dystopian dramatic atmosphere",                   "PLANET OF THE APES"),
    ("fr-monsterverse", "colossal kaiju monster silhouette destroying modern city skyline at night, dramatic atmospheric scale",                    "MONSTERVERSE"),
]


def already(slug, ext="jpg"):
    return (OUT_DIR / f"{slug}.{ext}").exists() and not OVERWRITE


def build_prompt(scene, title):
    # title is kept in the data tuple for logging/documentation only.
    # No text is requested from the AI — Flux's text rendering is unreliable
    # and Nuvio's row header provides the title separately.
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
    prompt = build_prompt(scene, title)
    try:
        img = fetch_pollinations(prompt)
        (OUT_DIR / f"{slug}.jpg").write_bytes(img)
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


def run_parallel(label, items):
    """Run make_ai_tile across items with a thread pool."""
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

    print("\n== Branded franchise art (from rrevanth) ==")
    b_ok = sum(copy_branded(s, u, e) for s, (u, e) in BRANDED.items())

    f_ok = run_parallel("Franchise fallbacks", FRANCHISE_PROMPTS)
    t_ok = run_parallel("Themed tiles",        THEMES)

    print(f"\nDone. Branded {b_ok}/{len(BRANDED)}, "
          f"Franchise AI {f_ok}/{len(FRANCHISE_PROMPTS)}, "
          f"Themed AI {t_ok}/{len(THEMES)}.")


if __name__ == "__main__":
    main()
