#!/usr/bin/env python3
"""Full config transform for the streaming-removal / genre-restructure request.

Starts from the two original exported configs and produces the final cleaned
versions in the repo root:

  1. Remove the Streaming collection + all streaming catalog definitions.
  2. Split Adventure out of Action into its own genre.
  3. Give every movie-based genre a set of curated, keyword-based movie
     subgenre rows (same engine as the Horror subgenres) - each subgenre is a
     self-contained TMDB Discover catalog. Subgenre concepts are unique across
     genres and distinct from the existing Themes row.
  4. Exactly one genre-level series row per genre (Horror collapses its seven
     per-subgenre series rows to a single "New Horror Series" row).
  5. Remove Studio Ghibli (studios folder + catalog definitions).

Keyword IDs come from keywords.json (resolved from TMDB's public site).
"""
import json

SRC_PROFILE = "/root/.claude/uploads/6e87b92e-c854-4fd7-b108-9d8c2c61369e/1e87ba4c-nuviocollectionsprofile120260602.json"
SRC_CONFIG = "/root/.claude/uploads/6e87b92e-c854-4fd7-b108-9d8c2c61369e/6b962f4b-aiometadataconfig20260602_1.json"
KEYWORDS = "/home/user/Nuvio-Assets/keywords.json"
OUT_PROFILE = "/home/user/Nuvio-Assets/nuvio-collections-profile.json"
OUT_CONFIG = "/home/user/Nuvio-Assets/nuvio-metadata-config.json"

GENRE_ID = {
    "Action": 28, "Adventure": 12, "Animation": 16, "Comedy": 35, "Crime": 80,
    "Documentary": 99, "Drama": 18, "Family": 10751, "Fantasy": 14, "History": 36,
    "Horror": 27, "Music": 10402, "Mystery": 9648, "Romance": 10749,
    "Science Fiction": 878, "TV Movie": 10770, "Thriller": 53, "War": 10752,
    "Western": 37,
}
ID_GENRE = {v: k for k, v in GENRE_ID.items()}

MOVIE_GENRE_CAT = {name: f"tmdb.discover.movie.genres.{slug}" for name, slug in {
    "Action": "action", "Adventure": "adventure", "Animation": "animation",
    "Comedy": "comedy", "Crime": "crime", "Documentary": "documentary",
    "Drama": "drama", "Family": "family", "Fantasy": "fantasy", "History": "history",
    "Horror": "horror", "Music": "music", "Mystery": "mystery", "Romance": "romance",
    "Science Fiction": "science-fiction", "Thriller": "thriller", "TV Movie": "tv-movie",
    "War": "war", "Western": "western",
}.items()}

