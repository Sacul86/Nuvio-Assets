"""
Generate themed placeholder landscape images (1920x1080) for all 41 Nuvio collection themes.
Each image gets a unique gradient palette matching its genre + a centered label.
"""

import math
import struct
import zlib
from pathlib import Path

WIDTH, HEIGHT = 1920, 1080

THEMES = {
    "horror-new-movies":       {"colors": [(20, 0, 0), (80, 10, 10), (30, 0, 0)], "label": "Horror • New Movies"},
    "horror-new-series":       {"colors": [(10, 10, 20), (60, 15, 30), (20, 5, 10)], "label": "Horror • New Series"},
    "horror-supernatural":     {"colors": [(15, 5, 25), (70, 20, 80), (10, 0, 15)], "label": "Horror • Supernatural"},
    "horror-slasher":          {"colors": [(30, 0, 0), (120, 10, 10), (15, 0, 0)], "label": "Horror • Slasher"},
    "horror-creature":         {"colors": [(10, 15, 10), (50, 70, 40), (5, 10, 5)], "label": "Horror • Creature"},
    "thriller-new-movies":     {"colors": [(10, 10, 40), (30, 80, 140), (5, 5, 20)], "label": "Thriller • New Movies"},
    "thriller-new-series":     {"colors": [(15, 15, 30), (50, 50, 100), (10, 10, 25)], "label": "Thriller • New Series"},
    "thriller-psychological":  {"colors": [(20, 15, 25), (80, 50, 90), (10, 5, 15)], "label": "Thriller • Psychological"},
    "thriller-crime":          {"colors": [(10, 10, 15), (60, 60, 70), (5, 5, 10)], "label": "Thriller • Crime"},
    "thriller-action":         {"colors": [(40, 20, 0), (180, 80, 10), (20, 10, 0)], "label": "Thriller • Action"},
    "zombie-new-movies":       {"colors": [(20, 25, 10), (80, 100, 30), (10, 15, 5)], "label": "Zombie • New Movies"},
    "zombie-new-series":       {"colors": [(25, 20, 10), (90, 80, 40), (15, 10, 5)], "label": "Zombie • New Series"},
    "zombie-comedy":           {"colors": [(30, 35, 10), (110, 130, 40), (15, 20, 5)], "label": "Zombie • Comedy"},
    "zombie-survival":         {"colors": [(20, 18, 10), (70, 65, 35), (10, 8, 5)], "label": "Zombie • Survival"},
    "space-new-movies":        {"colors": [(5, 0, 20), (20, 10, 80), (100, 50, 150)], "label": "Space • New Movies"},
    "space-new-series":        {"colors": [(0, 5, 15), (10, 30, 70), (60, 80, 140)], "label": "Space • New Series"},
    "space-alien":             {"colors": [(0, 15, 5), (10, 60, 30), (50, 150, 80)], "label": "Space • Alien"},
    "space-exploration":       {"colors": [(5, 5, 20), (30, 30, 100), (80, 80, 180)], "label": "Space • Exploration"},
    "space-opera":             {"colors": [(10, 0, 20), (50, 10, 90), (120, 40, 180)], "label": "Space • Opera"},
    "mystery-new-movies":      {"colors": [(15, 12, 8), (60, 50, 30), (30, 25, 15)], "label": "Mystery • New Movies"},
    "mystery-new-series":      {"colors": [(10, 10, 12), (50, 45, 55), (20, 18, 25)], "label": "Mystery • New Series"},
    "mystery-detective":       {"colors": [(20, 15, 8), (80, 60, 30), (40, 30, 15)], "label": "Mystery • Detective"},
    "mystery-whodunit":        {"colors": [(18, 10, 5), (70, 45, 20), (35, 22, 10)], "label": "Mystery • Whodunit"},
    "mystery-conspiracy":      {"colors": [(8, 8, 12), (40, 40, 60), (15, 15, 25)], "label": "Mystery • Conspiracy"},
    "scifi-new-movies":        {"colors": [(0, 10, 20), (0, 60, 120), (0, 150, 200)], "label": "Sci-Fi • New Movies"},
    "scifi-new-series":        {"colors": [(5, 10, 15), (20, 50, 80), (60, 120, 160)], "label": "Sci-Fi • New Series"},
    "scifi-dystopian":         {"colors": [(15, 10, 5), (60, 40, 20), (120, 80, 40)], "label": "Sci-Fi • Dystopian"},
    "scifi-ai":                {"colors": [(0, 15, 15), (0, 80, 80), (0, 180, 180)], "label": "Sci-Fi • AI"},
    "scifi-timetravel":        {"colors": [(10, 0, 20), (60, 20, 120), (140, 60, 220)], "label": "Sci-Fi • Time Travel"},
    "apoc-new-movies":         {"colors": [(30, 15, 0), (140, 70, 10), (60, 30, 5)], "label": "Apocalyptic • New Movies"},
    "apoc-new-series":         {"colors": [(25, 20, 10), (100, 80, 40), (50, 40, 20)], "label": "Apocalyptic • New Series"},
    "apoc-post":               {"colors": [(20, 20, 15), (80, 80, 60), (40, 40, 30)], "label": "Apocalyptic • Post"},
    "apoc-pandemic":           {"colors": [(10, 15, 5), (40, 70, 20), (20, 35, 10)], "label": "Apocalyptic • Pandemic"},
    "apoc-nuclear":            {"colors": [(40, 20, 0), (200, 100, 0), (255, 200, 50)], "label": "Apocalyptic • Nuclear"},
    "apoc-dystopia":           {"colors": [(10, 5, 15), (50, 25, 70), (100, 50, 140)], "label": "Apocalyptic • Dystopia"},
    "disaster-new-movies":     {"colors": [(20, 15, 5), (100, 70, 20), (200, 140, 40)], "label": "Disaster • New Movies"},
    "disaster-new-series":     {"colors": [(5, 15, 25), (20, 60, 100), (40, 120, 200)], "label": "Disaster • New Series"},
    "disaster-earth":          {"colors": [(30, 10, 0), (160, 50, 0), (255, 120, 20)], "label": "Disaster • Earth"},
    "disaster-water":          {"colors": [(0, 10, 25), (0, 50, 120), (20, 100, 200)], "label": "Disaster • Water"},
    "disaster-storm":          {"colors": [(10, 10, 15), (50, 50, 70), (100, 100, 130)], "label": "Disaster • Storm"},
    "disaster-space":          {"colors": [(5, 0, 10), (25, 5, 50), (80, 20, 120)], "label": "Disaster • Space"},
}


