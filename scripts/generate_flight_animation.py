#!/usr/bin/env python3
"""
Flight Contribution Animation Generator.

Renders an animated GIF showing an airplane traveling through
the full GitHub contribution history.

Usage:
    python scripts/generate_flight_animation.py [--input PATH] [--output PATH]
"""

import argparse
import json
import math
import os
import sys
from datetime import datetime, timedelta
from typing import List, Tuple, Dict

from PIL import Image, ImageDraw, ImageFilter, ImageFont
import imageio

# --- Canvas ---
WIDTH = 900
HEIGHT = 280

# --- Grid layout ---
CELL = 10
GAP = 3
PITCH = CELL + GAP
GRID_X = 65
GRID_Y = 42

# --- Animation ---
FPS = 12
TOTAL_FRAMES = 96
LOOP_FRAMES = TOTAL_FRAMES

# --- Colors ---
C_BG = (10, 14, 39)
C_BG2 = (14, 18, 45)
C_CYAN = (0, 212, 255)
C_PURPLE = (123, 97, 255)
C_STAR = (255, 255, 255)
C_GRID_EMPTY = (10, 14, 39)
C_GRID_EMPTY_BORDER = (18, 24, 55)
C_GRID_LOW = (14, 42, 61)
C_GRID_MED = (13, 74, 94)
C_GRID_HIGH = (0, 180, 220)
C_GRID_PEAK = (100, 80, 220)
C_TEXT = (90, 99, 128)
C_TEXT_DIM = (50, 56, 80)


