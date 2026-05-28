"""
fetch_all_assets.py v11 — every tile is a real backdrop + expanded lineup.

Sources:
  1. 86 themed tiles       — TMDB/fanart.tv backdrop of an iconic representative
                             film or series + Bebas Neue genre title overlay
                             (existing 41 + 10 horror/sci-fi sub-genres + 10 comedy
                              + 10 action + 10 drama + 5 animation sub-genres)
  2. 24 actor tiles        — Backdrop of the actor's iconic role + name overlay
  3. 17 branded franchises — copied as-is from rrevanth (official logos baked in)
  4. 17 franchise fallbacks — fanart.tv background composited with hdmovielogo,
                              falling back to TMDB collection backdrop + Bebas Neue

Priority chain (themed and franchise tiles both):
  Movie:  fanart.tv moviebackground → TMDB /movie/{id}/images
  TV:     TMDB /tv/{id}/images (fanart.tv TV needs TheTVDB IDs, skipped)
  Logo:   fanart.tv hdmovielogo for franchise tiles (composited if present)

Required env vars (set via workflow inputs):
  TMDB_API_KEY   — for TMDB images endpoints
  FANART_API_KEY — for fanart.tv backgrounds and franchise logos

Optional:
  OVERWRITE=1   — regenerate existing files (default: skip)
  WORKERS=N     — parallel HTTP fetches (default: 6)
  FONT_PATH=... — override the TTF location (default: /tmp/BebasNeue-Regular.ttf)
"""

import io
import os
import sys
import time
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

TILE_W, TILE_H = 1920, 1080

# Bebas Neue — downloaded by the workflow before this script runs.
FONT_PATH = os.environ.get("FONT_PATH", "/tmp/BebasNeue-Regular.ttf")
FALLBACK_FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

