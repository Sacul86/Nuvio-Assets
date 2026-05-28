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
import json
import os
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

try:
    import requests
    from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps
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
    ("disaster-new-movies",    "New Disaster Movies",   44912,  "MOVIE"),   # 2012 (Roland Emmerich)
    ("disaster-new-series",    "Disaster Series",       75219,  "TV"),      # 9-1-1 (emergency-disaster series)
    ("disaster-earth",         "Earthquakes & Volcanoes", 277216, "MOVIE"), # San Andreas
    ("disaster-water",         "Tsunamis & Floods",     84892,  "MOVIE"),   # The Impossible
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
    ("comedy-standup",         "Stand-up Specials",     115,    "MOVIE"),   # The Big Lebowski (cult comedy w/ rich TMDB art)
    ("comedy-buddy",           "Buddy Comedy",          4638,   "MOVIE"),   # Hot Fuzz
    ("comedy-sitcom",          "Sitcoms",               2316,   "TV"),      # The Office (US)
    ("comedy-parody",          "Parody & Spoof",        813,    "MOVIE"),   # Airplane!
    ("comedy-horror",          "Comedy Horror",         89247,  "TV"),      # What We Do in the Shadows TV
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
    ("drama-new-series",       "New Drama Series",      76331,  "TV"),      # Succession
    ("drama-period",           "Period Drama",          4348,   "MOVIE"),   # Pride & Prejudice (2005)
    ("drama-biopic",           "Biographical",          424694, "MOVIE"),   # Bohemian Rhapsody
    ("drama-coming-age",       "Coming-of-Age",         391713, "MOVIE"),   # Lady Bird
    ("drama-courtroom",        "Courtroom",             389,    "MOVIE"),   # 12 Angry Men (1957)
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
    ("actor-fpugh",        "Florence Pugh",       530385, "MOVIE"),   # Midsommar (iconic solo lead)
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
    """Return (bytes, source_tag) for the best backdrop on /movie or /tv.

    Tries /{type}/{id}/images first (richer set, ranked client-side). If that
    comes back empty or errors, falls back to /{type}/{id}'s primary
    backdrop_path field — TMDB sometimes exposes a primary backdrop even when
    the /images endpoint returns nothing for that title.
    """
    if not TMDB_KEY:
        return None, "no-tmdb-key"

    # Pass 1: /images
    try:
        r = requests.get(
            f"https://api.themoviedb.org/3/{media_type}/{tmdb_id}/images",
            params={"api_key": TMDB_KEY},
            timeout=20,
        )
        r.raise_for_status()
        path = pick_best_tmdb_backdrop(r.json().get("backdrops", []))
        if path:
            img = requests.get(
                f"https://image.tmdb.org/t/p/original{path}", timeout=30,
            ).content
            return img, "tmdb-images"
    except Exception as e:
        print(f"  [warn] tmdb /images {media_type}/{tmdb_id} failed: {type(e).__name__}")

    # Pass 2: /{type}/{id} primary backdrop_path
    try:
        r = requests.get(
            f"https://api.themoviedb.org/3/{media_type}/{tmdb_id}",
            params={"api_key": TMDB_KEY},
            timeout=20,
        )
        r.raise_for_status()
        path = r.json().get("backdrop_path")
        if path:
            img = requests.get(
                f"https://image.tmdb.org/t/p/original{path}", timeout=30,
            ).content
            return img, "tmdb-primary"
        return None, "tmdb-no-backdrop"
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


# ─── Filter-driven discovery (cover always matches the row's content) ─
FILTER_KEY_MAP = {
    "withGenres":           "with_genres",
    "withoutGenres":        "without_genres",
    "withKeywords":         "with_keywords",
    "withoutKeywords":      "without_keywords",
    "withCompanies":        "with_companies",
    "withCast":             "with_cast",
    "withCrew":             "with_crew",
    "withOriginalLanguage": "with_original_language",
    "voteCountGte":         "vote_count.gte",
    "voteAverageGte":       "vote_average.gte",
}


