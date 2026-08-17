#!/usr/bin/env python3
"""
Animated Project Star Map Generator.

Renders an animated GIF of projects as a twinkling constellation,
with connecting routes and a visiting cursor - the "what I build" view.

Deterministic: same input always produces the same frames.

Usage:
    python scripts/generate_project_map_animation.py [--output PATH]
"""

import argparse
import math
import os
import random
import sys

from PIL import Image, ImageDraw, ImageFont
import imageio

WIDTH = 900
HEIGHT = 320
FPS = 12
TOTAL_FRAMES = 96

C_BG = (8, 11, 30)
C_BG2 = (18, 20, 48)
C_CYAN = (0, 212, 255)
C_PURPLE = (123, 97, 255)
C_GREEN = (80, 220, 130)
C_TEXT = (190, 200, 225)
C_DIM = (110, 122, 150)
C_STAR = (255, 255, 255)

# (name, x, y, size, color) - constellation nodes
PROJECTS = [
    ("ModCode IDE", 150, 90, 5, C_CYAN),
    ("Fixly-Desktop", 330, 60, 4, C_PURPLE),
    ("SmartPark DBMS", 520, 80, 4, C_GREEN),
    ("git-system", 690, 110, 4, C_CYAN),
    ("weekly-leetcode", 790, 180, 4, C_PURPLE),
    ("Portfolio", 700, 250, 4, C_GREEN),
    ("ESP32 devices", 500, 240, 4, C_CYAN),
    ("draco-cli", 320, 210, 4, C_PURPLE),
    ("Hack 2k26", 140, 200, 4, C_GREEN),
    ("Full-Stack Journey", 250, 300, 3, C_CYAN),
]

# Route that a cursor visits (project indices), forming a "flight path"
ROUTE = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 0]


def find_font(size: int, bold: bool = False):
    if os.name == "nt":
        candidates = [
            r"C:\Windows\Fonts\segoeuib.ttf" if bold else r"C:\Windows\Fonts\segoeui.ttf",
            r"C:\Windows\Fonts\arialbd.ttf" if bold else r"C:\Windows\Fonts\arial.ttf",
        ]
    else:
        candidates = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        ]
    for p in candidates:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                continue
    return ImageFont.load_default()


def draw_star(draw, cx, cy, size, alpha, color=C_STAR):
    draw.line([(cx - size, cy), (cx + size, cy)], fill=(*color, alpha), width=1)
    draw.line([(cx, cy - size), (cx, cy + size)], fill=(*color, alpha), width=1)


def render_frame(frame_idx, stars, font, label_font):
    img = Image.new("RGBA", (WIDTH, HEIGHT), (*C_BG, 255))
    draw = ImageDraw.ImageDraw(img)

    # Background gradient
    for y in range(HEIGHT):
        t = y / HEIGHT
        r = int(C_BG[0] + (C_BG2[0] - C_BG[0]) * t)
        g = int(C_BG[1] + (C_BG2[1] - C_BG[1]) * t)
        b = int(C_BG[2] + (C_BG2[2] - C_BG[2]) * t)
        draw.line([(0, y), (WIDTH, y)], fill=(r, g, b, 255))

    time_val = frame_idx / TOTAL_FRAMES

    # Tiny background stars
    for sx, sy, brightness, phase in stars:
        tw = 0.5 + 0.5 * math.sin(time_val * math.pi * 4 + phase)
        a = int(brightness * tw * 180)
        a = max(4, min(255, a))
        draw.ellipse([sx - 1, sy - 1, sx + 1, sy + 1], fill=(*C_STAR, a))

    # Constellation routes (faint lines between connected nodes)
    for i in range(len(PROJECTS) - 1):
        x1, y1 = PROJECTS[i][1], PROJECTS[i][2]
        x2, y2 = PROJECTS[i + 1][1], PROJECTS[i + 1][2]
        draw.line([(x1, y1), (x2, y2)], fill=(*C_PURPLE, 36), width=1)

    # Route cursor (glowing dot that visits nodes)
    route_t = time_val
    seg_total = len(ROUTE) - 1
    seg = route_t * seg_total
    seg_idx = min(int(seg), seg_total - 1)
    seg_frac = seg - seg_idx
    p1 = PROJECTS[ROUTE[seg_idx]]
    p2 = PROJECTS[ROUTE[seg_idx + 1]]
    cx = p1[1] + (p2[1] - p1[1]) * seg_frac
    cy = p1[2] + (p2[2] - p1[2]) * seg_frac
    glow = Image.new("RGBA", img.size, (0, 0, 0, 0))
    gd = ImageDraw.ImageDraw(glow)
    for r in range(22, 0, -1):
        a = int(0.3 * 255 * (1 - r / 22) ** 1.5)
        gd.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(*C_CYAN, a))
    img.paste(Image.alpha_composite(img, glow), (0, 0))
    draw = ImageDraw.ImageDraw(img)
    draw.ellipse([cx - 3, cy - 3, cx + 3, cy + 3], fill=(*C_CYAN, 255))

    # Node stars with pulse
    for i, (name, nx, ny, size, color) in enumerate(PROJECTS):
        pulse = 0.5 + 0.5 * math.sin(time_val * math.pi * 2 + i * 0.9)
        a = int((120 + 100 * pulse))
        # Visited nodes glow brighter
        visited = (seg_frac and i <= seg_idx) or i < seg_idx
        if visited:
            a = int(200 + 55 * pulse)
        draw_star(draw, nx, ny, size, a, color=color)

    # Labels
    for i, (name, nx, ny, size, color) in enumerate(PROJECTS):
        lx = nx + 14
        ly = ny + 4
        # Keep labels on canvas
        lx = min(lx, WIDTH - 40)
        draw.text((lx, ly), name, font=label_font, fill=(*C_DIM, 230))

    # Header
    draw.text((44, 18), "PROJECT CONSTELLATION", font=font, fill=(*C_CYAN, 255))
    draw.text((44, 44), "hover over a star - each one is something I'm building",
              font=label_font, fill=(*C_DIM, 200))

    # Bottom accent
    draw.line([(0, HEIGHT - 4), (WIDTH, HEIGHT - 4)], fill=(*C_CYAN, 36), width=1)
    return img


def main():
    parser = argparse.ArgumentParser(description="Generate animated project star map")
    parser.add_argument("--output", default="assets/project-map.gif")
    args = parser.parse_args()

    print(f"Generating {TOTAL_FRAMES} frames at {FPS} fps...")
    font = find_font(16, bold=True)
    label_font = find_font(11)

    rng = random.Random(11)
    stars = [(rng.uniform(0, WIDTH), rng.uniform(0, HEIGHT),
              rng.uniform(0.2, 0.7), rng.uniform(0, math.pi * 2)) for _ in range(70)]

    frames = []
    for i in range(TOTAL_FRAMES):
        frame = render_frame(i, stars, font, label_font)
        bg = Image.new("RGB", (WIDTH, HEIGHT), C_BG)
        bg.paste(frame, mask=frame.split()[3])
        frames.append(bg)
        if (i + 1) % 20 == 0 or i == TOTAL_FRAMES - 1:
            print(f"    Frame {i + 1}/{TOTAL_FRAMES}")

    os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
    imageio.mimsave(args.output, [__import__("numpy").array(f) for f in frames],
                    format="GIF", duration=(1000 // FPS) / 1000.0, loop=0)
    print(f"  Written to {args.output} ({os.path.getsize(args.output) / 1024:.0f} KB)")
    print("Done!")


if __name__ == "__main__":
    main()