# Personal Nuvio Plugin List — Top 5

A tightly curated set of 5 providers from
[D3adlyRocket/All-in-One-Nuvio](https://github.com/D3adlyRocket/All-in-One-Nuvio):
**English only · movies + TV · no anime · no P2P · every endpoint verified HTTPS.**

## How to use

Add this raw URL as a plugin repository in Nuvio:

```
https://raw.githubusercontent.com/Sacul86/Nuvio-Assets/refs/heads/plugins/manifest.json
```

> This repo is **self-contained**: `manifest.json` plus the actual provider
> scripts in `providers/`. Nuvio resolves each entry's `filename` (e.g.
> `providers/vidlink.js`) relative to the manifest URL, so the scripts must live
> here — they do.

## The 5 providers

Chosen for reliability, quality, and source diversity — they pull from different
networks so they back each other up when one is down.

| Provider | Why it's here | Endpoints (all HTTPS) |
|---|---|---|
| **4KHDHub** | Best quality — 4K/HEVC direct links | `4khdhub.dad`, `*.hf.space` |
| **XPass** | Reliable TMDB/IMDb-ID direct play | `play.xpass.top` |
| **VidLink** | Strong independent alternate (confirmed working) | `vidlink.pro` |
| **VidEasy** | Large catalog | `videasy.net`, `player.videasy.net` |
| **Peachify** | Fast Cloudflare-Worker multi-source | `peachify.top`, `*.eat-peach.sbs` |

> **Two swaps from the original 5:**
> - **VidSrc → XPass.** VidSrc chains through `cloudnestra.com`, which returns
>   HTTP 403 (Cloudflare block), so it returned no streams.
> - **VidFast → Peachify.** VidFast works but is very slow/unreliable — its
>   resolve→`enc-dec.app` decrypt→fetch chain lags badly on mobile. Peachify is
>   a single Cloudflare-Worker network, verified HTTPS (no plain-HTTP/IP).

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
