#!/usr/bin/env python3
"""
Stats Cards Generator for GitHub Profile README.

Reads assets/stats.json and renders two static SVG cards:
  - assets/stats-card.svg      (GitHub Stats: repos, stars, followers, following)
  - assets/languages-card.svg  (Top Languages with proportional bars)

The SVGs are committed to the repository, so they are served directly by
GitHub and always render - no third-party service required.

Usage:
    python generate_stats_cards.py [--input PATH] [--output-dir DIR]
"""

import argparse
import json
import os
import sys
import xml.dom.minidom

FONT = "'Segoe UI', system-ui, -apple-system, sans-serif"

CARD_WIDTH = 460

BG_TOP = "#0a0e27"
BG_BOTTOM = "#1a1a3e"
CYAN = "#00d4ff"
PURPLE = "#7b61ff"
TEXT = "#e0e6ff"
MUTED = "#8892b0"
FAINT = "#5a6380"
TRACK = "#141832"

DEFAULT_LANG_COLORS = {
    "TypeScript": "#3178c6",
    "Python": "#3572A5",
    "JavaScript": "#f1e05a",
    "C": "#555555",
    "C++": "#f34b7d",
    "HTML": "#e34c26",
    "CSS": "#563d7c",
    "Shell": "#89e051",
    "Java": "#b07219",
    "PLpgSQL": "#336791",
    "Go": "#00ADD8",
    "Rust": "#dea584",
    "Ruby": "#701516",
}


def svg_header(title, height):
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" '
        'role="img" aria-label="{t}">\n'
        "  <defs>\n"
        '    <linearGradient id="bg" x1="0%" y1="0%" x2="100%" y2="100%">\n'
        f'      <stop offset="0%" style="stop-color:{BG_TOP};stop-opacity:1" />\n'
        f'      <stop offset="100%" style="stop-color:{BG_BOTTOM};stop-opacity:1" />\n'
        "    </linearGradient>\n"
        "  </defs>\n"
        f'  <rect width="{CARD_WIDTH}" height="{height}" fill="url(#bg)" rx="8" />\n'
    ).format(w=CARD_WIDTH, h=height, t=title)


def card_title(title, color):
    return (
        f'  <text x="24" y="38" font-family="{FONT}" font-size="16" font-weight="600" '
        f'fill="{color}" letter-spacing="1">{title}</text>\n'
        f'  <line x1="24" y1="50" x2="{CARD_WIDTH - 24}" y2="50" stroke="{FAINT}" '
        'stroke-width="1" opacity="0.5" />\n'
    )


def build_stats_card(stats):
    rows = [
        ("Repositories", stats.get("repos", 0)),
        ("Stars", stats.get("stars", 0)),
        ("Followers", stats.get("followers", 0)),
        ("Following", stats.get("following", 0)),
    ]
    height = 200
    parts = [svg_header("GitHub Stats", height), card_title("GitHub Stats", CYAN)]
    y = 82
    for label, value in rows:
        parts.append(
            f'  <text x="24" y="{y}" font-family="{FONT}" font-size="13" fill="{MUTED}">{label}</text>\n'
        )
        parts.append(
            f'  <text x="{CARD_WIDTH - 24}" y="{y}" text-anchor="end" font-family="{FONT}" '
            f'font-size="14" font-weight="600" fill="{TEXT}">{value}</text>\n'
        )
        y += 32
    parts.append("</svg>\n")
    return "".join(parts)


def build_languages_card(stats):
    langs = stats.get("top_languages", [])
    colors = {**DEFAULT_LANG_COLORS, **stats.get("lang_colors", {})}
    top = langs[:5]
    height = 46 + len(top) * 40
    parts = [svg_header("Top Languages", height), card_title("Top Languages", PURPLE)]
    track_x = 150
    track_w = CARD_WIDTH - track_x - 90
    y = 84
    for name, pct in top:
        color = colors.get(name, "#8892b0")
        fill_w = max(0, round(track_w * pct / 100.0))
        parts.append(
            f'  <text x="24" y="{y}" font-family="{FONT}" font-size="12" fill="{MUTED}">{name}</text>\n'
        )
        parts.append(
            f'  <rect x="{track_x}" y="{y - 8}" width="{track_w}" height="8" rx="4" fill="{TRACK}" />\n'
        )
        parts.append(
            f'  <rect x="{track_x}" y="{y - 8}" width="{fill_w}" height="8" rx="4" fill="{color}" />\n'
        )
        parts.append(
            f'  <text x="{CARD_WIDTH - 24}" y="{y}" text-anchor="end" font-family="{FONT}" '
            f'font-size="12" font-weight="600" fill="{TEXT}">{pct:.1f}%</text>\n'
        )
        y += 40
    parts.append("</svg>\n")
    return "".join(parts)


def validate(svg_text, name):
    try:
        xml.dom.minidom.parseString(svg_text)
    except Exception as e:
        print(f"ERROR: {name} is not valid XML: {e}", file=sys.stderr)
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Generate static stats SVG cards")
    parser.add_argument("--input", default="assets/stats.json")
    parser.add_argument("--output-dir", default="assets")
    args = parser.parse_args()

    with open(args.input, "r", encoding="utf-8") as f:
        stats = json.load(f)

    os.makedirs(args.output_dir, exist_ok=True)

    stats_svg = build_stats_card(stats)
    langs_svg = build_languages_card(stats)

    validate(stats_svg, "stats-card.svg")
    validate(langs_svg, "languages-card.svg")

    stats_path = os.path.join(args.output_dir, "stats-card.svg")
    langs_path = os.path.join(args.output_dir, "languages-card.svg")

    with open(stats_path, "w", encoding="utf-8") as f:
        f.write(stats_svg)
    with open(langs_path, "w", encoding="utf-8") as f:
        f.write(langs_svg)

    print(f"  Written {stats_path}")
    print(f"  Written {langs_path}")
    print("Done!")


if __name__ == "__main__":
    main()
