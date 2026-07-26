"""
build_covers.py — themed landscape covers for Nuvio concept collections.

For each Genres / Themes / Decades folder it:
  1. pulls a matching cinematic backdrop from TMDB,
  2. applies a punchy grade + bottom scrim,
  3. burns the folder name in GOLD CAPS, bottom-left, same position on every tile,
  4. saves assets/covers/<slug>.jpg.

Usage:
    export TMDB_API_KEY=your_key_here
    pip install requests pillow
    python build_covers.py

Re-run safe: existing covers are skipped (delete assets/covers to rebuild).
TMDB attribution required: https://www.themoviedb.org/about/logos-attribution
"""

import os
import sys
import time
from pathlib import Path

try:
    import requests
    from PIL import Image, ImageDraw, ImageFont, ImageEnhance
except ImportError:
    sys.exit("Run: pip install requests pillow")

API_KEY = os.environ.get("TMDB_API_KEY")
if not API_KEY:
    sys.exit("Set TMDB_API_KEY env var (free at themoviedb.org → Settings → API).")

BASE = "https://api.themoviedb.org/3"
IMG = "https://image.tmdb.org/t/p/w1280"
OUT = Path("assets/covers")
OUT.mkdir(parents=True, exist_ok=True)

# ── look ──────────────────────────────────────────────────────────
W, H = 1280, 720
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
GOLD = (232, 196, 112)
STROKE = (70, 45, 0)
MARGIN_X, MARGIN_B = 64, 58

# ── folder → (label, [query attempts]) ────────────────────────────
# each query attempt: (method, media_type, params). first that yields
# an unused backdrop wins. genre IDs: Action28 Adv12 Anim16 Com35
# Crime80 Doc99 Drama18 Family10751 Fantasy14 Hist36 Horror27
# Music10402 Mystery9648 Rom10749 SciFi878 Thriller53 War10752 West37
def disc(mt="movie", **p):
    return ("discover", mt, p)
def srch(q, mt="movie"):
    return ("search", mt, {"query": q})

D = "primary_release_date"
POP = {"sort_by": "popularity.desc", "vote_count.gte": "600"}
ACC = {"sort_by": "vote_average.desc", "vote_count.gte": "800"}

