#!/usr/bin/env python3
"""One-off transform for the streaming-removal / genre-restructure request.

Reads the two exported Nuvio configs, applies the requested edits, and writes
the cleaned versions into the repo root.

Edits:
  1. Remove the Streaming collection (collections profile) + all streaming
     catalog definitions (metadata config).
  2. Remove "Adventure" from the Action genre and add a standalone Adventure genre.
  3. Add closely-related TMDB movie sub-genre rows to each genre.
  4. Collapse each movie-based genre down to a single genre-level series row
     (no per-sub-genre series rows; Horror keeps its movie sub-genres but a
     single "New Horror Series" series row).
  5. Remove Studio Ghibli (studios collection folder + catalog definitions).
"""
import json

SRC_PROFILE = "/root/.claude/uploads/6e87b92e-c854-4fd7-b108-9d8c2c61369e/1e87ba4c-nuviocollectionsprofile120260602.json"
SRC_CONFIG = "/root/.claude/uploads/6e87b92e-c854-4fd7-b108-9d8c2c61369e/6b962f4b-aiometadataconfig20260602_1.json"
OUT_PROFILE = "/home/user/Nuvio-Assets/nuvio-collections-profile.json"
OUT_CONFIG = "/home/user/Nuvio-Assets/nuvio-metadata-config.json"

# ---- catalog id maps -------------------------------------------------------
MOVIE_GENRE = {
    "Action": "tmdb.discover.movie.genres.action",
    "Adventure": "tmdb.discover.movie.genres.adventure",
    "Animation": "tmdb.discover.movie.genres.animation",
    "Comedy": "tmdb.discover.movie.genres.comedy",
    "Crime": "tmdb.discover.movie.genres.crime",
    "Documentary": "tmdb.discover.movie.genres.documentary",
    "Drama": "tmdb.discover.movie.genres.drama",
    "Family": "tmdb.discover.movie.genres.family",
    "Fantasy": "tmdb.discover.movie.genres.fantasy",
    "History": "tmdb.discover.movie.genres.history",
    "Horror": "tmdb.discover.movie.genres.horror",
    "Music": "tmdb.discover.movie.genres.music",
    "Mystery": "tmdb.discover.movie.genres.mystery",
    "Romance": "tmdb.discover.movie.genres.romance",
    "Science Fiction": "tmdb.discover.movie.genres.science-fiction",
    "Thriller": "tmdb.discover.movie.genres.thriller",
    "TV Movie": "tmdb.discover.movie.genres.tv-movie",
    "War": "tmdb.discover.movie.genres.war",
    "Western": "tmdb.discover.movie.genres.western",
}
SERIES_GENRE = {
    "Action & Adventure": "tmdb.discover.series.genres.action-adventure",
    "Animation": "tmdb.discover.series.genres.animation",
    "Comedy": "tmdb.discover.series.genres.comedy",
    "Crime": "tmdb.discover.series.genres.crime",
    "Documentary": "tmdb.discover.series.genres.documentary",
    "Drama": "tmdb.discover.series.genres.drama",
    "Family": "tmdb.discover.series.genres.family",
    "Mystery": "tmdb.discover.series.genres.mystery",
    "Sci-Fi & Fantasy": "tmdb.discover.series.genres.sci-fi-fantasy",
    "Western": "tmdb.discover.series.genres.western",
    "War & Politics": "tmdb.discover.series.genres.war-politics",
}

# Horror keeps its curated movie sub-genre catalogs (genre label is "None").
HORROR_MOVIE_SUBS = [
    "tmdb.discover.movie.genres.horror",
    "tmdb.discover.movie.horror.slasher",
    "tmdb.discover.movie.horror.supernatural",
    "tmdb.discover.movie.horror.creature",
    "tmdb.discover.movie.horror.psychological",
    "tmdb.discover.movie.horror.found-footage",
    "tmdb.discover.movie.horror.folk-occult",
    "tmdb.discover.movie.horror.new-movies",
]
HORROR_SERIES = "tmdb.discover.series.horror.new-series"  # single genre-level series row

# Desired genre layout: title -> (ordered movie sub-genre names, single series label or None)
# Horror and the two series-only genres (Talk, Reality) are handled separately.
GENRE_SPEC = [
    ("Action",      ["Action", "Thriller", "War"],            "Action & Adventure"),
    ("Adventure",   ["Adventure", "Fantasy"],                 "Action & Adventure"),  # NEW
    ("Animation",   ["Animation", "Family"],                  "Animation"),
    ("Comedy",      ["Comedy", "Romance"],                    "Comedy"),
    ("Crime",       ["Crime", "Mystery", "Thriller"],         "Crime"),
    ("Documentary", ["Documentary", "History"],               "Documentary"),
    ("Drama",       ["Drama", "Romance"],                     "Drama"),
    ("Family",      ["Family", "Animation"],                  "Family"),
    ("Fantasy",     ["Fantasy", "Science Fiction", "Adventure"], "Sci-Fi & Fantasy"),
    ("History",     ["History", "War", "Documentary"],        "War & Politics"),
    ("Horror",      "__HORROR__",                             None),
    ("Music",       ["Music"],                                None),
    ("Mystery",     ["Mystery", "Crime", "Thriller"],         "Mystery"),
    ("Talk",        "__KEEP__",                               None),
    ("Reality",     "__KEEP__",                               None),
    ("Romance",     ["Romance", "Comedy", "Drama"],           None),
    ("Thriller",    ["Thriller", "Mystery", "Crime"],         None),
    ("TV",          ["TV Movie"],                             None),
    ("Western",     ["Western", "Action"],                    "Western"),
]


