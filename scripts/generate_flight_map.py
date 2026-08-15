#!/usr/bin/env python3
"""
Generate the Flight Contribution Map SVG from contribution data.

Reads data/contributions.json (produced by fetch_contributions.py) and
generates assets/flight-map.svg deterministically.

Usage:
    python scripts/generate_flight_map.py [--input PATH] [--output PATH]

The generated SVG is deterministic: identical input produces identical output.
"""

import argparse
import json
import os
import sys
from datetime import datetime, timedelta
from math import ceil


# --- Visual constants (deterministic) ---
CELL_SIZE = 10
CELL_GAP = 3
CELL_PITCH = CELL_SIZE + CELL_GAP
GRID_X_START = 65
GRID_Y_START = 42
SVG_WIDTH = 900
SVG_HEIGHT = 240

# Color palette (dark aviation theme)
COLOR_EMPTY = "#0a0e27"
COLOR_LOW = "#0e2a3d"
COLOR_MEDIUM = "#0d4a5e"
COLOR_HIGH = "#00d4ff"
COLOR_PEAK = "#7b61ff"


def load_contributions(path: str) -> dict:
    """Load contribution data from JSON file."""
    if not os.path.exists(path):
        print(f"ERROR: {path} not found. Run fetch_contributions.py first.", file=sys.stderr)
        sys.exit(1)

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    records = data.get("records", [])
    if not records:
        print("ERROR: No contribution records in data file", file=sys.stderr)
        sys.exit(1)

    return data


def build_date_map(records: list) -> dict:
    """Build a lookup dict from date string to contribution count."""
    return {r["date"]: r["contribution_count"] for r in records}