# Global set of backdrop file_paths already used as a tile cover during this
# workflow run. The picker walks tag-matched candidates in score order and
# takes the first one whose backdrop hasn't been claimed yet, so no two
# rows end up with the same image.
_USED_BACKDROPS = set()
_USED_LOCK = threading.Lock()


def reserve_backdrop(path):
    """Atomically claim `path` for this run. Returns True if newly claimed,
    False if another tile already took it."""
    if not path:
        return False
    with _USED_LOCK:
        if path in _USED_BACKDROPS:
            return False
        _USED_BACKDROPS.add(path)
        return True


def tmdb_discover_top(filters, media_type):
    """Run TMDB Discover with the row's filters, then re-rank the top 20 tag-
    matched results client-side by `vote_average * sqrt(vote_count)`.

    Why this formula rather than picking one TMDB sort:
      - popularity.desc surfaces this week's trending title (The Boys for
        horror TV, The Punisher for MCU).
      - vote_count.desc surfaces long-running ensemble shows but doesn't
        weigh quality (a low-rated show with many votes can win).
      - vote_average.desc surfaces highly-rated indies with a handful of
        votes (an obscure 9.0 short beats Endgame).
      - vote_average * sqrt(vote_count) requires BOTH: a high rating AND
        broad engagement. Empirically returns Stranger Things for horror
        TV and Avengers: Endgame for MCU, which is what 'iconic for this
        tag' should look like.

    Filters out anything below 100 votes and anything missing a backdrop.
    """
    if not TMDB_KEY:
        return None, None
    endpoint = "movie" if media_type == "MOVIE" else "tv"
    # Fetch the 20 highest-vote-count results that match the row's tags, then
    # re-rank in Python. sort_by=vote_count.desc is just the prefetch order;
    # the actual choice is made by the formula below.
    params = {"api_key": TMDB_KEY, "sort_by": "vote_count.desc", "page": 1}
    for k, v in (filters or {}).items():
        if k in FILTER_KEY_MAP:
            params[FILTER_KEY_MAP[k]] = v
    try:
        r = requests.get(
            f"https://api.themoviedb.org/3/discover/{endpoint}",
            params=params, timeout=20,
        )
        r.raise_for_status()
        candidates = [
            res for res in r.json().get("results", [])
            if res.get("backdrop_path") and (res.get("vote_count") or 0) >= 100
        ]
        if not candidates:
            # Loosen the floor for niche categories that don't have many
            # 100+ vote titles (stop-motion shorts, obscure sub-genres).
            candidates = [
                res for res in r.json().get("results", [])
                if res.get("backdrop_path")
            ]
        if not candidates:
            return None, None

        def score(b):
            avg = b.get("vote_average") or 0
            cnt = b.get("vote_count") or 0
            return avg * (cnt ** 0.5)

        # Walk in score order; first one whose backdrop hasn't been claimed
        # by another row wins. Guarantees no duplicate covers across the run.
        for cand in sorted(candidates, key=score, reverse=True):
            path = cand.get("backdrop_path")
            if reserve_backdrop(path):
                return cand.get("id"), path
        return None, None
    except Exception as e:
        print(f"  [warn] discover {media_type} failed: {type(e).__name__}")
        return None, None


def _load_collections_json():
    """Return the parsed v14 (or v13 fallback) collections JSON, or [] on miss."""
    for fname in ("carl-nuvio-themed-collections-v14.json",
                  "carl-nuvio-themed-collections-v13.json"):
        path = Path(fname)
        if path.exists():
            try:
                return json.loads(path.read_text())
            except Exception as e:
                print(f"  [warn] {fname} parse failed ({e})")
                return []
    print("  [warn] no v13/v14 JSON in repo")
    return []


def load_filters_from_v13():
    """Returns {slug: (filters, media_type)} for DISCOVER-mode rows."""
    out = {}
    for col in _load_collections_json():
        for fld in col["folders"]:
            slug = fld["id"].replace("folder-carl-", "")
            for src in fld.get("sources", []):
                if src.get("tmdbSourceType") == "DISCOVER":
                    out[slug] = (src.get("filters", {}), src.get("mediaType", "MOVIE"))
                    break
    return out


