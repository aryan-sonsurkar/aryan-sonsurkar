#!/usr/bin/env python3
"""
Animated Hero Intro Generator.

Renders an animated GIF of a starfield with a cruising airplane,
glowing title and tagline - the first impression of the profile.

Deterministic: same input always produces the same frames.

Usage:
    python scripts/generate_hero_animation.py [--output PATH]
"""

import argparse
import math
import os
import random
import sys
from typing import List, Tuple

from PIL import Image, ImageDraw, ImageFont
import imageio

WIDTH = 900
HEIGHT = 300
FPS = 12
TOTAL_FRAMES = 120

C_BG = (10, 14, 39)
C_BG2 = (26, 26, 62)
C_CYAN = (0, 212, 255)
C_PURPLE = (123, 97, 255)
C_STAR = (255, 255, 255)
C_TEXT = (224, 230, 255)
C_TEXT_DIM = (137, 146, 176)
C_GRID = (0, 212, 255)
C_ACCENT = (0, 212, 255)


def find_font(size: int, bold: bool = False):
    if os.name == "nt":
        candidates = [
            r"C:\Windows\Fonts\segoeuib.ttf" if bold else r"C:\Windows\Fonts\segoeui.ttf",
            r"C:\Windows\Fonts\arialbd.ttf" if bold else r"C:\Windows\Fonts\arial.ttf",
            r"C:\Windows\Fonts\verdana.ttf",
        ]
    else:
        candidates = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        ]
    for p in candidates:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                continue
    return ImageFont.load_default()


def fit_font(text: str, target_size: int, max_width: int, bold: bool = False):
    """Return the largest font (down to target_size*) that fits text in max_width."""
    size = target_size
    while size >= 24:
        font = find_font(size, bold=bold)
        d = ImageDraw.ImageDraw(Image.new("RGB", (1, 1)))
        bbox = d.textbbox((0, 0), text, font=font)
        if (bbox[2] - bbox[0]) <= max_width:
            return font
        size -= 4
    return find_font(target_size, bold=bold)


def generate_stars(seed: int, count: int = 90) -> List[Tuple[float, float, float, float]]:
    rng = random.Random(seed)
    stars = []
    for _ in range(count):
        x = rng.uniform(0, WIDTH)
        y = rng.uniform(0, HEIGHT)
        brightness = rng.uniform(0.2, 0.7)
        phase = rng.uniform(0, math.pi * 2)
        stars.append((x, y, brightness, phase))
    return stars


def rotate_point(px: float, py: float, cx: float, cy: float, ang: float) -> Tuple[float, float]:
    """Rotate (px,py) around (cx,cy) by angle radians."""
    cos_a, sin_a = math.cos(ang), math.sin(ang)
    dx, dy = px - cx, py - cy
    return (cx + dx * cos_a - dy * sin_a, cy + dx * sin_a + dy * cos_a)


def draw_airplane(draw: ImageDraw.ImageDraw, cx: float, cy: float,
                  ang: float, scale: float = 1.0, alpha: int = 255):
    s = scale
    shape = [
        (-10 * s, 0), (-4 * s, -1.5 * s), (6 * s, -4 * s),
        (10 * s, -1.5 * s), (12 * s, 0),
        (10 * s, 1.5 * s), (6 * s, 4 * s), (-4 * s, 1.5 * s),
    ]
    tail = [(-6 * s, -1.5 * s), (-8 * s, -6 * s), (-3 * s, -1.5 * s)]
    tail_b = [(-6 * s, 1.5 * s), (-8 * s, 6 * s), (-3 * s, 1.5 * s)]
    color = (*C_CYAN, alpha)
    pts = [rotate_point(x, y, 0, 0, ang) for (x, y) in shape]
    pts = [(cx + x, cy + y) for (x, y) in pts]
    draw.polygon(pts, fill=color)
    for poly in (tail, tail_b):
        p = [rotate_point(x, y, 0, 0, ang) for (x, y) in poly]
        p = [(cx + x, cy + y) for (x, y) in p]
        draw.polygon(p, fill=color)


def draw_glow(img: Image.Image, cx: float, cy: float, radius: int, color):
    glow = Image.new("RGBA", img.size, (0, 0, 0, 0))
    gd = ImageDraw.ImageDraw(glow)
    for r in range(radius, 0, -1):
        a = int(0.35 * 255 * (1 - r / radius) ** 1.5)
        gd.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(*color, a))
    img.paste(Image.alpha_composite(img, glow), (0, 0))


def path_y(x: float) -> float:
    """Curved flight path across the canvas."""
    return 175 + 38 * math.sin(x / 150.0 + 0.6)