SERIES_GENRE_CAT = {
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

# Horror keeps its existing curated movie subgenres (catalogId suffixes).
HORROR_EXISTING = ["slasher", "supernatural", "creature", "psychological",
                   "found-footage", "folk-occult", "new-movies"]

# --- subgenre taxonomy: slug -> (display name with emoji, with_genres id list) ---
# parent genre folder is given by GENRE_LAYOUT below.
SUBGENRE = {
    # Action
    "heist":              ("💰 Heist",               [28, 80, 53]),
    "superhero":          ("🦸 Superhero",           [28, 878, 12, 14]),
    "car-racing":         ("🏎️ Racing & Cars",       [28, 53]),
    "assassins":          ("🎯 Assassins & Hitmen",  [28, 53, 80]),
    # Adventure
    "swashbuckler-pirates": ("🏴‍☠️ Pirates & Swashbucklers", [12, 28]),
    "survival":           ("🏕️ Survival",            [12, 18, 53]),
    "jungle-lost-world":  ("🌴 Jungle & Lost Worlds", [12, 28]),
    "road-trip":          ("🛣️ Road Trip",           [12, 35, 18]),
    # Animation
    "anime":              ("🇯🇵 Anime",              [16]),
    "stop-motion":        ("🪀 Stop Motion",         [16]),
    "adult-animation":    ("🔞 Adult Animation",     [16, 35]),
    "computer-animation": ("🖥️ Computer Animation",  [16]),
    # Comedy
    "romantic-comedy":    ("💘 Romantic Comedy",     [35, 10749]),
    "parody-spoof":       ("🤡 Parody & Spoof",      [35]),
    "buddy-comedy":       ("👯 Buddy Comedy",        [35, 28]),
    "dark-comedy":        ("🖤 Dark Comedy",         [35, 18]),
    "slapstick":          ("🤸 Slapstick",           [35]),
    # Crime
    "mafia-gangster":     ("🔫 Mafia & Gangster",    [80, 18]),
    "drug-cartel":        ("💊 Drugs & Cartels",     [80, 18, 53]),
    "prison":             ("🔒 Prison",              [80, 18]),
    "detective-pi":       ("🕵️ Detective & PI",      [80, 9648, 53]),
    # Documentary
    "true-crime":         ("🔪 True Crime",          [99, 80]),
    "nature-wildlife":    ("🌿 Nature & Wildlife",   [99]),
    "sports-doc":         ("🏅 Sports",              [99]),
    "history-doc":        ("📜 History",             [99, 36]),
    # Music
    "musical":            ("🎬 Musical",             [10402, 35, 10749]),
    "concert-performance":("🎤 Concert & Live",      [10402, 99]),
    "music-biopic":       ("🎸 Music Biopic",        [10402, 18, 36]),
    "dance":              ("💃 Dance",               [10402, 18]),
    # Drama
    "legal-courtroom":    ("⚖️ Legal & Courtroom",   [18, 53, 80]),
    "biographical":       ("🎩 Biographical",        [18, 36]),
    "political-drama":    ("🏛️ Political",           [18, 53]),
    "family-drama":       ("👨‍👩‍👧 Family Drama",       [18]),
    # Family
    "talking-animals":    ("🐾 Talking Animals",     [10751, 16]),
    "holiday-christmas":  ("🎄 Holiday & Christmas", [10751, 35]),
    "fairy-tale":         ("🧚 Fairy Tale",          [10751, 14]),
    "school-friendship":  ("🎒 School & Friendship", [10751, 18, 35]),
    # Fantasy (sci-fi + fantasy umbrella)
    "cyberpunk":          ("🤖 Cyberpunk",           [878, 53]),
    "dystopian":          ("🌆 Dystopian",           [878, 18]),
    "robots-ai":          ("🦾 Robots & AI",         [878]),
    "mythology":          ("⚡ Mythology",           [14, 12]),
    "steampunk":          ("⚙️ Steampunk",           [878, 14, 12]),
    # History
    "period-drama":       ("👑 Period Drama",        [36, 18]),
    "ancient-world":      ("🏛️ Ancient World",       [36, 12, 28]),
    "war-film":           ("⚔️ War Films",           [36, 10752, 18]),
    "medieval":           ("🏰 Medieval",            [36, 12, 14]),
    # Horror (new ones added to existing curated)
    "body-horror":        ("🫀 Body Horror",         [27, 878]),
    "gothic-horror":      ("🦇 Gothic Horror",       [27, 18]),
    "comedy-horror":      ("😱 Comedy Horror",       [27, 35]),
    # Mystery
    "noir":               ("🌃 Noir & Neo-Noir",     [9648, 80, 53]),
    "whodunit":           ("🔍 Whodunit",            [9648, 80]),
    "conspiracy":         ("🕳️ Conspiracy",          [9648, 53]),
    # Romance
    "historical-romance": ("📜 Historical Romance",  [10749, 36, 18]),
    "forbidden-tragic":   ("💔 Forbidden & Tragic",  [10749, 18]),
    "teen-romance":       ("💕 Teen Romance",        [10749, 35, 18]),
    "lgbtq-romance":      ("🏳️‍🌈 LGBTQ+ Romance",     [10749, 18]),
    "paranormal-romance": ("🌙 Paranormal Romance",  [10749, 14, 27]),
    # Thriller
    "psychological-thriller": ("🧠 Psychological Thriller", [53, 9648, 18]),
    "crime-thriller":     ("🔪 Crime Thriller",      [53, 80]),
    "techno-thriller":    ("💻 Techno-Thriller",     [53, 878]),
    "erotic-thriller":    ("🔥 Erotic Thriller",     [53, 18]),
    # Western
    "spaghetti-western":  ("🌵 Spaghetti Western",   [37]),
    "revisionist-western":("🤠 Revisionist Western", [37, 18]),
    "neo-western":        ("🏜️ Neo-Western",         [37, 18, 80]),
    "outlaws":            ("🐎 Outlaws & Gunslingers", [37, 28]),
}

# genre folder -> (catalogId slug prefix, main genre name, [subgenre slugs], series label)
GENRE_LAYOUT = [
    ("Action",      "action",      "Action",      ["heist", "superhero", "car-racing", "assassins"], "Action & Adventure"),
    ("Adventure",   "adventure",   "Adventure",   ["swashbuckler-pirates", "survival", "jungle-lost-world", "road-trip"], "Action & Adventure"),
    ("Animation",   "animation",   "Animation",   ["anime", "stop-motion", "computer-animation", "adult-animation"], "Animation"),
    ("Comedy",      "comedy",      "Comedy",      ["romantic-comedy", "buddy-comedy", "dark-comedy", "parody-spoof", "slapstick"], "Comedy"),
    ("Crime",       "crime",       "Crime",       ["mafia-gangster", "drug-cartel", "prison", "detective-pi"], "Crime"),
    ("Documentary", "documentary", "Documentary", ["true-crime", "nature-wildlife", "sports-doc", "history-doc"], "Documentary"),
    ("Drama",       "drama",       "Drama",       ["legal-courtroom", "biographical", "political-drama", "family-drama"], "Drama"),
    ("Family",      "family",      "Family",      ["talking-animals", "holiday-christmas", "fairy-tale", "school-friendship"], "Family"),
    ("Fantasy",     "fantasy",     "Fantasy",     ["mythology", "cyberpunk", "dystopian", "robots-ai", "steampunk"], "Sci-Fi & Fantasy"),
    ("History",     "history",     "History",     ["period-drama", "medieval", "ancient-world", "war-film"], "War & Politics"),
    ("Horror",      "horror",      "Horror",      "__HORROR__", "__HORROR_SERIES__"),
    ("Music",       "music",       "Music",       ["musical", "concert-performance", "music-biopic", "dance"], None),
    ("Mystery",     "mystery",     "Mystery",     ["whodunit", "noir", "conspiracy"], "Mystery"),
    ("Talk",        None,          None,          "__KEEP__", None),
    ("Reality",     None,          None,          "__KEEP__", None),
    ("Romance",     "romance",     "Romance",     ["historical-romance", "forbidden-tragic", "teen-romance", "lgbtq-romance", "paranormal-romance"], None),
    ("Thriller",    "thriller",    "Thriller",    ["psychological-thriller", "crime-thriller", "techno-thriller", "erotic-thriller"], None),
    ("TV",          "tv",          "TV Movie",    [], None),
    ("Western",     "western",     "Western",     ["spaghetti-western", "revisionist-western", "neo-western", "outlaws"], None),
]


def src_row(typ, catalog_id, genre_label):
    return {
        "type": typ, "genre": genre_label, "title": None, "sortBy": None,
        "tmdbId": None, "addonId": "aio-metadata", "filters": None, "sortHow": None,
        "provider": "addon", "catalogId": catalog_id, "mediaType": None,
        "traktListId": None, "tmdbSourceType": None,
    }


def cat_src(typ, catalog_id, genre_label):
    return {"type": typ, "genre": genre_label, "addonId": "aio-metadata", "catalogId": catalog_id}


def make_subgenre_catalog(catalog_id, name, genre_ids, keywords):
    """Catalog definition modeled on the existing Horror-subgenre template."""
    is_anime = catalog_id.endswith(".anime")
    params = {
        "sort_by": "popularity.desc",
        "include_adult": False,
        "with_keywords": "|".join(str(k["id"]) for k in keywords),
        "with_genres": "|".join(str(g) for g in genre_ids),
        "vote_count.gte": 20,
        "with_release_type": "4|5|6",
    }
    form = {
        "catalogName": name,
        "discoverSource": "tmdb",
        "sortBy": "popularity.desc",
        "catalogType": "movie",
        "includeAdult": False,
        "releasedOnly": True,
        "includeGenres": [{"id": g, "label": ID_GENRE[g]} for g in genre_ids],
        "voteCountMin": 20,
        "withKeywords": [{"id": k["id"], "label": k["label"]} for k in keywords],
    }
    if not is_anime:
        params["without_keywords"] = "210024"
        form["excludeKeywords"] = [{"id": 210024, "label": "anime"}]
    return {
        "id": catalog_id, "type": "movie", "name": name, "enabled": True,
        "showInHome": False, "source": "tmdb",
        "metadata": {"discover": {"version": 2, "source": "tmdb", "mediaType": "movie",
                                  "params": params, "formState": form}},
    }


def main():
    profile = json.load(open(SRC_PROFILE))
    config = json.load(open(SRC_CONFIG))
    kwmap = json.load(open(KEYWORDS))

    # validate: each subgenre slug is assigned to exactly one genre folder
    layout_slugs = []
    for _, _, _, spec, _ in GENRE_LAYOUT:
        if isinstance(spec, list):
            layout_slugs += spec
    layout_slugs += ["body-horror", "gothic-horror", "comedy-horror"]  # horror adds
    dupe_slugs = {s for s in layout_slugs if layout_slugs.count(s) > 1}
    assert not dupe_slugs, f"subgenre(s) assigned to multiple genres: {dupe_slugs}"

    # validate keyword map: every non-horror-existing subgenre present + no reuse across slugs
    seen_kw = {}
    for slug in SUBGENRE:
        kws = kwmap.get(slug)
        assert kws, f"missing keywords for subgenre: {slug}"
        for k in kws:
            if k["id"] in seen_kw and seen_kw[k["id"]] != slug:
                raise SystemExit(f"DUPLICATE keyword {k['id']} ({k['label']}) in {slug} and {seen_kw[k['id']]}")
            seen_kw[k["id"]] = slug

    # 1. drop streaming collection
    profile = [c for c in profile if c.get("id") != "collections-streaming"]
    genres_col = next(c for c in profile if c["id"] == "collections-genres")
    studios_col = next(c for c in profile if c["id"] == "collections-studios")

    # 5. drop Studio Ghibli folder
    studios_col["folders"] = [f for f in studios_col["folders"]
                              if f["id"] != "collections.studios.ghibli"]

    existing = {f["title"]: f for f in genres_col["folders"]}
    action_meta = existing["Action"]
    cdn_base = action_meta["coverImageUrl"].rsplit("/", 1)[0]

    new_catalogs = []          # subgenre catalog defs to append to config
    new_folders = []

    for title, slug_prefix, main_name, sub_spec, series_label in GENRE_LAYOUT:
        if title == "Adventure":
            folder = json.loads(json.dumps(action_meta))
            folder["id"] = "collections.genres.adventure"
            folder["title"] = "Adventure"
            img = f"{cdn_base}/genre-adventure.jpg"
            folder["focusGifUrl"] = folder["coverImageUrl"] = folder["heroBackdropUrl"] = img
        else:
            folder = existing[title]

        if sub_spec == "__KEEP__":          # Talk / Reality: leave untouched
            new_folders.append(folder)
            continue

        sources, csources = [], []

        def add(typ, cid, label):
            sources.append(src_row(typ, cid, label))
            csources.append(cat_src(typ, cid, label))

        # main genre movie row
        add("movie", MOVIE_GENRE_CAT[main_name], main_name)

        if sub_spec == "__HORROR__":
            for sub in HORROR_EXISTING:
                add("movie", f"tmdb.discover.movie.horror.{sub}", "None")
            for sub in ["body-horror", "gothic-horror", "comedy-horror"]:
                cid = f"tmdb.discover.movie.horror.{sub}"
                name, gids = SUBGENRE[sub]
                new_catalogs.append(make_subgenre_catalog(cid, name, gids, kwmap[sub]))
                add("movie", cid, "None")
        else:
            for sub in sub_spec:
                cid = f"tmdb.discover.movie.{slug_prefix}.{sub}"
                name, gids = SUBGENRE[sub]
                new_catalogs.append(make_subgenre_catalog(cid, name, gids, kwmap[sub]))
                add("movie", cid, "None")

        # single genre-level series row
        if series_label == "__HORROR_SERIES__":
            add("series", "tmdb.discover.series.horror.new-series", "None")
        elif series_label:
            add("series", SERIES_GENRE_CAT[series_label], series_label)

        folder["sources"] = sources
        folder["catalogSources"] = csources
        new_folders.append(folder)

    genres_col["folders"] = new_folders

    # ---- metadata config: remove streaming + ghibli, append new subgenre catalogs ----
    cats = config["config"]["catalogs"]
    cats = [c for c in cats if ".streaming." not in c.get("id", "")
            and not c.get("id", "").endswith(".studios.ghibli")]
    existing_ids = {c["id"] for c in cats}
    for c in new_catalogs:
        if c["id"] not in existing_ids:
            cats.append(c)
            existing_ids.add(c["id"])
    config["config"]["catalogs"] = cats
    config["metadata"]["totalCatalogs"] = len(cats)
    config["metadata"]["enabledCatalogs"] = sum(1 for c in cats if c.get("enabled"))

    # ---- sanity: every source catalogId that is a tmdb.* exists in config ----
    valid = {c["id"] for c in cats}
    for col in profile:
        for f in col.get("folders", []):
            for s in f.get("sources", []):
                cid = s.get("catalogId")
                if cid and cid.startswith("tmdb.") and cid not in valid:
                    raise SystemExit(f"DANGLING source catalogId in {f['id']}: {cid}")
    blob = json.dumps(profile)
    assert ".streaming." not in blob and ".studios.ghibli" not in blob

    json.dump(profile, open(OUT_PROFILE, "w"), indent=2, ensure_ascii=False)
    open(OUT_PROFILE, "a").write("\n")
    json.dump(config, open(OUT_CONFIG, "w"), indent=2, ensure_ascii=False)
    open(OUT_CONFIG, "a").write("\n")

    print(f"new subgenre catalogs: {len(new_catalogs)} | total catalogs: {len(cats)} | enabled: {config['metadata']['enabledCatalogs']}")
    print("genre folders:")
    for f in genres_col["folders"]:
        movies = [s["catalogId"].split('.')[-1] for s in f["sources"] if s["type"] == "movie"]
        series = [s["catalogId"].split('.')[-1] for s in f["sources"] if s["type"] == "series"]
        print(f"  {f['title']:<12} movie rows={movies} series={series}")


if __name__ == "__main__":
    main()