# ─── Themed tiles: (slug, label, tmdb_id, media_type) ───────────────
# Each row uses ONE iconic representative film or series, chosen to fit the
# genre/keyword filter of the matching Nuvio collection row.
THEMES = [
    # Horror
    ("horror-new-movies",      "New Horror Movies",     933260, "MOVIE"),   # The Substance
    ("horror-new-series",      "New Horror Series",     70713,  "TV"),      # The Haunting of Hill House
    ("horror-supernatural",    "Supernatural",          138843, "MOVIE"),   # The Conjuring
    ("horror-slasher",         "Slasher",               948,    "MOVIE"),   # Halloween (1978)
    ("horror-creature",        "Creature Feature",      447332, "MOVIE"),   # A Quiet Place
    # Thriller
    ("thriller-new-movies",    "New Thriller Movies",   929590, "MOVIE"),   # Civil War (2024)
    ("thriller-new-series",    "New Thriller Series",   62560,  "TV"),      # Mr. Robot
    ("thriller-psychological", "Psychological",         419430, "MOVIE"),   # Get Out
    ("thriller-crime",         "Crime Thriller",        1422,   "MOVIE"),   # The Departed
    ("thriller-action",        "Action Thriller",       155,    "MOVIE"),   # The Dark Knight
    # Zombie
    ("zombie-new-movies",      "New Zombie Movies",     396535, "MOVIE"),   # Train to Busan
    ("zombie-new-series",      "New Zombie Series",     1402,   "TV"),      # The Walking Dead
    ("zombie-comedy",          "Zombie Comedy",         19908,  "MOVIE"),   # Zombieland
    ("zombie-survival",        "Survival Horror",       170,    "MOVIE"),   # 28 Days Later
    # Space
    ("space-new-movies",       "New Space Movies",      157336, "MOVIE"),   # Interstellar
    ("space-new-series",       "New Space Series",      63639,  "TV"),      # The Expanse
    ("space-alien",            "Alien Invasion",        329865, "MOVIE"),   # Arrival
    ("space-exploration",      "Space Exploration",     286217, "MOVIE"),   # The Martian
    ("space-opera",            "Space Opera",           11,     "MOVIE"),   # Star Wars: A New Hope
    # Mystery
    ("mystery-new-movies",     "New Mystery Movies",    546554, "MOVIE"),   # Knives Out
    ("mystery-new-series",     "New Mystery Series",    19885,  "TV"),      # Sherlock
    ("mystery-detective",      "Detective",             22538,  "MOVIE"),   # Sherlock Holmes (2009)
    ("mystery-whodunit",       "Whodunit",              661374, "MOVIE"),   # Glass Onion
    ("mystery-conspiracy",     "Conspiracy",            308,    "MOVIE"),   # All the President's Men
    # Sci-Fi
    ("scifi-new-movies",       "New Sci-Fi Movies",     693134, "MOVIE"),   # Dune: Part Two
    ("scifi-new-series",       "New Sci-Fi Series",     95396,  "TV"),      # Severance
    ("scifi-dystopian",        "Dystopian",             335984, "MOVIE"),   # Blade Runner 2049
    ("scifi-ai",               "AI & Robots",           264660, "MOVIE"),   # Ex Machina
    ("scifi-timetravel",       "Time Travel",           105,    "MOVIE"),   # Back to the Future
    # Apocalyptic
    ("apoc-new-movies",        "New Apocalyptic",       646380, "MOVIE"),   # Don't Look Up
    ("apoc-new-series",        "Apocalyptic Series",    100088, "TV"),      # The Last of Us
    ("apoc-post",              "Post-Apocalyptic",      76341,  "MOVIE"),   # Mad Max: Fury Road
    ("apoc-pandemic",          "Pandemic",              12493,  "MOVIE"),   # Contagion
    ("apoc-nuclear",           "Nuclear War",           872585, "MOVIE"),   # Oppenheimer
    ("apoc-dystopia",          "Dystopian Future",      9693,   "MOVIE"),   # Children of Men
    # Natural Disaster
    ("disaster-new-movies",    "New Disaster Movies",   587732, "MOVIE"),   # Greenland
    ("disaster-new-series",    "Disaster Series",       80388,  "TV"),      # Snowpiercer
    ("disaster-earth",         "Earthquakes & Volcanoes", 277216, "MOVIE"), # San Andreas
    ("disaster-water",         "Tsunamis & Floods",     8865,   "MOVIE"),   # Deep Impact
    ("disaster-storm",         "Storms & Hurricanes",   9504,   "MOVIE"),   # Twister (1996)
    ("disaster-space",         "Asteroid & Cosmic",     95,     "MOVIE"),   # Armageddon
    # Horror sub-genres (extended)
    ("horror-body",            "Body Horror",           9426,   "MOVIE"),   # The Fly (1986)
    ("horror-found-footage",   "Found Footage",         2667,   "MOVIE"),   # The Blair Witch Project
    ("horror-folk",            "Folk Horror",           493922, "MOVIE"),   # Hereditary
    ("horror-cosmic",          "Cosmic Horror",         440021, "MOVIE"),   # Color Out of Space
    ("horror-vampire",         "Vampires & Werewolves", 628,    "MOVIE"),   # Interview with the Vampire
    # Sci-Fi sub-genres (extended)
    ("scifi-cyberpunk",        "Cyberpunk",             315837, "MOVIE"),   # Ghost in the Shell (2017)
    ("scifi-hard",             "Hard Sci-Fi",           62,     "MOVIE"),   # 2001: A Space Odyssey
    ("scifi-steampunk",        "Steampunk",             428078, "MOVIE"),   # Mortal Engines
    ("scifi-multiverse",       "Multiverse",            545611, "MOVIE"),   # Everything Everywhere All At Once
    ("scifi-timeloop",         "Time Loop",             137,    "MOVIE"),   # Groundhog Day
    # Comedy
    ("comedy-new-movies",      "New Comedy Movies",     346698, "MOVIE"),   # Barbie
    ("comedy-new-series",      "New Comedy Series",     136315, "TV"),      # The Bear
    ("comedy-romcom",          "Romantic Comedy",       50546,  "MOVIE"),   # Crazy, Stupid, Love
    ("comedy-dark",            "Dark Comedy",           275,    "MOVIE"),   # Fargo (1996)
    ("comedy-buddy",           "Buddy Comedy",          4638,   "MOVIE"),   # Hot Fuzz
    ("comedy-sitcom",          "Sitcoms",               2316,   "TV"),      # The Office (US)
    ("comedy-parody",          "Parody & Spoof",        813,    "MOVIE"),   # Airplane!
    ("comedy-horror",          "Comedy Horror",         102362, "TV"),      # What We Do in the Shadows TV
    # Action
    ("action-new-movies",      "New Action Movies",     575264, "MOVIE"),   # M:I Dead Reckoning
    ("action-new-series",      "New Action Series",     108978, "TV"),      # Reacher
    ("action-martial-arts",    "Martial Arts",          146,    "MOVIE"),   # Crouching Tiger, Hidden Dragon
    ("action-heist",           "Heist",                 161,    "MOVIE"),   # Ocean's Eleven
    ("action-war",             "War",                   857,    "MOVIE"),   # Saving Private Ryan
    ("action-western",         "Western",               429,    "MOVIE"),   # The Good, the Bad and the Ugly
    ("action-military",        "Military",              8093,   "MOVIE"),   # Black Hawk Down
    ("action-spy",             "Spy & Espionage",       207703, "MOVIE"),   # Kingsman: The Secret Service
    ("action-cop",             "Cop & Police",          3179,   "MOVIE"),   # Bad Boys
    ("action-vigilante",       "Vigilante",             12159,  "MOVIE"),   # Death Wish (1974)
    # Drama
    ("drama-new-movies",       "New Drama Movies",      666277, "MOVIE"),   # Past Lives
    ("drama-new-series",       "New Drama Series",      1535,   "TV"),      # Succession
    ("drama-period",           "Period Drama",          4348,   "MOVIE"),   # Pride & Prejudice (2005)
    ("drama-biopic",           "Biographical",          424694, "MOVIE"),   # Bohemian Rhapsody
    ("drama-coming-age",       "Coming-of-Age",         391713, "MOVIE"),   # Lady Bird
    ("drama-courtroom",        "Courtroom",             1614,   "MOVIE"),   # A Few Good Men
    ("drama-medical",          "Medical",               1416,   "TV"),      # Grey's Anatomy
    ("drama-sports",           "Sports",                1366,   "MOVIE"),   # Rocky
    ("drama-family",           "Family",                39446,  "MOVIE"),   # The Kids Are All Right
    ("drama-political",        "Political",             4608,   "TV"),      # The West Wing
    # Animation (new sub-genre rows, separate from animation franchise tiles)
    ("anim-new-movies",        "New Animated Movies",   1022789,"MOVIE"),   # Inside Out 2
    ("anim-new-series",        "New Animated Series",   94605,  "TV"),      # Arcane
    ("anim-disney",            "Disney Classics",       8587,   "MOVIE"),   # The Lion King (1994)
    ("anim-stopmotion",        "Stop-Motion",           308531, "MOVIE"),   # Kubo and the Two Strings
]

