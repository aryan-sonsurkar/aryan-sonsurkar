#!/usr/bin/env python3
"""
Terminal Boot Intro Generator.

Renders an animated GIF of a terminal "booting" the profile:
a typewriter effect showing whoami, mission, and the philosophy.

Deterministic: same input always produces the same frames.

Usage:
    python scripts/generate_boot_animation.py [--output PATH]
"""

import argparse
import math
import os
import sys

from PIL import Image, ImageDraw, ImageFont
import imageio

WIDTH = 900
HEIGHT = 240
FPS = 14
TOTAL_FRAMES = 210

C_BG = (8, 11, 30)
C_TERMINAL = (10, 14, 39)
C_BORDER = (38, 48, 80)
C_TITLE_BAR = (16, 21, 45)
C_CYAN = (0, 212, 255)
C_GREEN = (80, 220, 130)
C_PURPLE = (123, 97, 255)
C_TEXT = (180, 196, 220)
C_DIM = (110, 122, 150)
C_CURSOR = (0, 212, 255)

LINES = [
    ("$", " whoami", "aryan-sonsurkar", C_TEXT),
    ("cls", None, None, None),
    ("$", " cat identity.txt", "Diploma Computer Engineering student.", C_TEXT),
    ("$", " ./mission.sh", "[OK] building things, brick by brick", C_GREEN),
    ("$", " ./stats.sh", "34 repos | 6 followers | currently: mod-codes-ide", C_TEXT),
    ("cls", None, None, None),
    ("$", " echo $PHILOSOPHY", "Learn -> Build -> Break -> Fix -> Ship", C_CYAN),
]


def find_font(size: int, bold: bool = False, mono: bool = True):
    if os.name == "nt":
        candidates = [
            r"C:\Windows\Fonts\consola.ttf",
            r"C:\Windows\Fonts\consolab.ttf" if bold else r"C:\Windows\Fonts\consola.ttf",
            r"C:\Windows\Fonts\courbd.ttf" if bold else r"C:\Windows\Fonts\cour.ttf",
        ]
    else:
        candidates = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
        ]
    for p in candidates:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                continue
    return ImageFont.load_default()


def line_str(entry):
    kind = entry[0]
    if kind == "cls":
        return ""
    return entry[1] + " " + entry[2]


def compute_timeline():
    """Return list of (line_index, char_offset, active_entry) snapshots per frame."""
    entries = [(i, ln) for i, ln in enumerate(LINES) if ln[0] != "cls"]
    total_content_chars = sum(len(ln[1]) + 1 + len(ln[2]) for _, ln in entries)
    snapshots = []
    for f in range(TOTAL_FRAMES):
        # Map frame to a char position across the whole terminal session
        progress = f / TOTAL_FRAMES
        target = int(progress * total_content_chars)
        remaining = target
        line_idx = 0
        active_entry = None
        for line_index, ln in entries:
            c_len = len(ln[1]) + 1 + len(ln[2])
            if remaining <= c_len:
                line_idx = line_index
                active_entry = (line_index, ln)
                break
            line_idx = line_index
            remaining -= c_len
        offset = remaining
        snapshots.append((line_idx, offset, active_entry))
    return snapshots


def render_frame(frame_idx, snapshots, font, snap_font):
    img = Image.new("RGBA", (WIDTH, HEIGHT), (*C_BG, 255))
    draw = ImageDraw.ImageDraw(img)

    # Terminal window
    draw.rounded_rectangle([25, 18, WIDTH - 25, HEIGHT - 18], radius=6,
                           fill=(*C_TERMINAL, 255), outline=(*C_BORDER, 255), width=1)
    # Title bar
    draw.rounded_rectangle([25, 18, WIDTH - 25, 44], radius=6,
                           fill=(*C_TITLE_BAR, 255))
    # Windows-style dots
    draw.ellipse([38, 26, 44, 32], fill=(255, 95, 86))
    draw.ellipse([50, 26, 56, 32], fill=(255, 189, 46))
    draw.ellipse([62, 26, 68, 32], fill=(39, 201, 63))
    title = "aryan@github: ~/profile"
    draw.text((WIDTH - 60, 31), title, font=snap_font, fill=(*C_DIM, 255), anchor="rm")

    # Blinking cursor phase
    cursor_on = (frame_idx // 7) % 2 == 0

    line_idx, offset, active = snapshots[frame_idx]
    x = 44
    y = 62
    line_h = 26

    visible = []
    for i in range(line_idx):
        entry = LINES[i]
        if entry[0] == "cls":
            continue
        visible.append(line_str(entry))

    # Active line typed so far
    if active is not None:
        _, ln = active
        typed = line_str(ln)
        visible.append(typed[:offset + len(ln[1] + " ")])

    for idx, text in enumerate(visible):
        y_pos = y + idx * line_h
        if y_pos > HEIGHT - 30:
            break
        color = C_TEXT
        if idx == len(visible) - 1 and text.startswith("$"):
            color = C_GREEN
        draw.text((x, y_pos), text, font=font, fill=(*color, 255))

        # Cursor at the active line
        if idx == len(visible) - 1 and active is not None and cursor_on:
            ln = active[1]
            w = draw.textlength(text, font=font)
            cursor_x = x + w + 2
            cursor_y = y_pos - 18
            draw.rectangle([cursor_x, cursor_y, cursor_x + 9, cursor_y + 20],
                           fill=(*C_CURSOR, 255))

    # Bottom hint
    hint = "system ready"
    draw.text((44, HEIGHT - 32), hint, font=snap_font, fill=(*C_GREEN, 220))
    draw.text((WIDTH - 44, HEIGHT - 32), "recording... ", font=snap_font,
              fill=(*C_DIM, 180), anchor="rm")
    return img


def main():
    parser = argparse.ArgumentParser(description="Generate terminal boot GIF")
    parser.add_argument("--output", default="assets/boot.gif")
    args = parser.parse_args()

    print(f"Generating {TOTAL_FRAMES} frames at {FPS} fps...")
    font = find_font(20, bold=False)
    snap_font = find_font(12, bold=False)
    snapshots = compute_timeline()

    frames = []
    for i in range(TOTAL_FRAMES):
        frame = render_frame(i, snapshots, font, snap_font)
        bg = Image.new("RGB", (WIDTH, HEIGHT), C_BG)
        bg.paste(frame, mask=frame.split()[3])
        frames.append(bg)
        if (i + 1) % 40 == 0 or i == TOTAL_FRAMES - 1:
            print(f"    Frame {i + 1}/{TOTAL_FRAMES}")

    os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
    imageio.mimsave(args.output, [__import__("numpy").array(f) for f in frames],
                    format="GIF", duration=(1000 // FPS) / 1000.0, loop=0)
    print(f"  Written to {args.output} ({os.path.getsize(args.output) / 1024:.0f} KB)")
    print("Done!")


if __name__ == "__main__":
    main()