def render_frame(frame_idx: int, stars, fonts) -> Image.Image:
    img = Image.new("RGBA", (WIDTH, HEIGHT), (*C_BG, 255))
    draw = ImageDraw.ImageDraw(img)

    # Background gradient
    for y in range(HEIGHT):
        t = y / HEIGHT
        r = int(C_BG[0] + (C_BG2[0] - C_BG[0]) * t)
        g = int(C_BG[1] + (C_BG2[1] - C_BG[1]) * t)
        b = int(C_BG[2] + (C_BG2[2] - C_BG[2]) * t)
        draw.line([(0, y), (WIDTH, y)], fill=(r, g, b, 255))

    # Subtle grid
    for gx in range(0, WIDTH + 1, 150):
        draw.line([(gx, 0), (gx, HEIGHT)], fill=(*C_GRID, 8))
    for gy in range(0, HEIGHT + 1, 50):
        draw.line([(0, gy), (WIDTH, gy)], fill=(*C_GRID, 8))

    # Twinkling stars
    time_val = frame_idx / TOTAL_FRAMES
    for sx, sy, brightness, phase in stars:
        tw = 0.5 + 0.5 * math.sin(time_val * math.pi * 4 + phase)
        a = int(brightness * tw * 255)
        a = max(4, min(255, a))
        size = 1 if brightness < 0.35 else 2
        draw.ellipse([sx - size, sy - size, sx + size, sy + size], fill=(*C_STAR, a))

    # Airplane cruise: loop across once per animation
    t = frame_idx / TOTAL_FRAMES
    x = -30 + t * (WIDTH + 60)
    y = path_y(x)
    ang = 0.05 * math.cos(x / 150.0 + 0.6) - 0.06

    # Trail
    for k in range(1, 24):
        tt = max(0.0, t - k * 0.004)
        tx = -30 + tt * (WIDTH + 60)
        ty = path_y(tx)
        a = int(0.45 * (1 - k / 24) * 255)
        draw.line([(tx, ty - 1), (tx - 3, ty - 1)], fill=(*C_CYAN, a), width=2)
        draw.line([(tx, ty + 1), (tx - 3, ty + 1)], fill=(*C_CYAN, a), width=2)

    draw_glow(img, x, y, 22, C_CYAN)
    draw.img = img

    # Dashed route
    for px in range(0, WIDTH, 14):
        py = path_y(px)
        draw.line([(px, py), (px + 8, path_y(px + 8))], fill=(*C_CYAN, 38), width=1)

    draw_airplane(draw, x, y, ang, scale=1.0, alpha=255)

    # Title with soft pulsing glow
    glow_pulse = 0.5 + 0.5 * math.sin(time_val * math.pi * 2)
    name_font = fonts["name"]
    tag_font = fonts["tag"]
    small_font = fonts["small"]

    name = "ARYAN SONSURKAR"
    bbox = draw.textbbox((0, 0), name, font=name_font)
    tw = bbox[2] - bbox[0]
    nx = (WIDTH - tw) // 2
    ny = 46

    glow_off = int(6 * (0.5 + 0.5 * glow_pulse))
    for off in range(glow_off, 0, -1):
        alpha = int(40 * (1 - off / max(1, glow_off)))
        draw.text((nx - off // 2, ny - off // 2), name, font=name_font,
                  fill=(*C_CYAN, alpha))
    draw.text((nx, ny), name, font=name_font, fill=C_TEXT)

    # Accent line with moving shimmer
    line_y = ny + 44
    shimmer = int(((frame_idx * 20) % WIDTH))
    draw.line([(nx, line_y), (nx + tw, line_y)], fill=(*C_PURPLE, 120), width=2)
    draw.line([(nx, line_y), (shimmer, line_y)], fill=(*C_CYAN, 220), width=2)

    # Tagline
    tag = "building things, brick by brick"
    bbox = draw.textbbox((0, 0), tag, font=tag_font)
    tw2 = bbox[2] - bbox[0]
    draw.text(((WIDTH - tw2) // 2, line_y + 16), tag, font=tag_font, fill=C_TEXT_DIM)

    # Bottom caption
    cap = "PRESS START TO FLY THROUGH THE JOURNEY"
    bbox = draw.textbbox((0, 0), cap, font=small_font)
    tw3 = bbox[2] - bbox[0]
    draw.text(((WIDTH - tw3) // 2, HEIGHT - 34), cap, font=small_font,
              fill=(*C_TEXT_DIM, 160))

    # Bottom accent line
    draw.line([(0, HEIGHT - 4), (WIDTH, HEIGHT - 4)], fill=(*C_CYAN, 36), width=1)
    return img


def main():
    parser = argparse.ArgumentParser(description="Generate animated hero GIF")
    parser.add_argument("--output", default="assets/hero.gif")
    args = parser.parse_args()

    print(f"Generating {TOTAL_FRAMES} frames at {FPS} fps...")
    fonts = {
        "name": fit_font("ARYAN SONSURKAR", 46, WIDTH - 100, bold=True),
        "tag": find_font(18),
        "small": find_font(11),
    }
    stars = generate_stars(seed=7, count=95)

    frames = []
    for i in range(TOTAL_FRAMES):
        frame = render_frame(i, stars, fonts)
        bg = Image.new("RGB", (WIDTH, HEIGHT), C_BG)
        bg.paste(frame, mask=frame.split()[3])
        frames.append(bg)
        if (i + 1) % 30 == 0 or i == TOTAL_FRAMES - 1:
            print(f"    Frame {i + 1}/{TOTAL_FRAMES}")

    os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
    imageio.mimsave(args.output, [__import__("numpy").array(f) for f in frames],
                    format="GIF", duration=(1000 // FPS) / 1000.0, loop=0)
    print(f"  Written to {args.output} ({os.path.getsize(args.output) / 1024:.0f} KB)")
    print("Done!")


if __name__ == "__main__":
    main()