# ─── Actors: (slug, label, iconic movie/show id, media_type) ────────
# Each tile uses ONE iconic role's backdrop + the actor's name in Bebas Neue.
ACTORS = [
    ("actor-tcruise",      "Tom Cruise",          361743, "MOVIE"),   # Top Gun: Maverick
    ("actor-ldicaprio",    "Leonardo DiCaprio",   27205,  "MOVIE"),   # Inception
    ("actor-dwashington",  "Denzel Washington",   2675,   "MOVIE"),   # Training Day
    ("actor-thanks",       "Tom Hanks",           13,     "MOVIE"),   # Forrest Gump
    ("actor-bpitt",        "Brad Pitt",           550,    "MOVIE"),   # Fight Club
    ("actor-rdeniro",      "Robert De Niro",      769,    "MOVIE"),   # Goodfellas
    ("actor-cbale",        "Christian Bale",      1359,   "MOVIE"),   # American Psycho
    ("actor-jphoenix",     "Joaquin Phoenix",     475557, "MOVIE"),   # Joker
    ("actor-rgosling",     "Ryan Gosling",        64690,  "MOVIE"),   # Drive
    ("actor-mrobbie",      "Margot Robbie",       402431, "MOVIE"),   # I, Tonya
    ("actor-estone",       "Emma Stone",          792307, "MOVIE"),   # Poor Things
    ("actor-fpugh",        "Florence Pugh",       569094, "MOVIE"),   # Black Widow
    ("actor-atjoy",        "Anya Taylor-Joy",     87739,  "TV"),      # The Queen's Gambit
    ("actor-sjohansson",   "Scarlett Johansson",  153,    "MOVIE"),   # Lost in Translation
    ("actor-wsmith",       "Will Smith",          607,    "MOVIE"),   # Men in Black
    ("actor-kreeves",      "Keanu Reeves",        603,    "MOVIE"),   # The Matrix
    ("actor-hjackman",     "Hugh Jackman",        263115, "MOVIE"),   # Logan
    ("actor-rreynolds",    "Ryan Reynolds",       293660, "MOVIE"),   # Deadpool
    ("actor-rdj",          "Robert Downey Jr.",   1726,   "MOVIE"),   # Iron Man
    ("actor-cpratt",       "Chris Pratt",         118340, "MOVIE"),   # Guardians of the Galaxy
    ("actor-jlawrence",    "Jennifer Lawrence",   82693,  "MOVIE"),   # Silver Linings Playbook
    ("actor-zendaya",      "Zendaya",             85552,  "TV"),      # Euphoria
    ("actor-cblanchett",   "Cate Blanchett",      817758, "MOVIE"),   # Tár
    ("actor-ctheron",      "Charlize Theron",     341013, "MOVIE"),   # Atomic Blonde
]

