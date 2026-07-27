"""
build_titlecards.py — landscape title cards for the concept collections:
a curated cinematic still + the collection NAME rendered cleanly on it, so
each tile both looks good and says what it is. Brands and franchises are
left as their landscape logo / titled art.

Writes assets/landscape/<slug>.jpg.  Usage: python build_titlecards.py <profile.json>
"""
import sys
import time
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageEnhance

import build_portrait as bp
import build_portrait_clean as c
import build_landscape as L
import build_final as F

SKIP = {"Networks", "Studios", "Streaming",
        "Film Collections", "TV Collections", "Anime Franchises"}
PEOPLE = {"Actors", "Directors"}
LIST = {"Anime", "Trending", "New & Latest", "Kids"}
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
GOLD = (230, 196, 110)

# curated representative titles for the list rows (iconic, appropriate)
LIST_CUR = {
    "Top Rated": ("tv", "Fullmetal Alchemist Brotherhood", 2009),
    "Latest Release": ("tv", "Jujutsu Kaisen", 2020),
    "Trending": ("tv", "Demon Slayer Kimetsu no Yaiba", 2019),
    "Most Popular": ("tv", "Attack on Titan", 2013),
    "Upcoming": ("tv", "Chainsaw Man", 2022),
    "Airing Now": ("tv", "One Piece", 1999),
    "Studio Ghibli": ("movie", "Spirited Away", 2001),
    "Crunchyroll Top 50": ("tv", "My Hero Academia", 2016),
    "Hidive": ("tv", "Spy x Family", 2022),
    "Family Movies": ("movie", "Paddington 2", 2017),
    "Family Series": ("tv", "Bluey", 2018),
    "Disney Kids": ("movie", "Encanto", 2021),
    "Animated Series": ("tv", "Avatar The Last Airbender", 2005),
    "Trending Kids Movies": ("movie", "Inside Out 2", 2024),
    "Trending Kids Series": ("tv", "Gravity Falls", 2012),
    "Top Kids Movies": ("movie", "The Lion King", 1994),
    "Nickelodeon": ("tv", "SpongeBob SquarePants", 1999),
    "Nick Jr": ("tv", "PAW Patrol", 2013),
    "DreamWorks Animated": ("movie", "Madagascar", 2005),
    "Halloween for Kids": ("movie", "Hotel Transylvania", 2012),
    "Animated Christmas": ("movie", "Klaus", 2019),
    "For You (Top 100 Today)": ("movie", "Deadpool & Wolverine", 2024),
    "Popular": ("movie", "Barbie", 2023),
    "Trakt Trending": ("tv", "Wednesday", 2022),
    "Trakt Popular": ("tv", "Stranger Things", 2016),
    "Trakt Anticipated": ("movie", "Avatar The Way of Water", 2022),
    "IMDb Top 100": ("movie", "The Shawshank Redemption", 1994),
    "Most Popular (Top 20)": ("movie", "Oppenheimer", 2023),
    "In Theaters": ("movie", "Dune Part Two", 2024),
    "Upcoming Movies": ("movie", "Superman", 2025),
    "On The Air": ("tv", "House of the Dragon", 2022),
    "Airing Today": ("tv", "The Last of Us", 2023),
    "Digital Releases": ("movie", "Wicked", 2024),
    "Latest Releases": ("movie", "Gladiator II", 2024),
    "Blu-ray Releases": ("movie", "Interstellar", 2014),
    "Airing Shows": ("tv", "Severance", 2022),
    "NYT Best of 2025": ("movie", "Anora", 2024),
}
FRANCHISE_KIDS = {"Toy Story", "Shrek", "Despicable Me", "Ice Age", "Kung Fu Panda",
                  "How to Train Your Dragon", "Finding Nemo", "The Incredibles"}


def cur_search(mt, q, yr):
    p = {"query": q}
    if yr and mt == "movie":
        p["primary_release_year"] = str(yr)
    if yr and mt == "tv":
        p["first_air_date_year"] = str(yr)
    r = c.items(f"search/{mt}", **p) or c.items(f"search/{mt}", query=q)
    return (mt, r[0]["id"]) if r else None


def resolve(coll, ttl, slug):
    if coll in PEOPLE:
        return c.person_profile(ttl)
    if slug in F.CURATED:
        return F.curated_pick(*F.CURATED[slug])
    if coll in LIST and ttl in LIST_CUR and ttl not in FRANCHISE_KIDS:
        return cur_search(*LIST_CUR[ttl])
    return c.resolve(coll, ttl, slug)


def titlecard(base, text, size):
    W, H = L.W, L.H
    im = ImageEnhance.Contrast(base.convert("RGB")).enhance(1.04)
    grad = Image.new("L", (W, H), 0)
    gd = grad.load()
    for y in range(H):
        row = int(215 * max((H - y) / H * 0.5 - 0.1, 0))
        for x in range(W):
            gd[x, y] = min(255, row + int(150 * max((W - x) / W - 0.45, 0)))
    im = Image.composite(Image.new("RGB", (W, H)), im, grad)
    d = ImageDraw.Draw(im)
    text = text.upper()
    f = ImageFont.truetype(FONT, size)
    maxw = W - 140
    lines, cur = [], ""
    for w in text.split():
        t = (cur + " " + w).strip()
        if d.textlength(t, font=f) <= maxw or not cur:
            cur = t
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    asc, desc = f.getmetrics()
    lh = asc + desc
    total = len(lines) * lh
    x = 70
    y0 = H - 84 - total
    d.rectangle([x, y0 - 26, x + 92, y0 - 16], fill=GOLD)   # accent bar
    y = y0
    for ln in lines:
        d.text((x + 2, y + 3), ln, font=f, fill=(0, 0, 0))
        d.text((x, y), ln, font=f, fill=(255, 255, 255))
        y += lh
    return im


def main():
    data = json.load(open(sys.argv[1]))
    jobs = [(cc["title"], f["title"], bp.slug_of(f))
            for cc in data for f in cc["folders"]
            if cc["title"] not in SKIP and bp.slug_of(f)]
    size = L.fit_size([t for _, t, _ in jobs], base=104)
    print(f"Building {len(jobs)} title cards @ font {size}\n")
    ok = miss = 0
    for coll, ttl, slug in jobs:
        try:
            res = resolve(coll, ttl, slug)
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
            titlecard(base, ttl, size).save(L.OUT / f"{slug}.jpg", "JPEG", quality=89)
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
