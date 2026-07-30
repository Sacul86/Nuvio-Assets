"""
Overlay rrevanth/nuvio-assets community covers onto the all-landscape profile.
Matched folders get the community art (some animated); everything else keeps
the generated title-card cover already in the profile.

Usage: python build_community_map.py <titlecards.json> <repo_clone_dir> <out.json>
"""
import sys
import os
import json

RAW = "https://raw.githubusercontent.com/rrevanth/nuvio-assets/main"

# (collection, folder title) -> "category/slug"   (only confident matches)
MAP = {
    # ---- Genres ----
    ("Genres", "Action"): "genres/action",
    ("Genres", "Comedy"): "genres/comedy",
    ("Genres", "Drama"): "genres/drama",
    ("Genres", "Sci-Fi"): "genres/sci-fi",
    ("Genres", "Horror"): "genres/horror",
    ("Genres", "Crime"): "genres/crime",
    ("Genres", "Fantasy"): "genres/fantasy",
    ("Genres", "Mystery"): "genres/whodunits",
    ("Genres", "Romance"): "genres/romance",
    ("Genres", "Thrillers"): "genres/thriller",
    ("Genres", "Documentaries"): "genres/documentary",
    ("Genres", "Animated"): "genres/animation",
    ("Genres", "Westerns"): "genres/westerns",
    ("Genres", "Anime"): "genres/anime",
    ("Genres", "Spy Thrillers"): "genres/spies",
    ("Genres", "War"): "genres/war-stories",
    ("Genres", "Adventure"): "genres/adventure",
    ("Genres", "Family"): "genres/family-movie-night",
    ("Genres", "History"): "genres/historical-blockbusters",
    ("Genres", "Musicals"): "genres/music",
    # ---- Decades ----
    ("Decades", "2020s"): "decades/2020s",
    ("Decades", "2010s"): "decades/2010s",
    ("Decades", "2000s"): "decades/2000s",
    ("Decades", "1990s"): "decades/1990s",
    ("Decades", "1980s"): "decades/1980s",
    ("Decades", "1970s"): "decades/1970s",
    ("Decades", "1960s"): "decades/1960s",
    # ---- Directors ----
    ("Directors", "Paul Thomas Anderson"): "directors/anderson",
    ("Directors", "John Carpenter"): "directors/carpenter",
    ("Directors", "Brian De Palma"): "directors/depalma",
    ("Directors", "David Fincher"): "directors/fincher",
    ("Directors", "Alfred Hitchcock"): "directors/hitchcock",
    ("Directors", "Stanley Kubrick"): "directors/kubrick",
    ("Directors", "Christopher Nolan"): "directors/nolan",
    ("Directors", "Martin Scorsese"): "directors/scorsese",
    ("Directors", "Steven Spielberg"): "directors/spielberg",
    ("Directors", "Denis Villeneuve"): "directors/villeneuve",
    # ---- Streaming ----
    ("Streaming", "Netflix"): "streaming/netflix",
    ("Streaming", "Prime Video"): "streaming/prime-video",
    ("Streaming", "Disney+"): "streaming/disney",
    ("Streaming", "HBO Max"): "streaming/hbo-max",
    ("Streaming", "Apple TV+"): "streaming/apple-tv",
    ("Streaming", "Paramount+"): "streaming/paramount",
    ("Streaming", "Hulu"): "streaming/hulu",
    ("Streaming", "Shudder"): "streaming/shudder",
    ("Streaming", "Crunchyroll"): "streaming/crunchyroll",
    ("Streaming", "Discovery+"): "streaming/discovery-plus",
    ("Streaming", "JioHotstar"): "streaming/jiohotstar",
    ("Streaming", "SonyLIV"): "streaming/sonyliv",
    ("Streaming", "MGM+"): "studios/mgm",
    ("Streaming", "Criterion Channel"): "studios/criterion",
    # ---- Studios ----
    ("Studios", "Pixar"): "studios/pixar",
    ("Studios", "Disney Animated"): "studios/walt-disney-animation",
    ("Studios", "Studio Ghibli"): "studios/studio-ghibli",
    ("Studios", "DreamWorks"): "studios/dreamworks",
    ("Studios", "Criterion"): "studios/criterion",
    # ---- Film Collections (franchises) ----
    ("Film Collections", "Marvel Cinematic Universe"): "franchises/mcu",
    ("Film Collections", "Harry Potter"): "franchises/wizarding-world",
    ("Film Collections", "Lord of the Rings"): "franchises/lord-of-the-rings",
    ("Film Collections", "Star Wars"): "franchises/star-wars",
    ("Film Collections", "James Bond"): "franchises/007",
    ("Film Collections", "Mission Impossible"): "franchises/mission-impossible",
    ("Film Collections", "Indiana Jones"): "franchises/indiana-jones",
    ("Film Collections", "Jurassic Park"): "franchises/jurassic-world",
    ("Film Collections", "John Wick"): "franchises/john-wick",
    ("Film Collections", "X-Men"): "franchises/x-men",
    ("Film Collections", "Transformers"): "franchises/transformers",
    ("Film Collections", "Hunger Games"): "franchises/hunger-games",
    ("Film Collections", "Pirates of the Caribbean"): "franchises/pirates-caribbean",
    ("Film Collections", "Dune"): "franchises/dune",
    ("Film Collections", "The Godfather"): "franchises/godfather",
    ("Film Collections", "Avatar"): "franchises/avatar",
    ("Film Collections", "DC Universe"): "franchises/dc-universe",
    # ---- TV Collections ----
    ("TV Collections", "Star Wars TV"): "franchises/star-wars",
    ("TV Collections", "Marvel TV"): "franchises/mcu",
    # ---- Themes ----
    ("Themes", "Zombies"): "genres/zombie-orama",
    ("Themes", "Superhero"): "genres/superheroes",
    ("Themes", "Outer Space"): "genres/space-epics",
    ("Themes", "Nature"): "genres/nature",
    ("Themes", "Whodunnit"): "genres/whodunits",
    ("Themes", "Acclaimed Short Films"): "genres/short-films",
    ("Themes", "Serial Killer"): "genres/psychological-terror",
    # ---- Kids ----
    ("Kids", "Family Movies"): "genres/family-movie-night",
    ("Kids", "DreamWorks Animated"): "studios/dreamworks",
    ("Kids", "Animated Series"): "genres/favorite-cartoons",
    # ---- Anime Franchises ----
    ("Anime Franchises", "One Piece"): "anime/one-piece",
}


