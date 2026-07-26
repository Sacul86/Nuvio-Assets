"""
build_landscape.py — 16:9 landscape gold-caps covers for EVERY folder.

Sources per collection (reusing build_portrait_clean resolvers):
  Streaming  -> native landscape brand cover (branding built in, no label)
  People     -> headshot on a blurred landscape backdrop (heads never cropped)
  everything -> a TITLE-FREE landscape backdrop from the representative title
Then: punchy grade, bottom scrim, folder name in GOLD CAPS bottom-left,
one fixed size, wrapped onto multiple lines when long.

Usage:
    export TMDB_API_KEY=your_key
    python build_landscape.py <profile.json>
Output: assets/landscape/<slug>.jpg  (+ pre-text cache in assets/.lscache)
"""
import sys
import time
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageEnhance, ImageFilter

import build_portrait as bp
import build_portrait_clean as c

W, H = 1280, 720
FONT, GOLD, STROKE = bp.FONT, bp.GOLD, bp.STROKE
MX, MB = 64, 52
W1280 = "https://image.tmdb.org/t/p/w1280"
OUT = Path("assets/landscape")
OUT.mkdir(parents=True, exist_ok=True)
CACHE = Path("assets/.lscache")
CACHE.mkdir(parents=True, exist_ok=True)
STREAM_COVER = "https://cdn.xperience-app.com/covers/default/{slug}.webp"


def dl(url):
    r = bp.S.get(url, timeout=30)
    r.raise_for_status()
    tmp = OUT / ".dl.tmp"
    tmp.write_bytes(r.content)
    im = Image.open(tmp).convert("RGB")
    tmp.unlink(missing_ok=True)
    return im


def cover_crop(im, w=W, h=H):
    im = im.convert("RGB")
    sw, sh = im.size
    s = max(w / sw, h / sh)
    im = im.resize((int(sw * s + 1), int(sh * s + 1)), Image.LANCZOS)
    iw, ih = im.size
    return im.crop(((iw - w) // 2, (ih - h) // 2, (iw - w) // 2 + w, (ih - h) // 2 + h))


def grade(im):
    im = ImageEnhance.Color(im).enhance(1.15)
    im = ImageEnhance.Contrast(im).enhance(1.10)
    im = ImageEnhance.Brightness(im).enhance(0.94)
    grad = Image.new("L", (1, H))
    for y in range(H):
        t = y / (H - 1)
        grad.putpixel((0, y), int(205 * max(0, (t - 0.5) / 0.5) ** 1.5))
    return Image.composite(Image.new("RGB", (W, H)), im, grad.resize((W, H)))


def person_tile(src):
    """Headshot anchored right on a blurred fill of itself; name goes bottom-left."""
    bg = cover_crop(src).filter(ImageFilter.GaussianBlur(30))
    bg = ImageEnhance.Brightness(bg).enhance(0.5)
    fh = int(H * 0.98)
    fw = max(1, int(src.width * fh / src.height))
    fg = src.resize((fw, fh), Image.LANCZOS)
    # soft left edge so the portrait melts into the blurred bg
    mask = Image.new("L", (fw, fh), 255)
    md = ImageDraw.Draw(mask)
    for x in range(min(fw, 220)):
        md.line([(x, 0), (x, fh)], fill=int(255 * (x / 220)))
    bg.paste(fg, (W - fw - 40, (H - fh) // 2), mask)
    return bg


def fit_size(labels, base=96, floor=44):
    maxw = W - MX * 2
    words = [w for lb in labels for w in lb.upper().split()]
    d = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    size = base
    while size > floor:
        f = ImageFont.truetype(FONT, size)
        if all(d.textlength(w, font=f) <= maxw for w in words):
            break
        size -= 2
    return size


def title(im, text, size):
    d = ImageDraw.Draw(im)
    f = ImageFont.truetype(FONT, size)
    maxw = W - MX * 2
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
    y = H - MB - (len(lines) * lh + (len(lines) - 1) * gap)
    for line in lines:
        d.text((MX + 3, y + 3), line, font=f, fill=(0, 0, 0))
        d.text((MX, y), line, font=f, fill=GOLD, stroke_width=2, stroke_fill=STROKE)
        y += lh + gap
    return im


def backdrop(res):
    """Return (kind, image) — a landscape source with no baked-in title."""
    if res[0] == "profile":
        return ("person", dl(bp.IMG + res[1]))
    mt, tid = res
    try:
        d = c.get_json(f"{mt}/{tid}/images")
    except Exception:
        d = {}
    bs = [b for b in d.get("backdrops", [])
          if b.get("iso_639_1") is None and b["file_path"] not in c.used_files]
    if not bs:
        bs = [b for b in d.get("backdrops", []) if b["file_path"] not in c.used_files]
    bs.sort(key=lambda x: -x.get("vote_average", 0))
    if bs:
        fp = bs[0]["file_path"]
        c.used_files.add(fp)
        return ("backdrop", dl(W1280 + fp))
    # last resort: a poster, cover-cropped to landscape
    ps = sorted((p for p in d.get("posters", []) if p["file_path"] not in c.used_files),
                key=lambda x: -x.get("vote_average", 0))
    if ps:
        fp = ps[0]["file_path"]
        c.used_files.add(fp)
        return ("poster", dl(W1280 + fp))
    return (None, None)


def main():
    data = json.load(open(sys.argv[1]))
    jobs = [(cc["title"], f["title"], bp.slug_of(f))
            for cc in data for f in cc["folders"] if bp.slug_of(f)]
    size = fit_size([t for _, t, _ in jobs])
    print(f"Building {len(jobs)} landscape covers @ font {size}\n")
    ok = miss = 0
    for coll, ttl, slug in jobs:
        try:
            if coll == "Streaming":
                base = cover_crop(dl(STREAM_COVER.format(slug=slug)))
                base.save(CACHE / f"{slug}.jpg", "JPEG", quality=90)
                base.save(OUT / f"{slug}.jpg", "JPEG", quality=90)
                ok += 1
                continue
            res = c.resolve(coll, ttl, slug)
            if not res:
                print(f"  [MISS] {coll}/{ttl}")
                miss += 1
                continue
            kind, src = backdrop(res)
            if src is None:
                print(f"  [MISS] {coll}/{ttl} (no image)")
                miss += 1
                continue
            base = person_tile(src) if kind == "person" else grade(cover_crop(src))
            base.save(CACHE / f"{slug}.jpg", "JPEG", quality=90)
            title(base, ttl, size).save(OUT / f"{slug}.jpg", "JPEG", quality=88)
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
