# Personal Nuvio Plugin List — Top 5

A tightly curated set of 5 providers from
[D3adlyRocket/All-in-One-Nuvio](https://github.com/D3adlyRocket/All-in-One-Nuvio):
**English only · movies + TV · no anime · no P2P · every endpoint verified HTTPS.**

## How to use

Add the raw URL of `personal-manifest.json` as a scraper repo in Nuvio:

```
https://raw.githubusercontent.com/sacul86/nuvio-assets/claude/personal-plugin-list-QffUb/personal-manifest.json
```

> The `filename` paths (e.g. `providers/vidsrc.js`) point at provider scripts in
> the original All-in-One-Nuvio repo. This manifest only curates **which**
> providers load. If Nuvio resolves provider files relative to the manifest,
> mirror the matching files from the source repo's `providers/` folder.

## The 5 providers

Chosen for reliability, quality, and source diversity — they pull from different
networks so they back each other up when one is down.

| Provider | Why it's here | Endpoints (all HTTPS) |
|---|---|---|
| **4KHDHub** | Best quality — 4K/HEVC direct links | `4khdhub.dad`, `*.hf.space` |
| **VidSrc** | Most popular/reliable embed network | `cloudnestra.com`, `vsrc.su` |
| **VidLink** | Strong independent alternate | `vidlink.pro` |
| **VidEasy** | Large catalog | `videasy.net`, `player.videasy.net` |
| **VidFast** | Fast modern source, good fallback | `vidfast.to`, `enc-dec.app` |

## HTTPS research

Each provider's actual source script was read to extract its live endpoints and
confirm the protocol. All five above use **HTTPS end-to-end** — no plain HTTP,
no raw IP addresses.

### Notable rejections
- **Cineby** — **disqualified.** Its main backend is
  `http://145.241.158.129:3113` — unencrypted HTTP straight to a raw IP. Fails
  the HTTPS requirement outright.
- **Torrentio** — torrent/P2P; the only category that genuinely exposes your IP
  to your ISP. Excluded.
- **ShowBox / UHDMovies / NetMirror** — heavily obfuscated; their real domains
  couldn't be confirmed as HTTPS from static analysis, so they were left out of
  a *verified*-HTTPS list (not necessarily insecure — just unverified).

## On "VPN required" for streaming

For streaming the VPN concern is ISP privacy, not geo-access. HTTPS already
encrypts *what* you stream (your ISP sees only the domain, not the content).
A VPN would additionally hide the domain — your call per provider. The one thing
that materially leaks your IP is P2P/torrents, which is why Torrentio is out.
All five providers here are direct HTTPS streams: same exposure as browsing any
normal website.

## Want more?

The previous 40-provider list (English, no anime, no VPN, but not all
HTTPS-verified) is in this branch's git history if you ever want to widen the
pool again.
