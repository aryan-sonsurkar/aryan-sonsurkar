#!/usr/bin/env python3
"""
Flight Map Generator for GitHub Profile README.

Fetches real GitHub contribution data and generates an SVG flight map
where contribution activity forms the terrain and an airplane travels
across the timeline.

Usage:
    python generate_flight_map.py [--user USERNAME] [--token TOKEN] [--output PATH]

Environment Variables:
    GITHUB_USERNAME  - GitHub username (default: aryan-sonsurkar)
    GITHUB_TOKEN     - GitHub API token (optional, for higher rate limits)
"""

import argparse
import json
import os
import sys
import urllib.request
import urllib.error
from datetime import datetime, timedelta
from typing import List, Dict, Tuple


def fetch_contribution_data(username: str, token: str = None) -> List[Dict]:
    """
    Fetch contribution data from GitHub API.
    Returns a list of contribution events with dates.
    """
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "profile-readme-generator"
    }
    if token:
        headers["Authorization"] = f"token {token}"

    events = []
    page = 1
    max_pages = 10

    while page <= max_pages:
        url = f"https://api.github.com/users/{username}/events/public?per_page=100&page={page}"
        req = urllib.request.Request(url, headers=headers)

        try:
            with urllib.request.urlopen(req) as response:
                data = json.loads(response.read().decode())
                if not data:
                    break
                events.extend(data)
                page += 1
        except urllib.error.HTTPError as e:
            print(f"Warning: HTTP {e.code} fetching events page {page}", file=sys.stderr)
            break
        except urllib.error.URLError as e:
            print(f"Warning: Network error: {e.reason}", file=sys.stderr)
            break

    return events


def fetch_repo_languages(username: str, token: str = None) -> Dict[str, int]:
    """
    Fetch language distribution across all repositories.
    Returns dict of language -> byte count.
    """
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "profile-readme-generator"
    }
    if token:
        headers["Authorization"] = f"token {token}"

    # Get all repos
    repos_url = f"https://api.github.com/users/{username}/repos?per_page=100&type=public"
    req = urllib.request.Request(repos_url, headers=headers)

    languages = {}
    try:
        with urllib.request.urlopen(req) as response:
            repos = json.loads(response.read().decode())

            for repo in repos:
                if repo.get("fork"):
                    continue
                lang_url = repo.get("languages_url")
                if lang_url:
                    lang_req = urllib.request.Request(lang_url, headers=headers)
                    try:
                        with urllib.request.urlopen(lang_req) as lang_resp:
                            repo_langs = json.loads(lang_resp.read().decode())
                            for lang, count in repo_langs.items():
                                languages[lang] = languages.get(lang, 0) + count
                    except Exception:
                        pass
    except Exception as e:
        print(f"Warning: Error fetching repos: {e}", file=sys.stderr)

    return languages


def process_contributions(events: List[Dict], weeks_back: int = 52) -> List[List[int]]:
    """
    Process raw events into a 7x52 grid of daily contribution counts.
    Grid[day][week] where day 0 = Sunday, week 0 = oldest.
    """
    today = datetime.utcnow().date()
    start_date = today - timedelta(weeks=weeks_back)

    # Initialize grid
    grid = [[0 for _ in range(weeks_back)] for _ in range(7)]

    # Count contributions per day
    daily_counts = {}
    for event in events:
        date_str = event.get("created_at", "")
        if not date_str:
            continue
        try:
            date = datetime.fromisoformat(date_str.replace("Z", "+00:00")).date()
        except ValueError:
            continue

        if date < start_date:
            continue

        daily_counts[date] = daily_counts.get(date, 0) + 1

    # Map to grid
    for date, count in daily_counts.items():
        days_since_start = (date - start_date).days
        week = days_since_start // 7
        day = date.weekday()  # Monday=0, Sunday=6
        # Convert to Sunday=0 convention for GitHub-style grid
        day = (day + 1) % 7

        if 0 <= week < weeks_back and 0 <= day < 7:
            grid[day][week] = count

    return grid