def lerp_color(c1, c2, t):
    return tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))


def generate_image(slug, theme_info):
    """Generate a 1920x1080 gradient JPG with a centered label."""
    from PIL import Image, ImageDraw, ImageFont

    colors = theme_info["colors"]
    label = theme_info["label"]

    img = Image.new("RGB", (WIDTH, HEIGHT))
    pixels = img.load()

    for y in range(HEIGHT):
        t = y / (HEIGHT - 1)
        if t < 0.5:
            c = lerp_color(colors[0], colors[1], t * 2)
        else:
            c = lerp_color(colors[1], colors[2], (t - 0.5) * 2)
        for x in range(WIDTH):
            vignette = 1.0 - 0.3 * ((x - WIDTH / 2) / (WIDTH / 2)) ** 2
            pixels[x, y] = tuple(max(0, min(255, int(ch * vignette))) for ch in c)

    draw = ImageDraw.Draw(img)

    try:
        font_large = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 64)
        font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 28)
    except (OSError, IOError):
        font_large = ImageFont.load_default()
        font_small = font_large

    bbox = draw.textbbox((0, 0), label, font=font_large)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    tx = (WIDTH - tw) // 2
    ty = (HEIGHT - th) // 2

    for dx in (-2, -1, 0, 1, 2):
        for dy in (-2, -1, 0, 1, 2):
            draw.text((tx + dx, ty + dy), label, fill=(0, 0, 0), font=font_large)
    draw.text((tx, ty), label, fill=(255, 255, 255), font=font_large)

    sub = f"NUVIO • {slug}"
    bbox2 = draw.textbbox((0, 0), sub, font=font_small)
    sw = bbox2[2] - bbox2[0]
    sx = (WIDTH - sw) // 2
    sy = ty + th + 30
    draw.text((sx, sy), sub, fill=(180, 180, 180), font=font_small)

    out_dir = Path("assets")
    out_dir.mkdir(exist_ok=True)
    out_path = out_dir / f"{slug}.jpg"
    img.save(out_path, "JPEG", quality=85)
    return out_path


def main():
    print(f"Generating {len(THEMES)} themed landscape placeholders (1920x1080)...")
    for i, (slug, info) in enumerate(THEMES.items(), 1):
        path = generate_image(slug, info)
        print(f"  [{i:2d}/{len(THEMES)}] {path}")
    print(f"\nDone. {len(THEMES)} images in assets/")


if __name__ == "__main__":
    main()
