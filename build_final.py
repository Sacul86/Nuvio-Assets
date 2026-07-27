"""
build_final.py — highest-quality landscape covers, consistent per collection.

  Networks / Studios / Streaming -> the service's own branded artwork
                                     (logo, no gold label).
  Genres / Themes / Decades       -> a hand-picked ICONIC title per folder,
                                     so each row is unmistakably on-theme.
  Franchises / people / lists     -> representative title-free still (as before).
Everything non-brand gets the wrapped gold-caps label at one fixed size.

Usage:
    export TMDB_API_KEY=your_key
    python build_final.py <profile.json>
"""
import sys
import time
import json
from pathlib import Path
from PIL import Image

import build_portrait as bp
import build_portrait_clean as c
import build_landscape as L

BRAND = {"Networks", "Studios", "Streaming"}
BRAND_COVER = "https://cdn.xperience-app.com/covers/default/{slug}.webp"


# ── curated iconic picks: slug -> (media_type, search title, year) ──
def M(q, y=None): return ("movie", q, y)
def T(q, y=None): return ("tv", q, y)

CURATED = {
    # Genres
    "genres.action": M("Mad Max Fury Road", 2015),
    "genres.comedy": M("The Hangover", 2009),
    "genres.drama": M("Forrest Gump", 1994),
    "genres.sci_fi": M("Blade Runner 2049", 2017),
    "genres.horror": M("The Conjuring", 2013),
    "genres.crime": M("Goodfellas", 1990),
    "genres.fantasy": M("The Lord of the Rings The Fellowship of the Ring", 2001),
    "genres.mystery": M("Knives Out", 2019),
    "genres.romance": M("Titanic", 1997),
    "genres.thrillers": M("Se7en", 1995),
    "genres.documentaries": T("Planet Earth II", 2016),
    "genres.animated": M("Spider-Man Into the Spider-Verse", 2018),
    "genres.bollywood": M("RRR", 2022),
    "genres.westerns": M("Django Unchained", 2012),
    "genres.sports": M("Creed", 2015),
    "genres.musicals": M("La La Land", 2016),
    "genres.k_drama": T("Squid Game", 2021),
    "genres.anime": M("Demon Slayer Mugen Train", 2020),
    "genres.spy": M("Skyfall", 2012),
    "genres.war": M("1917", 2019),
    "genres.adventure": M("Jurassic Park", 1993),
    "genres.family": M("Paddington 2", 2017),
    "genres.history": M("Gladiator", 2000),
    "genres.romantic_comedy": M("Crazy Rich Asians", 2018),
    # Themes
    "themed_curated.mindfuck_movies": M("Inception", 2010),
    "themed_curated.plot_twists": M("Fight Club", 1999),
    "themed_curated.heist_movies": M("Heat", 1995),
    "themed_curated.time_travel": M("Looper", 2012),
    "themed_curated.superhero": M("The Avengers", 2012),
    "themed_curated.zombies": M("Train to Busan", 2016),
    "themed_curated.serial_killer": M("Zodiac", 2007),
    "themed_curated.time_loop": M("Edge of Tomorrow", 2014),
    "themed_curated.modern_horror": M("Hereditary", 2018),
    "themed_curated.horror_classics": M("The Exorcist", 1973),
    "themed_curated.outer_space": M("Gravity", 2013),
    "themed_curated.true_crime": T("Making a Murderer", 2015),
    "themed_curated.history_war": M("Saving Private Ryan", 1998),
    "themed_curated.nature": T("Our Planet", 2019),
    "moods_themes.apocalypse": M("Children of Men", 2006),
    "moods_themes.whodunnit": M("Murder on the Orient Express", 2017),
    "moods_themes.based_on_true_story": M("The Social Network", 2010),
    "moods_themes.nostalgic_80s_90s": M("The Goonies", 1985),
    "moods_themes.rt_best_80s": M("Raiders of the Lost Ark", 1981),
    "moods_themes.rt_best_90s": M("Schindler's List", 1993),
    "moods_themes.rt_best_00s": M("The Lord of the Rings The Return of the King", 2003),
    "moods_themes.rt_best_10s": M("Parasite", 2019),
    "moods_themes.christmas": M("Elf", 2003),
    "moods_themes.thanksgiving": M("Planes, Trains and Automobiles", 1987),
    "moods_themes.epics": M("Lawrence of Arabia", 1962),
    "moods_themes.feature_docs": M("Free Solo", 2018),
    # Decades
    "by_decade.2020s": M("Dune", 2021),
    "by_decade.2010s": M("Interstellar", 2014),
    "by_decade.2000s": M("The Dark Knight", 2008),
    "by_decade.1990s": M("Pulp Fiction", 1994),
    "by_decade.1980s": M("Back to the Future", 1985),
    "by_decade.1970s": M("Star Wars", 1977),
    "by_decade.1960s": M("2001 A Space Odyssey", 1968),
    "by_decade.1950s_and_before": M("Casablanca", 1942),
    "era_mixes.90s_action": M("Terminator 2 Judgment Day", 1991),
    "era_mixes.80s_horror": M("The Shining", 1980),
    "era_mixes.90s_scifi": M("The Matrix", 1999),
    "era_mixes.80s_scifi": M("Blade Runner", 1982),
    "era_mixes.90s_comedy": M("Home Alone", 1990),
    "era_mixes.70s_crime": M("Taxi Driver", 1976),
    "era_mixes.2000s_romcom": M("Love Actually", 2003),
    "era_mixes.2010s_animation": M("Inside Out", 2015),
}