# ─── Branded franchises (copied as-is from rrevanth) ────────────────
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

# ─── Franchise fallbacks: TMDB collection ID → fanart.tv + TMDB chain ──
TMDB_COLLECTIONS = [
    ("fr-fast",         "9485",   "Fast & Furious"),
    ("fr-matrix",       "2344",   "The Matrix"),
    ("fr-terminator",   "528",    "Terminator"),
    ("fr-alien",        "8091",   "Alien"),
    ("fr-predator",     "399",    "Predator"),
    ("fr-madmax",       "8945",   "Mad Max"),
    ("fr-planetapes",   "173710", "Planet of the Apes"),
    ("fr-monsterverse", "535313", "MonsterVerse"),
    ("fr-startrek",     "115575", "Star Trek"),
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


# ─── Font helpers ───────────────────────────────────────────────────
def font_at(size):
    path = FONT_PATH if Path(FONT_PATH).exists() else FALLBACK_FONT
    return ImageFont.truetype(path, size)


def fit_font(text, max_width, max_size=220):
    for size in range(max_size, 50, -4):
        font = font_at(size)
        bbox = font.getbbox(text)
        if bbox[2] - bbox[0] <= max_width:
            return font
    return font_at(50)


# ─── Image overlays ─────────────────────────────────────────────────
def apply_text_overlay(img_bytes, label):
    """Resize to 16:9, darken bottom area, overlay big Bebas Neue title."""
    img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
    img = ImageOps.fit(img, (TILE_W, TILE_H), Image.LANCZOS)

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

    draw.text((x, y), text, font=font, fill="white",
              stroke_width=6, stroke_fill="black")

    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=90)
    return buf.getvalue()


def composite_logo_on_bg(bg_bytes, logo_bytes):
    """Resize bg to 16:9, paste hdmovielogo centered in the lower portion."""
    img = Image.open(io.BytesIO(bg_bytes)).convert("RGB")
    img = ImageOps.fit(img, (TILE_W, TILE_H), Image.LANCZOS)

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


# ─── External API helpers ───────────────────────────────────────────
def pick_best_fanart(items, prefer_lang="en"):
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


def pick_best_tmdb_backdrop(backdrops):
    """Rank backdrops: English/textless first, then by vote_count * vote_avg."""
    if not backdrops:
        return None
    def rank(b):
        lang = b.get("iso_639_1") or ""
        # Textless (null/"") preferred for overlay use, then English, then anything else.
        lang_pref = 2 if lang == "" else (1 if lang == "en" else 0)
        score = (b.get("vote_count") or 0) * ((b.get("vote_average") or 0) + 1)
        return (lang_pref, score)
    return max(backdrops, key=rank).get("file_path")


def fetch_tmdb_backdrop(media_type, tmdb_id):
    """Return (bytes, source_tag) for the best backdrop on /movie or /tv."""
    if not TMDB_KEY:
        return None, "no-tmdb-key"
    try:
        r = requests.get(
            f"https://api.themoviedb.org/3/{media_type}/{tmdb_id}/images",
            # No include_image_language: some titles tag every backdrop with a
            # non-English language code, which an "en,null" filter would empty out.
            # We rank language preference client-side instead.
            params={"api_key": TMDB_KEY},
            timeout=20,
        )
        r.raise_for_status()
        data = r.json()
        path = pick_best_tmdb_backdrop(data.get("backdrops", []))
        if not path:
            return None, "tmdb-empty"
        img = requests.get(
            f"https://image.tmdb.org/t/p/original{path}", timeout=30,
        ).content
        return img, "tmdb"
    except Exception as e:
        return None, f"tmdb-err:{type(e).__name__}"