def assets_for(repo, catslug):
    """Return (cover_url, focus_url|None) picking best cover + optional focus gif."""
    cat, slug = catslug.split("/", 1)
    d = os.path.join(repo, cat, slug)
    if not os.path.isdir(d):
        return None, None
    files = set(os.listdir(d))
    cover = None
    for ext in ("gif", "png", "jpg", "jpeg"):
        f = f"{slug}-landscape.{ext}"
        if f in files:
            cover = f
            break
    if cover is None and f"{slug}.gif" in files:   # e.g. one-piece
        cover = f"{slug}.gif"
    if cover is None:
        return None, None
    focus = None
    bare = f"{slug}.gif"
    if bare in files and bare != cover:
        focus = bare
    base = f"{RAW}/{cat}/{slug}"
    return f"{base}/{cover}", (f"{base}/{focus}" if focus else None)


def main():
    prof, repo, out = sys.argv[1], sys.argv[2], sys.argv[3]
    data = json.load(open(prof))
    n_comm = n_anim = 0
    report = {}
    for coll in data:
        ct = coll["title"]
        for fo in coll["folders"]:
            key = (ct, fo["title"])
            if key not in MAP:
                continue
            cover, focus = assets_for(repo, MAP[key])
            if not cover:
                print(f"  [missing files] {ct}/{fo['title']} -> {MAP[key]}")
                continue
            fo["coverImageUrl"] = cover
            fo["tileShape"] = "LANDSCAPE"
            if focus:
                fo["focusGifUrl"] = focus
                fo["focusGifEnabled"] = True
            if cover.endswith(".gif"):
                n_anim += 1
            n_comm += 1
            report.setdefault(ct, []).append(fo["title"])
    json.dump(data, open(out, "w"), indent=2, ensure_ascii=False)
    print(f"\nCommunity covers applied: {n_comm}  (animated: {n_anim})")
    for ct in report:
        print(f"  {ct} ({len(report[ct])}): {', '.join(report[ct])}")
    print(f"\nWrote {out}")


if __name__ == "__main__":
    main()
