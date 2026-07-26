"""
build_portrait_clean.py — like build_portrait, but every cover uses a
TITLE-FREE image so only the gold-caps folder label shows.

Per folder it resolves a representative TMDB title (or person), then picks:
  1. a textless poster  (iso_639_1 == null), else
  2. a textless backdrop (cropped to portrait), else
  3. the default poster as a last resort (logged).
People (Actors/Directors) use their profile portrait (already text-free).

Usage:
    export TMDB_API_KEY=your_key
    python build_portrait_clean.py <profile.json>
Overwrites assets/portrait/<slug>.jpg.
"""
import sys
import time
import json
from pathlib import Path
from PIL import Image

import build_portrait as bp
from build_covers import JOBS

W780 = "https://image.tmdb.org/t/p/w780"
W1280 = "https://image.tmdb.org/t/p/w1280"

used_ids = set()
used_files = set()


def items(path, **p):
    return bp.get(path, **p)


def get_json(path, **params):
    params["api_key"] = bp.API
    r = bp.S.get(f"{bp.BASE}/{path}", params=params, timeout=20)
    r.raise_for_status()
    return r.json()


def pick(results, default_mt):
    for it in results:
        tid = it.get("id")
        mt = it.get("media_type", default_mt)
        if tid and tid not in used_ids and mt in ("movie", "tv"):
            used_ids.add(tid)
            return (mt, tid)
    return None


def person_profile(name):
    for it in items("search/person", query=name):
        p = it.get("profile_path")
        if p and p not in used_files:
            used_files.add(p)
            return ("profile", p)
    return None


def brand(name, mt):
    cos = items("search/company", query=name)
    if cos:
        cid = cos[0]["id"]
        for page in (1, 2):
            pk = pick(items(f"discover/{mt}", with_companies=cid,
                            sort_by="popularity.desc", page=page,
                            **{"vote_count.gte": "50"}), mt)
            if pk:
                return pk
    return None


def concept(slug):
    for method, mt, params in JOBS[slug][1]:
        for page in (1, 2, 3):
            pk = pick(items(f"{method}/{mt}", page=page, **params), mt)
            if pk:
                return pk
    return None


NEW_MAP = bp.NEW_MAP


def resolve(coll, title, slug):
    if coll in ("Actors", "Directors"):
        return person_profile(title)
    if coll == "Film Collections":
        return pick(items("search/movie", query=title), "movie") or pick(items("search/multi", query=title), "movie")
    if coll == "TV Collections":
        q = title.replace(" Universe", "").replace(" TV", "").strip()
        return pick(items("search/tv", query=q), "tv") or pick(items("search/multi", query=q), "tv")
    if coll == "Anime Franchises":
        return pick(items("search/tv", query=title), "tv") or pick(items("search/multi", query=title), "tv")
    if coll == "Studios":
        return brand(title, "movie") or pick(items("search/movie", query=title), "movie")
    if coll == "Networks":
        return brand(title, "tv") or pick(items("search/tv", query=title), "tv")
    if coll == "Streaming":
        return brand(title, "movie") or brand(title, "tv") or pick(items("search/multi", query=title), "movie")
    if coll == "Anime":
        for page in (1, 2, 3, 4):
            pk = pick(items("discover/tv", page=page, **bp.ANIME_TV), "tv")
            if pk:
                return pk
        return None
    if coll == "Trending":
        for ep in ("trending/all/week", "trending/movie/week", "movie/popular", "tv/popular"):
            pk = pick(items(ep), "movie")
            if pk:
                return pk
        return None
    if coll == "New & Latest":
        ep, pr = NEW_MAP.get(title, ("movie/now_playing", {}))
        mt = "tv" if "/tv" in ep or ep.startswith("tv") else "movie"
        return pick(items(ep, **pr), mt) or pick(items("movie/upcoming"), "movie")
    if coll == "Kids":
        return (pick(items("search/movie", query=title), "movie")
                or pick(items("search/multi", query=title), "movie")
                or pick(items("discover/movie", with_genres="10751", sort_by="popularity.desc", **{"vote_count.gte": "200"}), "movie"))
    if coll in ("Genres", "Themes", "Decades"):
        return concept(slug)
    return None