def load_franchise_specs():
    """Returns [(slug, label, sources_list)] for every fr-* folder, regardless
    of whether the first source is COLLECTION (Star Wars, Toy Story etc.) or
    DISCOVER (MCU, DC Universe). make_franchise_tile handles both modes."""
    out = []
    for col in _load_collections_json():
        for fld in col["folders"]:
            slug = fld["id"].replace("folder-carl-", "")
            if not slug.startswith("fr-"):
                continue
            sources = fld.get("sources") or []
            if sources:
                out.append((slug, fld["title"], sources))
    return out


SLUG_FILTERS = None  # lazy-populated once


# Slugs where Discover would return crossover/ensemble titles rather than
# the curated iconic role - skip Discover entirely for these.
SKIP_DISCOVER_SLUGS = {"anim-disney"}


def _wants_handpicked(slug):
    # Only actor tiles and the curated 'anim-disney' row keep the hand-picked
    # path. Every other slug goes through TMDB Discover (or COLLECTION mode
    # for franchises) so the cover image is drawn from the row's actual
    # filter results.
    return slug in SKIP_DISCOVER_SLUGS or slug.startswith("actor-")


# ─── Actor headshot tiles ───────────────────────────────────────────
def fetch_actor_profile_url(person_id):
    """Highest-rated TMDB profile image URL for a person, or None."""
    if not TMDB_KEY:
        return None
    try:
        r = requests.get(
            f"https://api.themoviedb.org/3/person/{person_id}/images",
            params={"api_key": TMDB_KEY},
            timeout=20,
        )
        r.raise_for_status()
        profiles = r.json().get("profiles", [])
        if not profiles:
            return None
        best = max(
            profiles,
            key=lambda p: (p.get("vote_count") or 0) * ((p.get("vote_average") or 0) + 1),
        )
        return f"https://image.tmdb.org/t/p/original{best['file_path']}"
    except Exception:
        return None


