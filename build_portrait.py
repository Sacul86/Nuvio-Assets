"""
build_portrait.py — portrait (2:3) gold-caps covers for EVERY Nuvio folder.

Sources the right kind of TMDB portrait per collection:
  people (Actors/Directors) -> profile portrait
  franchises (Film/TV/Anime Collections) -> franchise poster
  brands (Streaming/Studios/Networks) -> representative catalogue poster
  lists (Trending/New/Anime) -> top poster
  concepts (Genres/Themes/Decades) -> top-title poster (queries reused)
Then: cover-crop to 1000x1500, punchy grade, bottom scrim, and the folder
name burned in GOLD CAPS bottom-left (same position everywhere).

Usage:
    export TMDB_API_KEY=your_key
    pip install requests pillow
    python build_portrait.py <profile.json>

Re-run safe (existing files skipped). Output: assets/portrait/<slug>.jpg
"""
import os
import re
import sys
import json
import time
from pathlib import Path

import requests
from PIL import Image, ImageDraw, ImageFont, ImageEnhance

from build_covers import JOBS  # concept-folder queries (Genres/Themes/Decades)

API = os.environ.get("TMDB_API_KEY")
if not API:
    sys.exit("Set TMDB_API_KEY.")

BASE = "https://api.themoviedb.org/3"
IMG = "https://image.tmdb.org/t/p/w780"
OUT = Path("assets/portrait")
OUT.mkdir(parents=True, exist_ok=True)

PW, PH = 1000, 1500
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
GOLD, STROKE = (232, 196, 112), (70, 45, 0)
MX, MB = 54, 66

S = requests.Session()
used = set()


def get(path, **params):
    params["api_key"] = API
    try:
        r = S.get(f"{BASE}/{path}", params=params, timeout=20)
        r.raise_for_status()
        return r.json().get("results", [])
    except Exception as e:
        print(f"      api: {e}")
        return []


def first_img(results, key="poster_path"):
    for it in results:
        p = it.get(key) or it.get("poster_path") or it.get("profile_path")
        if p and p not in used:
            used.add(p)
            return p
    return None


# ── resolvers (each returns an unused image path or None) ──────────
def person(name):
    return first_img(get("search/person", query=name), "profile_path")

def collection(name):
    return first_img(get("search/collection", query=name))

def movie(name):
    return first_img(get("search/movie", query=name))

def tv(name):
    return first_img(get("search/tv", query=name))

def multi(name):
    return first_img(get("search/multi", query=name))

def brand(name, mt):
    cos = get("search/company", query=name)
    if cos:
        cid = cos[0]["id"]
        for page in (1, 2):
            p = first_img(get(f"discover/{mt}", with_companies=cid,
                              sort_by="popularity.desc", page=page,
                              **{"vote_count.gte": "50"}))
            if p:
                return p
    return None

def concept(slug):
    _, attempts = JOBS[slug]
    for method, mt, params in attempts:
        for page in (1, 2, 3):
            p = first_img(get(f"{method}/{mt}", page=page, **params))
            if p:
                return p
    return None

def endpoint(path, **params):
    return first_img(get(path, **params))


ANIME_TV = {"with_genres": "16", "with_original_language": "ja", "sort_by": "popularity.desc"}
NEW_MAP = {
    "In Theaters": ("movie/now_playing", {}), "Upcoming Movies": ("movie/upcoming", {}),
    "On The Air": ("tv/on_the_air", {}), "Airing Today": ("tv/airing_today", {}),
    "Airing Shows": ("tv/on_the_air", {}),
}


def resolve(coll, title, slug):
    if coll in ("Actors", "Directors"):
        return person(title)
    if coll == "Film Collections":
        return collection(title) or movie(title)
    if coll == "TV Collections":
        q = title.replace(" Universe", "").replace(" TV", "").strip()
        return tv(q) or multi(q)
    if coll == "Anime Franchises":
        return tv(title) or multi(title)
    if coll == "Studios":
        return brand(title, "movie") or movie(title)
    if coll == "Networks":
        return brand(title, "tv") or tv(title)
    if coll == "Streaming":
        return brand(title, "movie") or brand(title, "tv") or multi(title)
    if coll == "Anime":
        for page in (1, 2, 3, 4):
            p = first_img(get("discover/tv", page=page, **ANIME_TV))
            if p:
                return p
        return None
    if coll == "Trending":
        for ep in ("trending/all/week", "trending/movie/week", "movie/popular", "tv/popular"):
            p = endpoint(ep)
            if p:
                return p
        return None
    if coll == "New & Latest":
        ep, pr = NEW_MAP.get(title, ("movie/now_playing", {}))
        return endpoint(ep, **pr) or endpoint("movie/upcoming")
    if coll == "Kids":
        return collection(title) or multi(title) or first_img(
            get("discover/movie", with_genres="10751", sort_by="popularity.desc",
                **{"vote_count.gte": "200"}))
    if coll in ("Genres", "Themes", "Decades"):
        return concept(slug)
    return None