def fetch_fanart_movie_bg(tmdb_id):
    fart = fetch_fanart_data(tmdb_id)
    if not fart:
        return None
    url = pick_best_fanart(fart.get("moviebackground", []))
    if not url:
        return None
    try:
        return requests.get(url, timeout=30).content
    except Exception:
        return None


# ─── Tile generators ────────────────────────────────────────────────
def make_themed_tile(slug, label, tmdb_id, media_type):
    """Real backdrop of an iconic film/series + Bebas Neue title overlay."""
    if already(slug):
        print(f"  [skip] {slug}")
        return True

    bg_bytes = None
    source = "?"

    if media_type == "MOVIE":
        bg_bytes = fetch_fanart_movie_bg(tmdb_id)
        if bg_bytes:
            source = "fanart.tv"
        else:
            bg_bytes, source = fetch_tmdb_backdrop("movie", tmdb_id)
    else:
        bg_bytes, source = fetch_tmdb_backdrop("tv", tmdb_id)

    if not bg_bytes:
        print(f"  [err]  {slug}: no backdrop ({source})")
        return False

    try:
        result = apply_text_overlay(bg_bytes, label)
        (OUT_DIR / f"{slug}.jpg").write_bytes(result)
        print(f"  [ok]   {slug:<22} '{label}' ({media_type} {tmdb_id}, {source})")
        return True
    except Exception as e:
        print(f"  [err]  {slug}: overlay failed: {e}")
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


def fetch_franchise(slug, collection_id, label):
    """fanart.tv (bg+logo) → fanart.tv (bg+text) → TMDB (backdrop+text)."""
    if already(slug):
        print(f"  [skip] {slug}")
        return True

    tmdb_data = fetch_tmdb_collection(collection_id)
    fart = fetch_fanart_data(collection_id)

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


# ─── Orchestration ──────────────────────────────────────────────────
def run_parallel(label, items, fn):
    print(f"\n== {label} ({len(items)} items, {WORKERS} workers) ==")
    ok = 0
    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        futs = {pool.submit(fn, *it): it[0] for it in items}
        for fut in as_completed(futs):
            try:
                if fut.result():
                    ok += 1
            except Exception as e:
                print(f"  [err]  {futs[fut]}: {e}")
    return ok


def main():
    print(f"Output: {OUT_DIR.absolute()}   OVERWRITE={OVERWRITE}   WORKERS={WORKERS}")
    print(f"TMDB:   {'configured' if TMDB_KEY else 'NO KEY — themed + fallback art will skip'}")
    print(f"FanArt: {'configured' if FANART_KEY else 'NO KEY — TMDB only'}")
    print(f"Font:   {FONT_PATH if Path(FONT_PATH).exists() else FALLBACK_FONT + ' (Bebas Neue not found)'}")

    print("\n== Branded franchise art (from rrevanth) ==")
    b_ok = sum(copy_branded(s, u, e) for s, (u, e) in BRANDED.items())

    print(f"\n== Franchise fallbacks ({len(TMDB_COLLECTIONS)} via fanart.tv → TMDB) ==")
    if not (TMDB_KEY or FANART_KEY):
        print("  Neither TMDB_API_KEY nor FANART_API_KEY set — skipping.")
        f_ok = 0
    else:
        f_ok = 0
        for slug, cid, lbl in TMDB_COLLECTIONS:
            if fetch_franchise(slug, cid, lbl):
                f_ok += 1
            time.sleep(0.2)

    t_ok = run_parallel("Themed tiles (iconic backdrops + title)", THEMES, make_themed_tile)
    a_ok = run_parallel("Actor tiles (iconic role + actor name)", ACTORS, make_themed_tile)

    print(f"\nDone. Branded {b_ok}/{len(BRANDED)}, "
          f"Franchise {f_ok}/{len(TMDB_COLLECTIONS)}, "
          f"Themed {t_ok}/{len(THEMES)}, "
          f"Actors {a_ok}/{len(ACTORS)}.")


if __name__ == "__main__":
    main()