def curated_pick(mt, q, yr):
    p = {"query": q}
    if yr and mt == "movie":
        p["primary_release_year"] = str(yr)
    if yr and mt == "tv":
        p["first_air_date_year"] = str(yr)
    return c.pick(c.items(f"search/{mt}", **p), mt) or c.pick(c.items(f"search/{mt}", query=q), mt)


def brand_tile(im):
    """Contain a ~16:9 brand cover onto 1280x720, edge-filling any slim bands
    so the logo is never cropped."""
    art = im.convert("RGB")
    aw, ah = art.size
    s = min(L.W / aw, L.H / ah)
    nw, nh = max(1, round(aw * s)), max(1, round(ah * s))
    art = art.resize((nw, nh), Image.LANCZOS)
    canvas = Image.new("RGB", (L.W, L.H))
    ox, oy = (L.W - nw) // 2, (L.H - nh) // 2
    if oy > 0:
        canvas.paste(art.crop((0, 0, nw, 1)).resize((nw, oy)), (ox, 0))
        canvas.paste(art.crop((0, nh - 1, nw, nh)).resize((nw, L.H - oy - nh)), (ox, oy + nh))
    if ox > 0:
        canvas.paste(art.crop((0, 0, 1, nh)).resize((ox, nh)), (0, oy))
        canvas.paste(art.crop((nw - 1, 0, nw, nh)).resize((L.W - ox - nw, nh)), (ox + nw, oy))
    canvas.paste(art, (ox, oy))
    return canvas


def main():
    data = json.load(open(sys.argv[1]))
    jobs = [(cc["title"], f["title"], bp.slug_of(f))
            for cc in data for f in cc["folders"] if bp.slug_of(f)]
    size = L.fit_size([t for _, t, _ in jobs])
    print(f"Building {len(jobs)} covers @ font {size}\n")
    ok = miss = 0
    for coll, ttl, slug in jobs:
        try:
            if coll in BRAND:
                base = brand_tile(L.dl(BRAND_COVER.format(slug=slug)))
                base.save(L.CACHE / f"{slug}.jpg", "JPEG", quality=92)
                base.save(L.OUT / f"{slug}.jpg", "JPEG", quality=92)   # no label
                ok += 1
                continue

            if slug in CURATED:
                res = curated_pick(*CURATED[slug])
            else:
                res = c.resolve(coll, ttl, slug)
            if not res:
                print(f"  [MISS] {coll}/{ttl}")
                miss += 1
                continue
            kind, src = L.backdrop(res)
            if src is None:
                print(f"  [MISS] {coll}/{ttl} (no image)")
                miss += 1
                continue
            base = L.person_tile(src) if kind == "person" else L.grade(L.cover_crop(src))
            base.save(L.CACHE / f"{slug}.jpg", "JPEG", quality=90)
            L.title(base, ttl, size).save(L.OUT / f"{slug}.jpg", "JPEG", quality=88)
            ok += 1
            if ok % 40 == 0:
                print(f"  ... {ok} done")
        except Exception as e:
            print(f"  [err] {slug}: {e}")
            miss += 1
        time.sleep(0.12)
    print(f"\nDone. {ok} ready, {miss} missed.")


if __name__ == "__main__":
    main()