def composite_actor_headshot(profile_bytes, label):
    """1920x1080 landscape tile: blurred headshot as background, portrait
    centered on top, actor name in Bebas Neue at the bottom."""
    portrait = Image.open(io.BytesIO(profile_bytes)).convert("RGB")

    # Background: cover-fit the same image to landscape, then heavy blur + darken.
    bg = ImageOps.fit(portrait, (TILE_W, TILE_H), Image.LANCZOS)
    bg = bg.filter(ImageFilter.GaussianBlur(radius=70))
    dim = Image.new("RGBA", (TILE_W, TILE_H), (0, 0, 0, 120))
    bg = Image.alpha_composite(bg.convert("RGBA"), dim)

    # Foreground portrait: scale so its height takes ~92% of the tile.
    # If the source isn't a typical portrait shape, clamp width to 70% of the
    # canvas so a square/landscape profile doesn't cover the whole tile.
    pw, ph = portrait.size
    target_h = int(TILE_H * 0.92)
    target_w = int(pw * target_h / ph)
    if target_w > int(TILE_W * 0.70):
        target_w = int(TILE_W * 0.70)
        target_h = int(ph * target_w / pw)
    portrait = portrait.resize((target_w, target_h), Image.LANCZOS)
    px = (TILE_W - target_w) // 2
    py = (TILE_H - target_h) // 2 - 20
    bg.paste(portrait, (px, py))

    # Bottom band gradient + Bebas Neue name.
    overlay = Image.new("RGBA", (TILE_W, TILE_H), (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    for y in range(TILE_H):
        t = max(0.0, (y - TILE_H * 0.70) / (TILE_H * 0.30))
        a = int(230 * (t ** 1.4))
        od.line([(0, y), (TILE_W, y)], fill=(0, 0, 0, a))
    bg = Image.alpha_composite(bg, overlay).convert("RGB")

    draw = ImageDraw.Draw(bg)
    text = label.upper()
    font = fit_font(text, max_width=int(TILE_W * 0.80), max_size=200)
    bbox = draw.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    x = (TILE_W - tw) // 2
    y = TILE_H - th - 60
    draw.text((x, y), text, font=font, fill="white",
              stroke_width=6, stroke_fill="black")

    buf = io.BytesIO()
    bg.save(buf, "JPEG", quality=92)
    return buf.getvalue()


def get_actor_person_id(slug):
    """Pull the TMDB person ID out of the v13/v14 JSON's withCast filter for this slug."""
    spec = SLUG_FILTERS.get(slug) if SLUG_FILTERS else None
    if not spec:
        return None
    filters, _ = spec
    cast = filters.get("withCast")
    if not cast:
        return None
    try:
        return int(str(cast).split(",")[0])
    except (TypeError, ValueError):
        return None


def make_themed_tile(slug, label, tmdb_id, media_type):
    """Pick a representative backdrop and overlay the label.

    For actor tiles and a small set of curated slugs, use the hand-picked
    tmdb_id directly - Discover would return whatever crossover movie they're
    most popular in (Emma Stone -> Amazing Spider-Man), and that's a worse
    cover than the iconic role we picked by hand (Poor Things).

    For everything else, prefer Discover with the row's own DISCOVER filter
    from v13 JSON - that way the cover image is drawn from the same pool of
    titles Nuvio shows when the user clicks the row. Fall back to the
    hand-picked id only if Discover returns nothing.
    """
    if already(slug):
        print(f"  [skip] {slug}")
        return True

    global SLUG_FILTERS
    if SLUG_FILTERS is None:
        SLUG_FILTERS = load_filters_from_v13()

    # Actor tiles get a dedicated path: TMDB profile headshot composited on
    # a blurred copy of the same image, with the actor's name overlaid.
    if slug.startswith("actor-"):
        person_id = get_actor_person_id(slug)
        if person_id:
            profile_url = fetch_actor_profile_url(person_id)
            if profile_url:
                try:
                    profile_bytes = requests.get(profile_url, timeout=30).content
                    result = composite_actor_headshot(profile_bytes, label)
                    (OUT_DIR / f"{slug}.jpg").write_bytes(result)
                    print(f"  [ok]   {slug:<22} '{label}' (TMDB person {person_id})")
                    return True
                except Exception as e:
                    print(f"  [warn] {slug}: headshot composite failed ({e}); falling back to iconic role")
        else:
            print(f"  [warn] {slug}: no TMDB person id in v13 filter; falling back to iconic role")

    bg_bytes = None
    source = "?"

    # Discover path (genre rows). Skipped for actor tiles and curated slugs.
    if not _wants_handpicked(slug):
        spec = SLUG_FILTERS.get(slug)
        if spec:
            filters, mt = spec
            discover_id, discover_backdrop = tmdb_discover_top(filters, mt)
            if discover_id:
                if mt == "MOVIE":
                    bg_bytes = fetch_fanart_movie_bg(discover_id)
                    if bg_bytes:
                        source = f"fanart.tv (discover→{discover_id})"
                if not bg_bytes and discover_backdrop:
                    try:
                        bg_bytes = requests.get(
                            f"https://image.tmdb.org/t/p/original{discover_backdrop}",
                            timeout=30,
                        ).content
                        source = f"discover→{discover_id}"
                    except Exception as e:
                        print(f"  [warn] {slug}: discover backdrop dl failed: {e}")
                if not bg_bytes:
                    bg_bytes, s = fetch_tmdb_backdrop(
                        "movie" if mt == "MOVIE" else "tv", discover_id,
                    )
                    if bg_bytes:
                        source = f"{s} (discover→{discover_id})"

    # Hand-picked path (always for actor/curated, fallback for everyone else).
    if not bg_bytes:
        if media_type == "MOVIE":
            bg_bytes = fetch_fanart_movie_bg(tmdb_id)
            if bg_bytes:
                source = f"fanart.tv (iconic {tmdb_id})"
        if not bg_bytes:
            bg_bytes, s = fetch_tmdb_backdrop(
                "movie" if media_type == "MOVIE" else "tv", tmdb_id,
            )
            if bg_bytes:
                source = f"{s} (iconic {tmdb_id})"

    if not bg_bytes:
        print(f"  [err]  {slug}: no backdrop found")
        return False

    try:
        result = apply_text_overlay(bg_bytes, label)
        (OUT_DIR / f"{slug}.jpg").write_bytes(result)
        print(f"  [ok]   {slug:<22} '{label}' ({source})")
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


def fetch_collection_backdrop(collection_id):
    """For a TMDB collection: prefer the collection's own backdrop_path,
    else the most popular member movie's backdrop that hasn't been claimed
    by another row in this run. Returns bytes or None."""
    coll = fetch_tmdb_collection(collection_id)
    if not coll:
        return None

    # Try collection-level backdrop first (often franchise-branded key art).
    chosen = None
    if reserve_backdrop(coll.get("backdrop_path")):
        chosen = coll.get("backdrop_path")
    else:
        # Walk member movies by popularity, take the first whose backdrop is
        # still free. Means Avengers Collection won't reuse the same movie's
        # backdrop that some other row already took.
        parts = sorted(coll.get("parts") or [], key=lambda p: p.get("popularity") or 0, reverse=True)
        for movie in parts:
            if reserve_backdrop(movie.get("backdrop_path")):
                chosen = movie["backdrop_path"]
                break

    if not chosen:
        return None
    try:
        return requests.get(
            f"https://image.tmdb.org/t/p/original{chosen}", timeout=30,
        ).content
    except Exception:
        return None


def make_franchise_tile(slug, label, sources):
    """Pull a backdrop for a fr-* franchise via the first viable source.

    For COLLECTION sources: use the collection's backdrop (or its top movie's).
    For DISCOVER sources (DC Universe etc.): standard Discover.
    Always apply the Bebas Neue title overlay so the franchise name is on the
    tile - no more rrevanth-style baked-in logos.
    """
    if already(slug):
        print(f"  [skip] {slug}")
        return True

    bg_bytes = None
    source = "?"

    for src in sources:
        kind = src.get("tmdbSourceType")
        mt = src.get("mediaType", "MOVIE")
        if kind == "COLLECTION":
            cid = src.get("tmdbId")
            if cid:
                bg_bytes = fetch_collection_backdrop(cid)
                if bg_bytes:
                    source = f"collection {cid}"
                    break
        elif kind == "DISCOVER":
            filters = src.get("filters", {})
            tid, path = tmdb_discover_top(filters, mt)
            if tid and path:
                try:
                    bg_bytes = requests.get(
                        f"https://image.tmdb.org/t/p/original{path}", timeout=30,
                    ).content
                    source = f"discover→{tid}"
                    break
                except Exception as e:
                    print(f"  [warn] {slug}: discover bg dl failed: {e}")

    if not bg_bytes:
        print(f"  [err]  {slug}: no backdrop found for franchise")
        return False

    try:
        result = apply_text_overlay(bg_bytes, label)
        (OUT_DIR / f"{slug}.jpg").write_bytes(result)
        print(f"  [ok]   {slug:<22} '{label}' ({source})")
        return True
    except Exception as e:
        print(f"  [err]  {slug}: overlay failed: {e}")
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
    print(f"TMDB:   {'configured' if TMDB_KEY else 'NO KEY — themed + franchise art will skip'}")
    print(f"FanArt: {'configured' if FANART_KEY else 'NO KEY — TMDB only'}")
    print(f"Font:   {FONT_PATH if Path(FONT_PATH).exists() else FALLBACK_FONT + ' (Bebas Neue not found)'}")

    # Franchises (fr-*): drive entirely off the v13/v14 JSON, no rrevanth copy.
    franchise_specs = load_franchise_specs()
    print(f"\n== Franchises ({len(franchise_specs)} COLLECTION-mode tiles via TMDB) ==")
    f_ok = 0
    for slug, lbl, srcs in franchise_specs:
        if make_franchise_tile(slug, lbl, srcs):
            f_ok += 1
        time.sleep(0.15)

    t_ok = run_parallel("Themed tiles (Discover-driven backdrops + title)", THEMES, make_themed_tile)
    a_ok = run_parallel("Actor tiles (TMDB headshot)", ACTORS, make_themed_tile)

    print(f"\nDone. Franchise {f_ok}/{len(franchise_specs)}, "
          f"Themed {t_ok}/{len(THEMES)}, "
          f"Actors {a_ok}/{len(ACTORS)}.")


if __name__ == "__main__":
    main()
