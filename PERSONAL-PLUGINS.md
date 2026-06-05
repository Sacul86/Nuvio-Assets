# Personal Nuvio Plugin List

A trimmed fork of [D3adlyRocket/All-in-One-Nuvio](https://github.com/D3adlyRocket/All-in-One-Nuvio),
filtered to **English content only**, **no anime**, and **no VPN-required providers**.

## How to use

Add the raw URL of `personal-manifest.json` as a scraper repo in Nuvio:

```
https://raw.githubusercontent.com/sacul86/nuvio-assets/claude/personal-plugin-list-QffUb/personal-manifest.json
```

> Note: the `filename` paths (e.g. `providers/vidsrc.js`) point at provider
> scripts that live in the original All-in-One-Nuvio repo. This manifest only
> curates **which** providers load; it does not host the scripts. If Nuvio
> resolves provider files relative to the manifest, mirror the `providers/`
> folder from the source repo alongside this manifest (or keep using the
> original repo's manifest and just disable the entries listed below).

## What's included (39 providers)

All entries support English (`en`) content and stream movies/TV — no anime,
no torrent/P2P, no providers known to be geo-/ISP-blocked behind a VPN.

4KHDHub · 4KHDHub-NEW · AllMovieLand · Castle · Cineby · CineMM · CinemaCity ·
CineStream · Dahmermovies · Dahmermovies-TV · DooFlix · GoatAPI · HDHub4u ·
HindMoviez · HDMovie2 · LA.Movie · Lordflix · MovieBox · MovieBlast ·
MoviesDrive · MoviesMod · Movies4u · NetMirror · NoTorrent · Peachify ·
PlayIMDb (Movies) · PlayIMDb (Series) · StreamFlix · TopCartoons · MultiVid ·
UHDMovies · VegaMovies · VidLink · VidEasy · VidSrc · VixSrc · VidFast ·
XPass · ZinkMovies

> Several of these are multi-language (English + Hindi/Tamil/Telugu/etc.). They
> are kept because they serve English content; their other languages don't hurt.

## What was removed (20 providers)

### Anime (10)
AllAnime · All-Wish · AnimeKai · AnikotoTV · AnimePahe · AnimeSalt ·
Animetsu · AnimeWorld · Anime-Sama · HiAnime

### Not English (6)
- **Isaidub** — Tamil only
- **OnlyKDrama** — Korean only
- **Kisskh** — Korean / Chinese / Japanese / Thai (no English)
- **OneTouchTV** — Asian Drama & Anime (Korean/Japanese/Chinese)
- **Nakios** — "Mainly French"
- **Purstream** — French (VF / VOSTFR)

> Borderline French-focused providers **Movix VF** and **ToFlix** were also
> dropped (both are French-dub-oriented even though they list English). Say the
> word and I'll add them back.

### Needs a VPN (2)
- **Torrentio** — torrent/P2P source; a VPN is strongly advisable for these
- **ShowBox** — its FebBox streaming backend is region-locked

## Note on "VPN required"

The source manifest has **no VPN field**, so this can't be filtered
mechanically. VPN need comes from a host being geo-blocked or ISP-blocked in
your region (it has nothing to do with HTTP vs HTTPS — those only encrypt the
connection). Only the two clear-cut cases above were removed. Some Indian
download sites (UHDMovies, HDHub4u, MoviesMod, VegaMovies, MoviesDrive, etc.)
are ISP-blocked **inside India** but work fine elsewhere, so they were kept —
if you're in a region where they're blocked, disable them.
