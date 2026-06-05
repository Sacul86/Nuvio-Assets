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

## What's included (40 providers)

All entries support English (`en`) content and stream movies/TV — no anime,
no torrent/P2P, no providers known to be geo-/ISP-blocked behind a VPN.

4KHDHub · 4KHDHub-NEW · AllMovieLand · Castle · Cineby · CineMM · CinemaCity ·
CineStream · Dahmermovies · Dahmermovies-TV · DooFlix · GoatAPI · HDHub4u ·
HindMoviez · HDMovie2 · LA.Movie · Lordflix · MovieBox · MovieBlast ·
MoviesDrive · MoviesMod · Movies4u · NetMirror · NoTorrent · Peachify ·
PlayIMDb (Movies) · PlayIMDb (Series) · ShowBox · StreamFlix · TopCartoons · MultiVid ·
UHDMovies · VegaMovies · VidLink · VidEasy · VidSrc · VixSrc · VidFast ·
XPass · ZinkMovies

> Several of these are multi-language (English + Hindi/Tamil/Telugu/etc.). They
> are kept because they serve English content; their other languages don't hurt.

## What was removed (19 providers)

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

### Needs a VPN (1)
- **Torrentio** — torrent/P2P source. With torrents your IP is broadcast to
  every other peer in the swarm and actively logged by copyright monitors, so a
  VPN is genuinely needed to stay private from your ISP. This is the one
  provider here that materially increases your exposure.

## Note on "VPN required" (for streaming = ISP privacy)

For streaming, the VPN concern is keeping your traffic private from your ISP —
not unblocking regions. The distinction that matters:

- **Direct HTTP(S) streaming** — every provider in the kept list (VidSrc,
  ShowBox, UHDMovies, etc.). Your ISP just sees you connecting to a website,
  same as normal browsing; with HTTPS it sees the domain, not what you watch.
- **Torrent / P2P** (Torrentio) — your IP is exposed to other peers and logged.
  This is where a VPN actually matters, so it was removed.

HTTPS already encrypts the *content* of what you stream from the direct
providers; a VPN only adds hiding the *domain* from your ISP. That's your call
per provider — but none of the kept providers expose you the way P2P does.
