# Profile README - Development Guide

This document explains the architecture, automation, and customization of the GitHub profile README system.

## Architecture

```
aryan-sonsurkar/
├── README.md                          # Profile README (rendered on GitHub)
├── assets/
│   ├── hero.svg                       # Animated hero banner
│   ├── flight-map.svg                 # Contribution visualization (auto-generated)
│   ├── project-map.svg                # Project constellation map
│   └── footer.svg                     # Footer decoration
├── scripts/
│   ├── generate_flight_map.py         # Generates flight-map.svg from GitHub API
│   └── generate_stats.py              # Fetches and caches GitHub statistics
├── .github/
│   └── workflows/
│       └── update-profile.yml         # Automated weekly update workflow
└── README_DEVELOPMENT.md              # This file
```

## How Contribution Data is Generated

### Data Flow

1. **GitHub Actions** triggers weekly (Sunday 00:00 UTC) or on manual dispatch
2. **`generate_flight_map.py`** fetches public events from `https://api.github.com/users/{username}/events/public`
3. Events are processed into a 7x52 grid (days x weeks)
4. Each cell's color intensity maps to contribution count
5. The SVG is regenerated with the real data
6. **`generate_stats.py`** fetches repository data and language distribution
7. Changes are committed only if the generated content actually changed

### Color Mapping

| Contributions | Color | Hex |
|--------------|-------|-----|
| 0 | Empty | `#0a0e27` |
| Low | Dim | `#0e2a3d` |
| Medium | Moderate | `#0d4a5e` |
| High | Bright | `#00d4ff` |
| Peak | Accent | `#7b61ff` |

### Rate Limiting

- Unauthenticated: 60 requests/hour
- With `GITHUB_TOKEN`: 5,000 requests/hour
- The workflow uses the built-in `GITHUB_TOKEN` automatically

## How the Airplane Animation Works

The airplane is a static SVG element positioned at the latest active week in the contribution grid. Since GitHub's README renderer does not support CSS animations reliably, the airplane is rendered as a static element.

The flight path is a bezier curve that overlays the contribution grid, creating the visual impression of a journey across the timeline.

**Why no animation?** GitHub strips `<style>` tags and `<script>` from SVGs rendered in READMEs. CSS animations via `@keyframes` are also unreliable. Static SVGs with strong visual design are more dependable.

## How Project Data is Sourced

Project information is **hardcoded** in `README.md` because:

1. Project descriptions require human judgment
2. Status labels (BUILDING, ACTIVE, etc.) are manual annotations
3. The number of highlighted projects should stay curated

To add/remove projects, edit the `Current Missions` and `Project Constellation` sections in `README.md`.

## How GitHub Actions Updates the Profile

### Workflow: `update-profile.yml`

- **Trigger**: Weekly cron (Sunday 00:00 UTC) + manual dispatch
- **Steps**:
  1. Checkout repository
  2. Set up Python 3.11
  3. Run `generate_flight_map.py` with `GITHUB_TOKEN`
  4. Run `generate_stats.py` with `GITHUB_TOKEN`
  5. Validate generated SVGs (XML parsing)
  6. Check for actual changes via `git diff`
  7. Commit and push only if content changed

### Preventing Infinite Loops

- The workflow commits with author `github-actions[bot]`
- It only runs on `schedule` and `workflow_dispatch` triggers
- It does NOT trigger on push events (no `on: push`)
- It checks `git diff --cached --quiet` before committing

### Secrets Required

| Secret | Purpose | Required |
|--------|---------|----------|
| `GITHUB_TOKEN` | API access for events/repos | Auto-provided |

No manual secrets configuration is needed. `GITHUB_TOKEN` is provided automatically by GitHub Actions.

## How to Modify Colors

### Flight Map Colors

Edit the color constants in `scripts/generate_flight_map.py`:

```python
# In get_color() function:
if count == 0:
    return "#0a0e27"    # Empty cell
elif ratio < 0.25:
    return "#0e2a3d"    # Low activity
elif ratio < 0.5:
    return "#0d4a5e"    # Medium activity
elif ratio < 0.75:
    return "#00d4ff"    # High activity
else:
    return "#7b61ff"    # Peak activity
```

### Theme Colors

| Element | Color | Usage |
|---------|-------|-------|
| Background | `#0a0e27` | Dark space theme |
| Primary accent | `#00d4ff` | Cyan - flight/navigation |
| Secondary accent | `#7b61ff` | Purple - highlights |
| Text primary | `#e0e6ff` | Light text |
| Text secondary | `#5a6380` | Muted text |
| Text tertiary | `#3a4060` | Very muted |

## How to Add/Remove Projects

### Current Missions Section

Edit the HTML table in `README.md` under `## Current Missions`:

```html
<td width="50%" valign="top">
  <h3><a href="https://github.com/aryan-sonsurkar/repo-name">Project Name</a></h3>
  <p>Short description</p>
  <code>Language</code> · ⭐ Stars
  <br/><br/>
  <strong>Status:</strong> <code>STATUS</code>
</td>
```

Status options: `BUILDING`, `ACTIVE`, `EXPERIMENTING`, `EXPLORING`

### Project Constellation Section

Edit the table under `## Project Constellation` similarly.

## How to Run Generation Locally

### Prerequisites

- Python 3.8+
- Internet access

### Steps

```bash
# Generate flight map
python scripts/generate_flight_map.py --user aryan-sonsurkar --output assets/flight-map.svg

# Generate stats
python scripts/generate_stats.py --user aryan-sonsurkar --output assets/stats.json

# With authentication (higher rate limits)
export GITHUB_TOKEN=your_token_here
python scripts/generate_flight_map.py --output assets/flight-map.svg
```

### Local Preview

Open `README.md` in a Markdown preview tool, or:

```bash
# Using Python's built-in server
python -m http.server 8000
# Then open http://localhost:8000 and view README.md
```

SVG files can be opened directly in any browser.

## Validation

Run validation manually:

```bash
# Validate SVGs
python -c "
import xml.etree.ElementTree as ET
for f in ['assets/hero.svg', 'assets/flight-map.svg', 'assets/project-map.svg', 'assets/footer.svg']:
    try:
        ET.parse(f)
        print(f'OK: {f}')
    except ET.ParseError as e:
        print(f'FAIL: {f}: {e}')
"
```

## GitHub Limitations

| Feature | Supported | Notes |
|---------|-----------|-------|
| Inline SVG | Yes | Renders in README |
| SVG animation | Unreliable | CSS animations stripped |
| JavaScript | No | Not executed in README |
| External images | Yes | Via `img src` URLs |
| HTML tables | Yes | Supported in Markdown |
| Shields.io badges | Yes | Dynamic badge images |
| Local file references | Yes | Relative paths work |

## Design Decisions

1. **Static SVGs over GIFs**: SVGs are smaller, scalable, and maintain quality
2. **No CSS animations**: GitHub's renderer strips them; static design is more reliable
3. **Dark theme**: Aviation/space aesthetic for professionalism
4. **Curated projects**: Only meaningful work is highlighted, not every repository
5. **Real data**: Contribution map uses actual GitHub API data, never fabricated
6. **Automated updates**: Weekly workflow keeps the profile current without manual effort