def image_url(res):
    """Return (url, note) for a title-free image, or (None, note)."""
    kind = res[0]
    if kind == "profile":
        return (W780 + res[1], "profile")
    mt, tid = res
    try:
        d = get_json(f"{mt}/{tid}/images")
    except Exception:
        d = {}
    posters = sorted((p for p in d.get("posters", [])
                      if p.get("iso_639_1") is None and p["file_path"] not in used_files),
                     key=lambda x: -x.get("vote_average", 0))
    if posters:
        fp = posters[0]["file_path"]
        used_files.add(fp)
        return (W780 + fp, "textless-poster")
    backs = [b for b in d.get("backdrops", [])
             if b.get("iso_639_1") is None and b["file_path"] not in used_files]
    if not backs:
        backs = [b for b in d.get("backdrops", []) if b["file_path"] not in used_files]
    backs.sort(key=lambda x: -x.get("vote_average", 0))
    if backs:
        fp = backs[0]["file_path"]
        used_files.add(fp)
        return (W1280 + fp, "textless-backdrop")
    # last resort: default poster (may carry text)
    try:
        pp = get_json(f"{mt}/{tid}").get("poster_path")
        if pp:
            return (W780 + pp, "TEXT-fallback")
    except Exception:
        pass
    return (None, "none")


CACHE = Path("assets/.srccache")   # pre-text tiles, for instant re-texting
CACHE.mkdir(parents=True, exist_ok=True)
STREAM_COVER = "https://cdn.xperience-app.com/covers/default/{slug}.webp"


def main():
    profile = sys.argv[1]
    data = json.load(open(profile))
    jobs = [(c["title"], f["title"], bp.slug_of(f))
            for c in data for f in c["folders"] if bp.slug_of(f)]
    size = bp.fit_size([t for _, t, _ in jobs])   # one size for every tile
    print(f"Rebuilding {len(jobs)} portraits @ font {size}\n")
    ok = miss = fallback = 0
    for coll, ttl, slug in jobs:
        try:
            # Streaming: branded logo cover, text already built in -> no gold label
            if coll == "Streaming":
                raw = bp.S.get(STREAM_COVER.format(slug=slug), timeout=30)
                raw.raise_for_status()
                tmp = bp.OUT / f".{slug}.src"
                tmp.write_bytes(raw.content)
                tile = bp.streaming_tile(Image.open(tmp))
                tile.save(CACHE / f"{slug}.jpg", "JPEG", quality=90)
                tile.save(bp.OUT / f"{slug}.jpg", "JPEG", quality=90)
                tmp.unlink(missing_ok=True)
                ok += 1
                continue

            res = resolve(coll, ttl, slug)
            if not res:
                print(f"  [MISS] {coll}/{ttl}")
                miss += 1
                continue
            url, note = image_url(res)
            if not url:
                print(f"  [MISS] {coll}/{ttl} (no image)")
                miss += 1
                continue
            if note == "TEXT-fallback":
                fallback += 1
                print(f"  [text] {coll}/{ttl} — no textless art, kept default poster")
            raw = bp.S.get(url, timeout=30)
            raw.raise_for_status()
            tmp = bp.OUT / f".{slug}.src"
            tmp.write_bytes(raw.content)
            base = bp.grade(bp.cover_crop(Image.open(tmp)))
            base.save(CACHE / f"{slug}.jpg", "JPEG", quality=90)
            bp.title(base, ttl, size).save(bp.OUT / f"{slug}.jpg", "JPEG", quality=88)
            tmp.unlink(missing_ok=True)
            ok += 1
            if ok % 40 == 0:
                print(f"  ... {ok} done")
        except Exception as e:
            print(f"  [err] {slug}: {e}")
            miss += 1
        time.sleep(0.12)
    print(f"\nDone. {ok} ready ({fallback} kept text as last resort), {miss} missed.")


if __name__ == "__main__":
    main()