def movie_source(catalog_id, genre_label):
    return {
        "type": "movie", "genre": genre_label, "title": None, "sortBy": None,
        "tmdbId": None, "addonId": "aio-metadata", "filters": None, "sortHow": None,
        "provider": "addon", "catalogId": catalog_id, "mediaType": None,
        "traktListId": None, "tmdbSourceType": None,
    }


def series_source(catalog_id, genre_label):
    return {
        "type": "series", "genre": genre_label, "title": None, "sortBy": None,
        "tmdbId": None, "addonId": "aio-metadata", "filters": None, "sortHow": None,
        "provider": "addon", "catalogId": catalog_id, "mediaType": None,
        "traktListId": None, "tmdbSourceType": None,
    }


def catalog_source(typ, catalog_id, genre_label):
    return {"type": typ, "genre": genre_label, "addonId": "aio-metadata", "catalogId": catalog_id}


def build_sources(title, movie_spec, series_label):
    sources, cat_sources = [], []

    def add(typ, cid, label):
        (sources.append(movie_source(cid, label) if typ == "movie" else series_source(cid, label)))
        cat_sources.append(catalog_source(typ, cid, label))

    if movie_spec == "__HORROR__":
        for cid in HORROR_MOVIE_SUBS:
            label = "Horror" if cid.endswith("genres.horror") else "None"
            add("movie", cid, label)
        add("series", HORROR_SERIES, "None")
    else:
        for name in movie_spec:
            add("movie", MOVIE_GENRE[name], name)
        if series_label:
            add("series", SERIES_GENRE[series_label], series_label)
    return sources, cat_sources


def main():
    profile = json.load(open(SRC_PROFILE))
    config = json.load(open(SRC_CONFIG))

    # ---- collections profile ----
    # 1. drop streaming collection
    before = len(profile)
    profile = [c for c in profile if c.get("id") != "collections-streaming"]
    assert len(profile) == before - 1, "streaming collection not removed"

    genres_col = next(c for c in profile if c["id"] == "collections-genres")
    studios_col = next(c for c in profile if c["id"] == "collections-studios")

    # 5. drop Studio Ghibli folder
    n = len(studios_col["folders"])
    studios_col["folders"] = [f for f in studios_col["folders"] if f["id"] != "collections.studios.ghibli"]
    assert len(studios_col["folders"]) == n - 1, "ghibli folder not removed"

    # 2-4. rebuild genre folders
    existing = {f["title"]: f for f in genres_col["folders"]}
    action_meta = existing["Action"]
    cdn_base = action_meta["coverImageUrl"].rsplit("/", 1)[0]  # .../assets

    new_folders = []
    for title, movie_spec, series_label in GENRE_SPEC:
        if title == "Adventure":
            # new folder, clone Action's display metadata, swap the image basename
            folder = json.loads(json.dumps(action_meta))
            folder["id"] = "collections.genres.adventure"
            folder["title"] = "Adventure"
            adv_img = f"{cdn_base}/genre-adventure.jpg"
            folder["focusGifUrl"] = adv_img
            folder["coverImageUrl"] = adv_img
            folder["heroBackdropUrl"] = adv_img
        else:
            folder = existing[title]

        if movie_spec == "__KEEP__":
            new_folders.append(folder)
            continue

        sources, cat_sources = build_sources(title, movie_spec, series_label)
        folder["sources"] = sources
        folder["catalogSources"] = cat_sources
        new_folders.append(folder)

    genres_col["folders"] = new_folders

    # ---- metadata config ----
    cats = config["config"]["catalogs"]
    n0 = len(cats)
    cats = [c for c in cats if ".streaming." not in c.get("id", "")
            and not c.get("id", "").endswith(".studios.ghibli")]
    removed = n0 - len(cats)
    config["config"]["catalogs"] = cats
    config["metadata"]["totalCatalogs"] = len(cats)
    config["metadata"]["enabledCatalogs"] = sum(1 for c in cats if c.get("enabled"))

    # ---- sanity: no dangling references to removed catalogs ----
    blob = json.dumps(profile)
    assert ".streaming." not in blob, "streaming catalog still referenced in profile"
    assert ".studios.ghibli" not in blob, "ghibli catalog still referenced in profile"
    valid_ids = {c.get("id") for c in cats}
    for col in profile:
        for f in col.get("folders", []):
            for s in f.get("sources", []):
                cid = s.get("catalogId")
                if cid and cid.startswith("tmdb.") and cid not in valid_ids:
                    raise SystemExit(f"DANGLING source catalogId in {f['id']}: {cid}")

    json.dump(profile, open(OUT_PROFILE, "w"), indent=2, ensure_ascii=False)
    open(OUT_PROFILE, "a").write("\n")
    json.dump(config, open(OUT_CONFIG, "w"), indent=2, ensure_ascii=False)
    open(OUT_CONFIG, "a").write("\n")

    print(f"removed {removed} catalog defs (streaming + ghibli); catalogs now {len(cats)}")
    print(f"collections: {[c['title'] for c in profile]}")
    print("genre folders:")
    for f in genres_col["folders"]:
        m = [s["catalogId"].split('.')[-1] for s in f["sources"] if s["type"] == "movie"]
        s = [x["catalogId"].split('.')[-1] for x in f["sources"] if x["type"] == "series"]
        print(f"  {f['title']:<12} movies={m} series={s}")


if __name__ == "__main__":
    main()