JOBS = {
    # ── Genres ──
    "genres.action":          ("Action",        [disc(with_genres="28", **POP)]),
    "genres.comedy":          ("Comedy",        [disc(with_genres="35", **POP)]),
    "genres.drama":           ("Drama",         [disc(with_genres="18", **POP)]),
    "genres.sci_fi":          ("Sci-Fi",        [disc(with_genres="878", **POP)]),
    "genres.horror":          ("Horror",        [disc(with_genres="27", **POP)]),
    "genres.crime":           ("Crime",         [disc(with_genres="80", **POP)]),
    "genres.fantasy":         ("Fantasy",       [disc(with_genres="14", **POP)]),
    "genres.mystery":         ("Mystery",       [disc(with_genres="9648", **POP)]),
    "genres.romance":         ("Romance",       [disc(with_genres="10749", **POP)]),
    "genres.thrillers":       ("Thrillers",     [disc(with_genres="53", **POP)]),
    "genres.documentaries":   ("Documentaries", [disc(with_genres="99", **POP), disc(with_genres="99", sort_by="popularity.desc")]),
    "genres.animated":        ("Animated",      [disc(with_genres="16", **POP)]),
    "genres.bollywood":       ("Bollywood",     [disc(with_original_language="hi", sort_by="popularity.desc", **{"vote_count.gte": "80"})]),
    "genres.westerns":        ("Westerns",      [disc(with_genres="37", **POP)]),
    "genres.sports":          ("Sports",        [disc(with_keywords="6075", sort_by="popularity.desc"), srch("boxing")]),
    "genres.musicals":        ("Musicals",      [disc(with_genres="10402", **POP), srch("musical")]),
    "genres.k_drama":         ("K-Drama",       [disc("tv", with_original_language="ko", sort_by="popularity.desc", **{"vote_count.gte": "40"})]),
    "genres.anime":           ("Anime",         [disc("tv", with_genres="16", with_original_language="ja", sort_by="popularity.desc")]),
    "genres.spy":             ("Spy Thrillers", [srch("spy"), disc(with_keywords="470", **POP)]),
    "genres.war":             ("War",           [disc(with_genres="10752", **POP)]),
    "genres.adventure":       ("Adventure",     [disc(with_genres="12", **POP)]),
    "genres.family":          ("Family",        [disc(with_genres="10751", **POP)]),
    "genres.history":         ("History",       [disc(with_genres="36", **POP)]),
    "genres.romantic_comedy": ("Romantic Comedy",[disc(with_genres="10749,35", **POP)]),

    # ── Themes ──
    "themed_curated.mindfuck_movies": ("Mindfuck",     [disc(with_genres="53,9648", **POP)]),
    "themed_curated.plot_twists":     ("Plot Twists",  [disc(with_genres="53,9648", sort_by="popularity.desc", **{"vote_count.gte": "600", "page": "2"})]),
    "themed_curated.heist_movies":    ("Heist",        [srch("heist")]),
    "themed_curated.time_travel":     ("Time Travel",  [srch("time travel")]),
    "themed_curated.superhero":       ("Superhero",    [disc(with_keywords="9715", sort_by="popularity.desc"), srch("superhero")]),
    "themed_curated.zombies":         ("Zombies",      [srch("zombie")]),
    "themed_curated.serial_killer":   ("Serial Killer",[srch("serial killer")]),
    "themed_curated.time_loop":       ("Time Loop",    [srch("time loop")]),
    "themed_curated.modern_horror":   ("Modern Horror",[disc(with_genres="27", sort_by="popularity.desc", **{"primary_release_date.gte": "2016-01-01", "vote_count.gte": "400"})]),
    "themed_curated.horror_classics": ("Horror Classics",[disc(with_genres="27", sort_by="popularity.desc", **{"primary_release_date.lte": "1992-12-31", "vote_count.gte": "400"})]),
    "themed_curated.outer_space":     ("Outer Space",  [srch("space"), disc(with_genres="878", **POP)]),
    "themed_curated.true_crime":      ("True Crime",   [srch("true crime", "tv"), disc("tv", with_genres="80,99", sort_by="popularity.desc")]),
    "themed_curated.rotten_tomatoes_100": ("100% Rotten Tomatoes", [disc(sort_by="vote_average.desc", **{"vote_count.gte": "4000"})]),
    "themed_curated.history_war":     ("History & War",[disc(with_genres="10752,36", **POP)]),
    "themed_curated.nature":          ("Nature",       [srch("planet earth", "tv"), srch("nature")]),
    "themed_curated.standup_comedy":  ("Stand-up Comedy",[srch("stand up comedy")]),
    "moods_themes.apocalypse":        ("Apocalypse",   [srch("apocalypse")]),
    "moods_themes.whodunnit":         ("Whodunnit",    [srch("murder mystery"), srch("detective")]),
    "moods_themes.based_on_true_story":("Based on a True Story",[disc(with_keywords="9672", **POP)]),
    "moods_themes.nostalgic_80s_90s": ("Nostalgic 80s & 90s",[disc(sort_by="popularity.desc", **{"primary_release_date.gte": "1980-01-01", "primary_release_date.lte": "1999-12-31", "vote_count.gte": "800"})]),
    "moods_themes.rt_best_80s":       ("RT Best of the 80s",[disc(**{"sort_by": "vote_average.desc", "primary_release_date.gte": "1980-01-01", "primary_release_date.lte": "1989-12-31", "vote_count.gte": "800"})]),
    "moods_themes.rt_best_90s":       ("RT Best of the 90s",[disc(**{"sort_by": "vote_average.desc", "primary_release_date.gte": "1990-01-01", "primary_release_date.lte": "1999-12-31", "vote_count.gte": "800"})]),
    "moods_themes.rt_best_00s":       ("RT Best of the 00s",[disc(**{"sort_by": "vote_average.desc", "primary_release_date.gte": "2000-01-01", "primary_release_date.lte": "2009-12-31", "vote_count.gte": "1500"})]),
    "moods_themes.rt_best_10s":       ("RT Best of the 10s",[disc(**{"sort_by": "vote_average.desc", "primary_release_date.gte": "2010-01-01", "primary_release_date.lte": "2019-12-31", "vote_count.gte": "3000"})]),
    "moods_themes.christmas":         ("Christmas",    [srch("christmas")]),
    "moods_themes.christmas_tv_movies":("Christmas TV Movies",[srch("christmas", "tv")]),
    "moods_themes.thanksgiving":      ("Thanksgiving", [srch("thanksgiving")]),
    "moods_themes.underrated_gems":   ("Underrated Gems",[disc(**{"sort_by": "vote_average.desc", "vote_count.gte": "300", "vote_count.lte": "1200"})]),
    "moods_themes.short_films":       ("Acclaimed Short Films",[srch("short film")]),
    "moods_themes.epics":             ("Epics",        [disc(with_genres="36,12", sort_by="popularity.desc", **{"with_runtime.gte": "150", "vote_count.gte": "600"})]),
    "moods_themes.quick_watches":     ("Quick Watches",[disc(sort_by="popularity.desc", **{"with_runtime.lte": "95", "vote_count.gte": "600"})]),
    "moods_themes.feature_docs":      ("Feature-Length Docs",[disc(with_genres="99", sort_by="popularity.desc", **{"with_runtime.gte": "70"})]),

    # ── Decades ──
    "by_decade.2020s": ("2020s", [disc(sort_by="popularity.desc", **{"primary_release_date.gte": "2020-01-01", "primary_release_date.lte": "2029-12-31", "vote_count.gte": "800"})]),
    "by_decade.2010s": ("2010s", [disc(sort_by="popularity.desc", **{"primary_release_date.gte": "2010-01-01", "primary_release_date.lte": "2019-12-31", "vote_count.gte": "3000"})]),
    "by_decade.2000s": ("2000s", [disc(sort_by="popularity.desc", **{"primary_release_date.gte": "2000-01-01", "primary_release_date.lte": "2009-12-31", "vote_count.gte": "2000"})]),
    "by_decade.1990s": ("1990s", [disc(sort_by="popularity.desc", **{"primary_release_date.gte": "1990-01-01", "primary_release_date.lte": "1999-12-31", "vote_count.gte": "1200"})]),
    "by_decade.1980s": ("1980s", [disc(sort_by="popularity.desc", **{"primary_release_date.gte": "1980-01-01", "primary_release_date.lte": "1989-12-31", "vote_count.gte": "800"})]),
    "by_decade.1970s": ("1970s", [disc(sort_by="popularity.desc", **{"primary_release_date.gte": "1970-01-01", "primary_release_date.lte": "1979-12-31", "vote_count.gte": "500"})]),
    "by_decade.1960s": ("1960s", [disc(sort_by="popularity.desc", **{"primary_release_date.gte": "1960-01-01", "primary_release_date.lte": "1969-12-31", "vote_count.gte": "300"})]),
    "by_decade.1950s_and_before": ("1950s & Before", [disc(sort_by="popularity.desc", **{"primary_release_date.lte": "1959-12-31", "vote_count.gte": "200"})]),
    "era_mixes.90s_action":     ("90s Action",     [disc(with_genres="28", sort_by="popularity.desc", **{"primary_release_date.gte": "1990-01-01", "primary_release_date.lte": "1999-12-31", "vote_count.gte": "400"})]),
    "era_mixes.80s_horror":     ("80s Horror",     [disc(with_genres="27", sort_by="popularity.desc", **{"primary_release_date.gte": "1980-01-01", "primary_release_date.lte": "1989-12-31", "vote_count.gte": "300"})]),
    "era_mixes.90s_scifi":      ("90s Sci-Fi",     [disc(with_genres="878", sort_by="popularity.desc", **{"primary_release_date.gte": "1990-01-01", "primary_release_date.lte": "1999-12-31", "vote_count.gte": "400"})]),
    "era_mixes.80s_scifi":      ("80s Sci-Fi",     [disc(with_genres="878", sort_by="popularity.desc", **{"primary_release_date.gte": "1980-01-01", "primary_release_date.lte": "1989-12-31", "vote_count.gte": "300"})]),
    "era_mixes.90s_comedy":     ("90s Comedy",     [disc(with_genres="35", sort_by="popularity.desc", **{"primary_release_date.gte": "1990-01-01", "primary_release_date.lte": "1999-12-31", "vote_count.gte": "400"})]),
    "era_mixes.70s_crime":      ("70s Crime",      [disc(with_genres="80", sort_by="popularity.desc", **{"primary_release_date.gte": "1970-01-01", "primary_release_date.lte": "1979-12-31", "vote_count.gte": "200"})]),
    "era_mixes.2000s_romcom":   ("2000s Rom-Coms", [disc(with_genres="10749,35", sort_by="popularity.desc", **{"primary_release_date.gte": "2000-01-01", "primary_release_date.lte": "2009-12-31", "vote_count.gte": "300"})]),
    "era_mixes.2010s_animation":("2010s Animation",[disc(with_genres="16", sort_by="popularity.desc", **{"primary_release_date.gte": "2010-01-01", "primary_release_date.lte": "2019-12-31", "vote_count.gte": "600"})]),
}