def load_config(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_contributions(path: str) -> dict:
    if not os.path.exists(path):
        print(f"ERROR: {path} not found", file=sys.stderr)
        sys.exit(1)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def compute_grid(data: dict) -> Tuple[int, datetime, dict, int]:
    records = data["records"]
    dates = sorted(r["date"] for r in records)
    first = datetime.strptime(dates[0], "%Y-%m-%d")
    last = datetime.strptime(dates[-1], "%Y-%m-%d")
    first_sunday = first - timedelta(days=(first.weekday() + 1) % 7)
    last_saturday = last + timedelta(days=(5 - last.weekday()) % 7)
    num_weeks = ((last_saturday - first_sunday).days // 7) + 1
    date_map = {r["date"]: r["contribution_count"] for r in records}
    max_count = max(date_map.values()) if date_map else 1
    return num_weeks, first_sunday, date_map, max_count


def get_grid_color(count: int, max_count: int) -> Tuple[int, int, int]:
    if count == 0:
        return C_GRID_EMPTY
    ratio = count / max_count
    if ratio < 0.25:
        return C_GRID_LOW
    elif ratio < 0.5:
        return C_GRID_MED
    elif ratio < 0.75:
        return C_GRID_HIGH
    else:
        return C_GRID_PEAK


def generate_stars(seed: int, count: int = 80) -> List[Tuple[int, int, float, float]]:
    """Generate random star positions with twinkle phase."""
    import random
    rng = random.Random(seed)
    stars = []
    for _ in range(count):
        x = rng.randint(0, WIDTH)
        y = rng.randint(0, HEIGHT)
        brightness = rng.uniform(0.15, 0.6)
        phase = rng.uniform(0, math.pi * 2)
        stars.append((x, y, brightness, phase))
    return stars


def ease_in_out(t: float) -> float:
    """Smooth easing function."""
    return t * t * (3 - 2 * t)


def lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def draw_airplane(draw: ImageDraw.ImageDraw, cx: float, cy: float,
                  angle: float, scale: float = 1.0, alpha: int = 255):
    """Draw a small airplane shape centered at (cx, cy)."""
    s = scale
    # Airplane body points (nose pointing right)
    body = [
        (cx - 10*s, cy),       # tail
        (cx - 4*s, cy - 1.5*s),
        (cx + 6*s, cy - 4*s),  # right wing tip
        (cx + 10*s, cy - 1.5*s),
        (cx + 12*s, cy),       # nose
        (cx + 10*s, cy + 1.5*s),
        (cx + 6*s, cy + 4*s),  # left wing tip
        (cx - 4*s, cy + 1.5*s),
    ]
    # Tail fin
    tail = [
        (cx - 6*s, cy - 1.5*s),
        (cx - 8*s, cy - 6*s),
        (cx - 3*s, cy - 1.5*s),
    ]
    tail_bottom = [
        (cx - 6*s, cy + 1.5*s),
        (cx - 8*s, cy + 6*s),
        (cx - 3*s, cy + 1.5*s),
    ]

    color = (*C_CYAN, alpha)
    draw.polygon(body, fill=color)
    draw.polygon(tail, fill=color)
    draw.polygon(tail_bottom, fill=color)


def draw_glow(img: Image.Image, cx: float, cy: float,
              radius: int = 20, color: Tuple[int, int, int] = C_CYAN,
              intensity: float = 0.4):
    """Draw a soft glow at position."""
    glow_layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    glow_draw = ImageDraw.ImageDraw(glow_layer)
    for r in range(radius, 0, -1):
        a = int(intensity * 255 * (r / radius) ** 0.5 * (1 - r / radius))
        a = max(0, min(255, a))
        glow_draw.ellipse(
            [cx - r, cy - r, cx + r, cy + r],
            fill=(*color, a)
        )
    img.paste(Image.alpha_composite(Image.new("RGBA", img.size, (0,0,0,0)), glow_layer), (0, 0))


def render_frame(
    frame_idx: int,
    num_weeks: int,
    first_sunday: datetime,
    date_map: dict,
    max_count: int,
    stars: List[Tuple[int, int, float, float]],
    total_contributions: int,
    active_days: int,
) -> Image.Image:
    """Render a single animation frame."""

    # Create base image
    img = Image.new("RGBA", (WIDTH, HEIGHT), (*C_BG, 255))
    draw = ImageDraw.ImageDraw(img)

    # --- Background gradient (subtle) ---
    for y in range(HEIGHT):
        t = y / HEIGHT
        r = int(C_BG[0] + (C_BG2[0] - C_BG[0]) * t)
        g = int(C_BG[1] + (C_BG2[1] - C_BG[1]) * t)
        b = int(C_BG[2] + (C_BG2[2] - C_BG[2]) * t)
        draw.line([(0, y), (WIDTH, y)], fill=(r, g, b, 255))

    # --- Stars ---
    time_val = frame_idx / TOTAL_FRAMES
    for sx, sy, brightness, phase in stars:
        twinkle = 0.5 + 0.5 * math.sin(time_val * math.pi * 4 + phase)
        a = int(brightness * twinkle * 255)
        a = max(0, min(255, a))
        size = 1 if brightness < 0.3 else 2
        draw.ellipse([sx-size, sy-size, sx+size, sy+size], fill=(*C_STAR, a))

    # --- Grid cells ---
    grid_cells = []
    for week in range(num_weeks):
        for row in range(7):
            x = GRID_X + week * PITCH
            y = GRID_Y + row * PITCH
            cell_date = first_sunday + timedelta(weeks=week, days=row)
            date_str = cell_date.strftime("%Y-%m-%d")
            count = date_map.get(date_str, 0)
            color = get_grid_color(count, max_count)

            # Fade in grid cells progressively based on frame
            cell_week = week
            fade_threshold = (frame_idx / TOTAL_FRAMES) * num_weeks
            if cell_week > fade_threshold + 2:
                continue

            cell_alpha = 1.0
            if cell_week > fade_threshold - 1:
                cell_alpha = max(0, min(1, (fade_threshold + 2 - cell_week) / 3))

            r_c, g_c, b_c = color
            a_c = int(cell_alpha * 255)
            draw.rounded_rectangle(
                [x, y, x + CELL, y + CELL],
                radius=2,
                fill=(r_c, g_c, b_c, a_c),
                outline=(C_GRID_EMPTY_BORDER[0], C_GRID_EMPTY_BORDER[1], C_GRID_EMPTY_BORDER[2], int(cell_alpha * 100)),
                width=1,
            )
            grid_cells.append((x, y, week, count))

    # --- Month labels ---
    seen_months = {}
    for week in range(num_weeks):
        ws = first_sunday + timedelta(weeks=week)
        mk = ws.strftime("%Y-%m")
        if mk not in seen_months:
            seen_months[mk] = True
            mx = GRID_X + week * PITCH + CELL // 2
            month_name = ws.strftime("%b")
            draw.text((mx, 28), month_name, fill=(*C_TEXT_DIM, 200), anchor="mm")

    # --- Day labels ---
    day_names = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
    for row in range(7):
        dy = GRID_Y + row * PITCH + CELL // 2
        draw.text((55, dy), day_names[row], fill=(*C_TEXT_DIM, 180), anchor="rm")

    # --- Compute airplane position ---
    # Animation progress: 0.0 to 1.0
    progress = frame_idx / TOTAL_FRAMES

    # Airplane travel: starts at frame 12, ends at frame 82
    travel_start = 12 / TOTAL_FRAMES
    travel_end = 82 / TOTAL_FRAMES

    if progress < travel_start:
        airplane_progress = 0.0
    elif progress > travel_end:
        airplane_progress = 1.0
    else:
        airplane_progress = (progress - travel_start) / (travel_end - travel_start)
        airplane_progress = ease_in_out(airplane_progress)

    # Map progress to week position
    airplane_week_f = airplane_progress * (num_weeks - 1)
    airplane_week = int(round(airplane_week_f))

    # Find the latest active week for the airplane to target
    latest_active_week = 0
    for week in range(num_weeks):
        for row in range(7):
            cell_date = first_sunday + timedelta(weeks=week, days=row)
            if date_map.get(cell_date.strftime("%Y-%m-%d"), 0) > 0:
                latest_active_week = max(latest_active_week, week)

    # Clamp airplane to latest active week
    if airplane_week > latest_active_week:
        airplane_week = latest_active_week

    # Find a good row for the airplane (center of activity for that week)
    best_row = 3  # default middle
    best_count = 0
    for row in range(7):
        cell_date = first_sunday + timedelta(weeks=airplane_week, days=row)
        c = date_map.get(cell_date.strftime("%Y-%m-%d"), 0)
        if c > best_count:
            best_count = c
            best_row = row

    # Airplane pixel position
    plane_x = GRID_X + airplane_week_f * PITCH + CELL // 2
    plane_y = GRID_Y + best_row * PITCH + CELL // 2

    # --- Flight trail ---
    trail_alpha_base = 0.6
    trail_points = []
    for w in range(airplane_week + 1):
        # Find best row for this week
        tr = 3
        tc = 0
        for row in range(7):
            cd = first_sunday + timedelta(weeks=w, days=row)
            c = date_map.get(cd.strftime("%Y-%m-%d"), 0)
            if c > tc:
                tc = c
                tr = row
        tx = GRID_X + w * PITCH + CELL // 2
        ty = GRID_Y + tr * PITCH + CELL // 2
        trail_points.append((tx, ty))

    # Draw trail with decreasing opacity
    if len(trail_points) >= 2:
        for i in range(len(trail_points) - 1):
            t = i / max(1, len(trail_points) - 1)
            a = int(trail_alpha_base * t * 255)
            a = max(0, min(255, a))
            x1, y1 = trail_points[i]
            x2, y2 = trail_points[i + 1]
            # Trail glow
            for offset in range(3, 0, -1):
                ga = int(a * 0.3 / offset)
                draw.line(
                    [(x1, y1 + offset), (x2, y2 + offset)],
                    fill=(*C_CYAN, ga), width=1
                )
                draw.line(
                    [(x1, y1 - offset), (x2, y2 - offset)],
                    fill=(*C_CYAN, ga), width=1
                )
            draw.line(
                [(x1, y1), (x2, y2)],
                fill=(*C_CYAN, a), width=2
            )

    # --- Dashed flight path (full route, faint) ---
    path_y = GRID_Y + 3 * PITCH
    path_start_x = GRID_X
    path_end_x = GRID_X + (num_weeks - 1) * PITCH + CELL // 2
    dash_len = 8
    gap_len = 6
    x = path_start_x
    while x < path_end_x:
        x2 = min(x + dash_len, path_end_x)
        # Slight wave
        wy = path_y + 4 * math.sin(x * 0.02)
        wy2 = path_y + 4 * math.sin(x2 * 0.02)
        fade = 0.08
        draw.line([(x, wy), (x2, wy2)], fill=(*C_CYAN, int(fade * 255)), width=1)
        x += dash_len + gap_len

    # --- Airplane glow ---
    if airplane_week > 0 or progress >= travel_start:
        glow_radius = 18 + int(3 * math.sin(time_val * math.pi * 6))
        glow_layer = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
        glow_draw = ImageDraw.ImageDraw(glow_layer)
        for r in range(glow_radius, 0, -1):
            ga = int(0.35 * 255 * (1 - r / glow_radius) ** 1.5)
            ga = max(0, min(255, ga))
            glow_draw.ellipse(
                [plane_x - r, plane_y - r, plane_x + r, plane_y + r],
                fill=(*C_CYAN, ga)
            )
        img = Image.alpha_composite(img, glow_layer)
        draw = ImageDraw.ImageDraw(img)

    # --- Airplane ---
    if progress >= travel_start:
        plane_alpha = 255
        if progress < travel_start + 5 / TOTAL_FRAMES:
            plane_alpha = int((progress - travel_start) / (5 / TOTAL_FRAMES) * 255)
        draw_airplane(draw, plane_x, plane_y, 0, scale=1.0, alpha=plane_alpha)

    # --- Contribution count text ---
    total = total_contributions
    active = active_days
    stats_y = HEIGHT - 30
    draw.text((GRID_X, stats_y), f"{total} CONTRIBUTIONS", fill=(*C_TEXT, 180))
    draw.text((GRID_X, stats_y + 14), f"{active} ACTIVE DAYS  |  {num_weeks} WEEKS",
              fill=(*C_TEXT_DIM, 150))

    # --- Legend ---
    legend_x = WIDTH - 160
    legend_y = stats_y
    labels = ["Less", "More"]
    colors_legend = [C_GRID_EMPTY, C_GRID_LOW, C_GRID_MED, C_GRID_HIGH, C_GRID_PEAK]
    for i, c in enumerate(colors_legend):
        lx = legend_x + i * 14
        draw.rounded_rectangle([lx, legend_y, lx + 10, legend_y + 10], radius=1,
                               fill=(*c, 200))
    draw.text((legend_x + 74, legend_y + 5), "Less", fill=(*C_TEXT_DIM, 150), anchor="lm")
    draw.text((legend_x + 114, legend_y + 5), "More", fill=(*C_TEXT_DIM, 150), anchor="lm")

    # --- Bottom accent line ---
    draw.line([(0, HEIGHT - 4), (WIDTH, HEIGHT - 4)],
              fill=(*C_CYAN, 30), width=1)

    return img


def generate_animation(
    data: dict,
    config: dict,
    output_path: str,
) -> str:
    """Generate the full flight animation GIF."""

    records = data["records"]
    total = data.get("total_contributions", sum(r["contribution_count"] for r in records))
    active = data.get("active_days", sum(1 for r in records if r["contribution_count"] > 0))

    num_weeks, first_sunday, date_map, max_count = compute_grid(data)
    stars = generate_stars(seed=42, count=70)

    print(f"  Grid: {num_weeks} weeks, max count: {max_count}")
    print(f"  Rendering {TOTAL_FRAMES} frames at {FPS} fps...")

    frames = []
    for i in range(TOTAL_FRAMES):
        frame = render_frame(
            i, num_weeks, first_sunday, date_map, max_count,
            stars, total, active,
        )
        # Convert RGBA to RGB for GIF
        bg = Image.new("RGB", (WIDTH, HEIGHT), C_BG)
        bg.paste(frame, mask=frame.split()[3])
        frames.append(bg)

        if (i + 1) % 20 == 0 or i == TOTAL_FRAMES - 1:
            print(f"    Frame {i + 1}/{TOTAL_FRAMES}")

    # Write GIF
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    duration_ms = 1000 // FPS

    # Use imageio for GIF writing
    frame_arrays = [__import__("numpy").array(f) for f in frames]
    imageio.mimsave(
        output_path,
        frame_arrays,
        format="GIF",
        duration=duration_ms / 1000.0,
        loop=0,
    )

    size_kb = os.path.getsize(output_path) / 1024
    print(f"  Written to {output_path} ({size_kb:.0f} KB)")
    return output_path


def main():
    parser = argparse.ArgumentParser(description="Generate flight contribution animation")
    parser.add_argument("--input", default="data/contributions.json")
    parser.add_argument("--output", default="assets/flight-map.gif")
    parser.add_argument("--config", default="config/profile.json")
    args = parser.parse_args()

    print("Loading data...")
    data = load_contributions(args.input)
    config = load_config(args.config)

    records = data["records"]
    print(f"  Records: {len(records)}")
    print(f"  Range: {data.get('first_date', '?')} to {data.get('last_date', '?')}")
    print(f"  Total: {data.get('total_contributions', '?')}")

    print("Generating animation...")
    generate_animation(data, config, args.output)
    print("Done!")


if __name__ == "__main__":
    main()