def get_color(count: int, max_count: int) -> str:
    """Map contribution count to color."""
    if count == 0:
        return "#0a0e27"
    if max_count == 0:
        return "#0a0e27"

    ratio = count / max_count

    if ratio < 0.25:
        return "#0e2a3d"
    elif ratio < 0.5:
        return "#0d4a5e"
    elif ratio < 0.75:
        return "#00d4ff"
    else:
        return "#7b61ff"


def generate_svg(grid: List[List[int]], username: str) -> str:
    """Generate the flight map SVG from the contribution grid."""
    weeks = len(grid[0]) if grid else 52
    days = len(grid)

    # Find max contribution for color scaling
    max_count = max(max(row) for row in grid) if grid else 1
    total_contributions = sum(sum(row) for row in grid)

    # Calculate cell positions
    start_x = 65
    start_y = 42
    cell_size = 11
    gap = 4
    pitch = cell_size + gap

    # Month labels
    today = datetime.utcnow().date()
    months = []
    for w in range(weeks):
        week_date = today - timedelta(weeks=weeks - 1 - w)
        month_name = week_date.strftime("%b")
        if w == 0 or month_name != months[-1][1] if months else True:
            months.append((w, month_name))

    # Generate grid cells
    grid_cells = []
    for day in range(days):
        for week in range(weeks):
            x = start_x + week * pitch
            y = start_y + day * pitch
            count = grid[day][week]
            color = get_color(count, max_count)
            opacity = "0.6" if count == 0 else "0.8"
            grid_cells.append(
                f'    <rect x="{x}" y="{y}" width="{cell_size}" height="{cell_size}" '
                f'rx="2" fill="{color}" opacity="{opacity}"/>'
            )

    # Month label elements
    month_labels = []
    for week_idx, month_name in months:
        x = start_x + week_idx * pitch + cell_size // 2
        month_labels.append(
            f'    <text x="{x}" y="28" text-anchor="middle" '
            f'font-family="\'Segoe UI\', system-ui, sans-serif" '
            f'font-size="10" fill="#3a4060">{month_name}</text>'
        )

    # Day labels
    day_names = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
    day_labels = []
    for day in range(days):
        y = start_y + day * pitch + cell_size - 1
        day_labels.append(
            f'    <text x="55" y="{y}" text-anchor="end" '
            f'font-family="\'Segoe UI\', system-ui, sans-serif" '
            f'font-size="8" fill="#2a3050">{day_names[day]}</text>'
        )

    # Flight path (bezier curve across the grid)
    path_end_x = start_x + (weeks - 1) * pitch
    mid_y = start_y + 3 * pitch  # Center vertically

    # Calculate airplane position (latest active week)
    airplane_week = weeks - 1
    airplane_day = 0
    for w in range(weeks - 1, -1, -1):
        for d in range(days):
            if grid[d][w] > 0:
                airplane_week = w
                airplane_day = d
                break
        else:
            continue
        break

    airplane_x = start_x + airplane_week * pitch + cell_size // 2
    airplane_y = start_y + airplane_day * pitch + cell_size // 2

    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 900 220" role="img" aria-label="Flight contribution map showing GitHub activity as a flight journey across weeks">
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
  <rect width="900" height="220" fill="url(#fm-bg)" rx="8" />

  <!-- Month labels -->
  <g font-family="'Segoe UI', system-ui, sans-serif" font-size="10" fill="#3a4060" text-anchor="middle">
{chr(10).join(month_labels)}
  </g>

  <!-- Day labels -->
  <g font-family="'Segoe UI', system-ui, sans-serif" font-size="8" fill="#2a3050" text-anchor="end">
{chr(10).join(day_labels)}
  </g>

  <!-- Contribution grid -->
  <g id="contribution-grid">
{chr(10).join(grid_cells)}
  </g>

  <!-- Flight path overlay -->
  <path d="M {start_x},{mid_y} C {start_x + 100},{mid_y - 15} {start_x + 200},{mid_y + 10} {start_x + 300},{mid_y - 5} S {start_x + 500},{mid_y + 5} {path_end_x},{mid_y - 10}"
        stroke="url(#fm-path)" stroke-width="2" fill="none" opacity="0.5"
        stroke-dasharray="6,4" />

  <!-- Airplane at current position -->
  <g transform="translate({airplane_x + 10}, {airplane_y - 5}) rotate(-5)" filter="url(#airplane-glow)">
    <path d="M -10,0 L -3,-1.5 L 7,-5 L 10,-1.5 L 10,1.5 L 7,5 L -3,1.5 L -10,0 Z
             M -1.5,-1.5 L -1.5,-7 L 0,-9 L 1.5,-7 L 1.5,-1.5
             M 3.5,-5 L 5,-10 L 7,-10 L 5,-5
             M 3.5,5 L 5,10 L 7,10 L 5,5"
          fill="#00d4ff" opacity="0.9" />
  </g>

  <!-- Activity summary -->
  <g transform="translate({start_x}, 165)" font-family="'Segoe UI', system-ui, sans-serif">
    <text font-size="10" fill="#5a6380" letter-spacing="1">CONTRIBUTION ACTIVITY</text>
    <g transform="translate(0, 18)">
      <rect width="8" height="8" rx="1.5" fill="#0a0e27" opacity="0.6"/>
      <rect x="14" width="8" height="8" rx="1.5" fill="#0e2a3d" opacity="0.7"/>
      <rect x="28" width="8" height="8" rx="1.5" fill="#0d4a5e" opacity="0.8"/>
      <rect x="42" width="8" height="8" rx="1.5" fill="#00d4ff" opacity="0.7"/>
      <rect x="56" width="8" height="8" rx="1.5" fill="#7b61ff" opacity="0.6"/>
      <text x="72" y="8" font-size="9" fill="#3a4060">Less</text>
      <text x="105" y="8" font-size="9" fill="#3a4060">More</text>
    </g>
  </g>

  <!-- Stats -->
  <g transform="translate(700, 165)" font-family="'Segoe UI', system-ui, sans-serif" text-anchor="end">
    <text font-size="10" fill="#5a6380" letter-spacing="1">{total_contributions} CONTRIBUTIONS</text>
  </g>

  <!-- Bottom accent -->
  <rect x="0" y="212" width="900" height="2" rx="1" fill="url(#fm-path)" opacity="0.2" />
</svg>'''

    return svg


def main():
    parser = argparse.ArgumentParser(description="Generate flight map SVG from GitHub data")
    parser.add_argument("--user", default=os.environ.get("GITHUB_USERNAME", "aryan-sonsurkar"),
                        help="GitHub username")
    parser.add_argument("--token", default=os.environ.get("GITHUB_TOKEN"),
                        help="GitHub API token")
    parser.add_argument("--output", default="assets/flight-map.svg",
                        help="Output SVG path")
    parser.add_argument("--weeks", type=int, default=52,
                        help="Number of weeks to display")
    args = parser.parse_args()

    print(f"Fetching contribution data for {args.user}...")
    events = fetch_contribution_data(args.user, args.token)
    print(f"  Found {len(events)} events")

    print("Processing contributions into grid...")
    grid = process_contributions(events, args.weeks)
    total = sum(sum(row) for row in grid)
    print(f"  Total contributions: {total}")

    print("Generating SVG...")
    svg = generate_svg(grid, args.user)

    # Ensure output directory exists
    output_dir = os.path.dirname(args.output)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    with open(args.output, "w", encoding="utf-8") as f:
        f.write(svg)

    print(f"  Written to {args.output}")
    print("Done!")


if __name__ == "__main__":
    main()