used = set()


def find_backdrop(attempts):
    for method, mt, params in attempts:
        url = f"{BASE}/{method}/{mt}"
        for page in range(1, 4):
            q = {"api_key": API_KEY, "page": str(page), **params}
            try:
                r = requests.get(url, params=q, timeout=20)
                r.raise_for_status()
            except Exception as e:
                print(f"      api error: {e}")
                break
            for item in r.json().get("results", []):
                bd = item.get("backdrop_path")
                if bd and bd not in used:
                    used.add(bd)
                    return bd
    return None


def grade(im):
    im = im.convert("RGB").resize((W, H), Image.LANCZOS)
    im = ImageEnhance.Color(im).enhance(1.18)
    im = ImageEnhance.Contrast(im).enhance(1.12)
    im = ImageEnhance.Brightness(im).enhance(0.94)
    grad = Image.new("L", (1, H))
    for y in range(H):
        t = y / (H - 1)
        grad.putpixel((0, y), int(205 * max(0, (t - 0.45) / 0.55) ** 1.5))
    grad = grad.resize((W, H))
    return Image.composite(Image.new("RGB", (W, H)), im, grad)


def title(im, text):
    d = ImageDraw.Draw(im)
    text = text.upper()
    size = 132
    while size > 40:
        f = ImageFont.truetype(FONT, size)
        ls = max(2, size * 0.03)
        w = sum(d.textlength(c, font=f) for c in text) + (len(text) - 1) * ls
        if w <= W - MARGIN_X * 2:
            break
        size -= 4
    f = ImageFont.truetype(FONT, size)
    ls = max(2, size * 0.03)
    asc, desc = f.getmetrics()
    y = H - MARGIN_B - (asc + desc)
    cx = MARGIN_X
    for c in text:
        d.text((cx + 3, y + 3), c, font=f, fill=(0, 0, 0))
        d.text((cx, y), c, font=f, fill=GOLD, stroke_width=2, stroke_fill=STROKE)
        cx += d.textlength(c, font=f) + ls
    return im


def main():
    slugs = sorted(JOBS)
    print(f"Building {len(slugs)} covers → {OUT}/\n")
    ok = miss = 0
    for slug in slugs:
        out = OUT / f"{slug}.jpg"
        if out.exists():
            print(f"  [skip] {slug}")
            ok += 1
            continue
        label, attempts = JOBS[slug]
        bd = find_backdrop(attempts)
        if not bd:
            print(f"  [MISS] {slug} — no backdrop")
            miss += 1
            continue
        try:
            raw = requests.get(IMG + bd, timeout=30)
            raw.raise_for_status()
            tmp = OUT / f".{slug}.src"
            tmp.write_bytes(raw.content)
            im = title(grade(Image.open(tmp)), label)
            im.save(out, "JPEG", quality=88)
            tmp.unlink(missing_ok=True)
            print(f"  [ok]   {slug:<34} '{label}'")
            ok += 1
        except Exception as e:
            print(f"  [err]  {slug}: {e}")
            miss += 1
        time.sleep(0.2)
    print(f"\nDone. {ok} ready, {miss} missed.")


if __name__ == "__main__":
    main()