# ── image treatment ───────────────────────────────────────────────
def cover_crop(im):
    im = im.convert("RGB")
    sw, sh = im.size
    scale = max(PW / sw, PH / sh)
    im = im.resize((int(sw * scale + 1), int(sh * scale + 1)), Image.LANCZOS)
    w, h = im.size
    return im.crop(((w - PW) // 2, 0, (w - PW) // 2 + PW, PH))


def grade(im):
    im = ImageEnhance.Color(im).enhance(1.12)
    im = ImageEnhance.Contrast(im).enhance(1.08)
    im = ImageEnhance.Brightness(im).enhance(0.96)
    grad = Image.new("L", (1, PH))
    for y in range(PH):
        t = y / (PH - 1)
        grad.putpixel((0, y), int(215 * max(0, (t - 0.55) / 0.45) ** 1.5))
    return Image.composite(Image.new("RGB", (PW, PH)), im, grad.resize((PW, PH)))


def fit_size(labels, base=98, floor=48):
    """One font size used for every tile: the largest that fits the longest
    single (unbreakable) word across all labels within the text column."""
    maxw = PW - MX * 2
    words = [w for lb in labels for w in lb.upper().split()]
    size = base
    while size > floor:
        f = ImageFont.truetype(FONT, size)
        d = ImageDraw.Draw(Image.new("RGB", (1, 1)))
        if all(d.textlength(w, font=f) <= maxw for w in words):
            break
        size -= 2
    return size


def title(im, text, size=None):
    """Gold caps, fixed size, wrapped onto multiple lines, bottom-left."""
    d = ImageDraw.Draw(im)
    if size is None:
        size = fit_size([text])
    f = ImageFont.truetype(FONT, size)
    maxw = PW - MX * 2
    # greedy word-wrap (never shrink to fit a phrase)
    lines, cur = [], ""
    for w in text.upper().split():
        trial = (cur + " " + w).strip()
        if d.textlength(trial, font=f) <= maxw or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    asc, desc = f.getmetrics()
    lh = asc + desc
    gap = int(lh * 0.06)
    total = len(lines) * lh + (len(lines) - 1) * gap
    y = PH - MB - total
    for line in lines:
        d.text((MX + 3, y + 3), line, font=f, fill=(0, 0, 0))
        d.text((MX, y), line, font=f, fill=GOLD, stroke_width=2, stroke_fill=STROKE)
        y += lh + gap
    return im


def streaming_tile(src_im):
    """Fit a landscape brand cover onto a portrait canvas, filling the top/
    bottom bands by edge-replicating the art so the logo is never cropped."""
    art = src_im.convert("RGB")
    aw, ah = art.size
    nw = PW
    nh = max(1, round(ah * PW / aw))
    art = art.resize((nw, nh), Image.LANCZOS)
    canvas = Image.new("RGB", (PW, PH))
    top = (PH - nh) // 2
    if top > 0:
        canvas.paste(art.crop((0, 0, PW, 1)).resize((PW, top)), (0, 0))
        bot = PH - top - nh
        if bot > 0:
            canvas.paste(art.crop((0, nh - 1, PW, nh)).resize((PW, bot)), (0, top + nh))
    canvas.paste(art, (0, max(0, top)))
    return canvas


def slug_of(fo):
    m = re.search(r"/covers/[^/]+/([^/]+)\.webp", fo.get("coverImageUrl", "") or "")
    return m.group(1) if m else None


def main():
    profile = sys.argv[1] if len(sys.argv) > 1 else sys.exit("pass profile.json")
    data = json.load(open(profile))
    jobs = []
    for coll in data:
        for fo in coll["folders"]:
            s = slug_of(fo)
            if s:
                jobs.append((coll["title"], fo["title"], s))
    print(f"Building {len(jobs)} portrait covers → {OUT}/\n")
    ok = miss = 0
    for coll, ttl, slug in jobs:
        out = OUT / f"{slug}.jpg"
        if out.exists():
            ok += 1
            continue
        try:
            path = resolve(coll, ttl, slug)
        except Exception as e:
            path = None
            print(f"  [err] {slug}: {e}")
        if not path:
            print(f"  [MISS] {coll}/{ttl} ({slug})")
            miss += 1
            continue
        try:
            raw = S.get(IMG + path, timeout=30)
            raw.raise_for_status()
            tmp = OUT / f".{slug}.src"
            tmp.write_bytes(raw.content)
            im = title(grade(cover_crop(Image.open(tmp))), ttl)
            im.save(out, "JPEG", quality=88)
            tmp.unlink(missing_ok=True)
            ok += 1
            if ok % 25 == 0:
                print(f"  ... {ok} done")
        except Exception as e:
            print(f"  [err] {slug}: {e}")
            miss += 1
        time.sleep(0.12)
    print(f"\nDone. {ok} ready, {miss} missed.")


if __name__ == "__main__":
    main()