def compute_grid(records: list) -> tuple:
    """
    Compute the grid dimensions and layout from records.

    Returns:
        (num_weeks, first_sunday, date_map, max_count, total, active_days)
    """
    dates = sorted(r["date"] for r in records)
    first_date = datetime.strptime(dates[0], "%Y-%m-%d")
    last_date = datetime.strptime(dates[-1], "%Y-%m-%d")

    # Find the Sunday on or before the first date (grid anchor)
    first_sunday = first_date - timedelta(days=(first_date.weekday() + 1) % 7)

    # Find the Saturday on or after the last date
    last_saturday = last_date + timedelta(days=(5 - last_date.weekday()) % 7)

    # Number of weeks
    num_weeks = ((last_saturday - first_sunday).days // 7) + 1

    date_map = build_date_map(records)
    max_count = max(date_map.values()) if date_map else 1
    total = sum(date_map.values())
    active_days = sum(1 for v in date_map.values() if v > 0)

    return num_weeks, first_sunday, date_map, max_count, total, active_days


def get_color(count: int, max_count: int) -> str:
    """Map contribution count to color."""
    if count == 0 or max_count == 0:
        return COLOR_EMPTY
    ratio = count / max_count
    if ratio < 0.25:
        return COLOR_LOW
    elif ratio < 0.5:
        return COLOR_MEDIUM
    elif ratio < 0.75:
        return COLOR_HIGH
    else:
        return COLOR_PEAK


def compute_airplane_position(date_map: dict, first_sunday: datetime) -> tuple:
    """Find the latest active date and return its grid position."""
    latest_date = None
    latest_count = 0
    for date_str, count in date_map.items():
        if count > 0:
            d = datetime.strptime(date_str, "%Y-%m-%d")
            if latest_date is None or d > latest_date:
                latest_date = d
                latest_count = count

    if latest_date is None:
        return GRID_X_START + 5 * CELL_PITCH, GRID_Y_START + 3 * CELL_PITCH

    days_since_sunday = (latest_date - first_sunday).days
    week = days_since_sunday // 7
    day = latest_date.weekday()
    # Convert weekday (Mon=0..Sun=6) to grid row (Sun=0..Sat=6)
    row = (day + 1) % 7

    x = GRID_X_START + week * CELL_PITCH + CELL_SIZE // 2
    y = GRID_Y_START + row * CELL_PITCH + CELL_SIZE // 2
    return x, y


def generate_svg(date_map: dict, num_weeks: int, first_sunday: datetime,
                 max_count: int, total: int, active_days: int) -> str:
    """Generate the flight map SVG string."""

    # Compute airplane position
    plane_x, plane_y = compute_airplane_position(date_map, first_sunday)

    # Compute grid height
    grid_height = 7 * CELL_PITCH

    # Generate month labels
    month_labels = []
    seen_months = {}
    for week in range(num_weeks):
        week_start = first_sunday + timedelta(weeks=week)
        month_key = week_start.strftime("%Y-%m")
        month_name = week_start.strftime("%b")
        if month_key not in seen_months:
            seen_months[month_key] = True
            x = GRID_X_START + week * CELL_PITCH + CELL_SIZE // 2
            month_labels.append(
                f'    <text x="{x}" y="28" text-anchor="middle" '
                f'font-family="\'Segoe UI\', system-ui, sans-serif" '
                f'font-size="10" fill="#3a4060">{month_name}</text>'
            )

    # Generate day labels
    day_names = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
    day_labels = []
    for row in range(7):
        y = GRID_Y_START + row * CELL_PITCH + CELL_SIZE - 1
        day_labels.append(
            f'    <text x="55" y="{y}" text-anchor="end" '
            f'font-family="\'Segoe UI\', system-ui, sans-serif" '
            f'font-size="8" fill="#2a3050">{day_names[row]}</text>'
        )

    # Generate grid cells
    grid_cells = []
    for week in range(num_weeks):
        for row in range(7):
            x = GRID_X_START + week * CELL_PITCH
            y = GRID_Y_START + row * CELL_PITCH

            # Compute the date for this cell
            cell_date = first_sunday + timedelta(weeks=week, days=row)
            date_str = cell_date.strftime("%Y-%m-%d")

            count = date_map.get(date_str, 0)
            color = get_color(count, max_count)
            opacity = "0.6" if count == 0 else "0.8"

            grid_cells.append(
                f'    <rect x="{x}" y="{y}" width="{CELL_SIZE}" height="{CELL_SIZE}" '
                f'rx="2" fill="{color}" opacity="{opacity}"/>'
            )

    # Compute SVG height based on actual grid
    svg_height = max(SVG_HEIGHT, GRID_Y_START + grid_height + 60)

    # Flight path - smooth curve across the grid
    path_end_x = GRID_X_START + (num_weeks - 1) * CELL_PITCH + CELL_SIZE // 2
    mid_y = GRID_Y_START + 3 * CELL_PITCH  # Center vertically

    # Build control points for a smooth bezier
    cp1_x = GRID_X_START + num_weeks * CELL_PITCH * 0.15
    cp1_y = mid_y - 12
    cp2_x = GRID_X_START + num_weeks * CELL_PITCH * 0.5
    cp2_y = mid_y + 8
    cp3_x = GRID_X_START + num_weeks * CELL_PITCH * 0.8
    cp3_y = mid_y - 6

    flight_path = (
        f"M {GRID_X_START},{mid_y} "
        f"C {cp1_x},{cp1_y} {cp2_x},{cp2_y} {path_end_x},{mid_y - 5}"
    )

    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {SVG_WIDTH} {svg_height}" role="img" aria-label="Flight contribution map showing full GitHub contribution history as a flight journey">
  <defs>
    <linearGradient id="fm-bg" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:#0a0e27;stop-opacity:1" />
      <stop offset="100%" style="stop-color:#111633;stop-opacity:1" />
    </linearGradient>
    <linearGradient id="fm-path" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" style="stop-color:#00d4ff;stop-opacity:0.05" />
      <stop offset="30%" style="stop-color:#00d4ff;stop-opacity:0.4" />
      <stop offset="70%" style="stop-color:#7b61ff;stop-opacity:0.5" />
      <stop offset="100%" style="stop-color:#00d4ff;stop-opacity:0.3" />
    </linearGradient>
    <filter id="airplane-glow">
      <feGaussianBlur stdDeviation="3" result="blur" />
      <feMerge>
        <feMergeNode in="blur" />
        <feMergeNode in="SourceGraphic" />
      </feMerge>
    </filter>
  </defs>

  <!-- Background -->
  <rect width="{SVG_WIDTH}" height="{svg_height}" fill="url(#fm-bg)" rx="8" />

  <!-- Month labels -->
  <g font-family="\'Segoe UI\', system-ui, sans-serif" font-size="10" fill="#3a4060" text-anchor="middle">
{chr(10).join(month_labels)}
  </g>

  <!-- Day labels -->
  <g font-family="\'Segoe UI\', system-ui, sans-serif" font-size="8" fill="#2a3050" text-anchor="end">
{chr(10).join(day_labels)}
  </g>

  <!-- Contribution grid -->
  <g id="contribution-grid">
{chr(10).join(grid_cells)}
  </g>

  <!-- Flight path overlay -->
  <path d="{flight_path}"
        stroke="url(#fm-path)" stroke-width="2" fill="none" opacity="0.5"
        stroke-dasharray="6,4" />

  <!-- Secondary trail -->
  <path d="{flight_path}"
        stroke="#00d4ff" stroke-width="0.5" fill="none" opacity="0.12" />

  <!-- Airplane at latest contribution -->
  <g transform="translate({plane_x + 10}, {plane_y - 5}) rotate(-5)" filter="url(#airplane-glow)">
    <path d="M -10,0 L -3,-1.5 L 7,-5 L 10,-1.5 L 10,1.5 L 7,5 L -3,1.5 L -10,0 Z
             M -1.5,-1.5 L -1.5,-7 L 0,-9 L 1.5,-7 L 1.5,-1.5
             M 3.5,-5 L 5,-10 L 7,-10 L 5,-5
             M 3.5,5 L 5,10 L 7,10 L 5,5"
          fill="#00d4ff" opacity="0.9" />
  </g>

  <!-- Activity summary -->
  <g transform="translate({GRID_X_START}, {svg_height - 35})" font-family="\'Segoe UI\', system-ui, sans-serif">
    <text font-size="10" fill="#5a6380" letter-spacing="1">CONTRIBUTION HISTORY</text>
    <g transform="translate(0, 18)">
      <rect width="8" height="8" rx="1.5" fill="{COLOR_EMPTY}" opacity="0.6"/>
      <rect x="14" width="8" height="8" rx="1.5" fill="{COLOR_LOW}" opacity="0.7"/>
      <rect x="28" width="8" height="8" rx="1.5" fill="{COLOR_MEDIUM}" opacity="0.8"/>
      <rect x="42" width="8" height="8" rx="1.5" fill="{COLOR_HIGH}" opacity="0.7"/>
      <rect x="56" width="8" height="8" rx="1.5" fill="{COLOR_PEAK}" opacity="0.6"/>
      <text x="72" y="8" font-size="9" fill="#3a4060">Less</text>
      <text x="105" y="8" font-size="9" fill="#3a4060">More</text>
    </g>
  </g>

  <!-- Stats -->
  <g transform="translate({SVG_WIDTH - 20}, {svg_height - 35})" font-family="\'Segoe UI\', system-ui, sans-serif" text-anchor="end">
    <text font-size="10" fill="#5a6380" letter-spacing="1">{total} CONTRIBUTIONS</text>
    <text x="0" y="18" font-size="10" fill="#5a6380" letter-spacing="1">{active_days} ACTIVE DAYS</text>
    <text x="0" y="36" font-size="10" fill="#5a6380" letter-spacing="1">{num_weeks} WEEKS</text>
  </g>

  <!-- Bottom accent -->
  <rect x="0" y="{svg_height - 8}" width="{SVG_WIDTH}" height="2" rx="1" fill="url(#fm-path)" opacity="0.2" />
</svg>'''

    return svg


def main():
    parser = argparse.ArgumentParser(description="Generate flight map SVG from contribution data")
    parser.add_argument("--input", default="data/contributions.json",
                        help="Path to contributions JSON")
    parser.add_argument("--output", default="assets/flight-map.svg",
                        help="Output SVG path")
    args = parser.parse_args()

    print(f"Loading contribution data from {args.input}...")
    data = load_contributions(args.input)
    records = data["records"]

    print(f"  Records: {len(records)}")
    print(f"  Date range: {data.get('first_date', '?')} to {data.get('last_date', '?')}")
    print(f"  Total contributions: {data.get('total_contributions', '?')}")

    print("Building grid...")
    num_weeks, first_sunday, date_map, max_count, total, active_days = compute_grid(records)
    print(f"  Weeks: {num_weeks}")
    print(f"  Max daily count: {max_count}")

    print("Generating SVG...")
    svg = generate_svg(date_map, num_weeks, first_sunday, max_count, total, active_days)

    # Ensure output directory exists
    output_dir = os.path.dirname(args.output)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    with open(args.output, "w", encoding="utf-8") as f:
        f.write(svg)

    size = os.path.getsize(args.output)
    print(f"  Written to {args.output} ({size} bytes)")
    print("Done!")


if __name__ == "__main__":
    main()
