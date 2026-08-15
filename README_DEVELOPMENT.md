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
├── data/
│   └── contributions.json             # Full historical contribution data (auto-generated)
├── scripts/
│   ├── fetch_contributions.py         # Fetches full history via GitHub GraphQL API
│   ├── generate_flight_map.py         # Generates flight-map.svg from contributions.json
│   └── generate_stats.py              # Fetches and caches GitHub statistics
├── .github/
│   └── workflows/
│       └── update-profile.yml         # Automated weekly update workflow
└── README_DEVELOPMENT.md              # This file
```

## How Contribution Data is Generated

### Data Pipeline

```
GitHub GraphQL API
       │
       ▼
fetch_contributions.py  ──►  data/contributions.json
                                      │
                                      ▼
generate_flight_map.py  ──►  assets/flight-map.svg
```

1. **`fetch_contributions.py`** queries the GitHub GraphQL API for the user's full `contributionCalendar`
2. This returns the **complete contribution history** (every day since first contribution)
3. Results are stored in **`data/contributions.json`** as the single source of truth
4. **`generate_flight_map.py`** reads `data/contributions.json` and generates the SVG
5. The SVG is regenerated from scratch each time (no incremental updates)

### Data Source

- **API**: GitHub GraphQL API (`https://api.github.com/graphql`)
- **Query field**: `user.contributionCalendar`
- **Coverage**: Full history since the user's first contribution
- **Authentication**: Required (uses `GITHUB_TOKEN` in workflow)

### Data Format (`data/contributions.json`)

```json
{
  "username": "aryan-sonsurkar",
  "fetched_at": "2026-08-15T12:00:00+00:00",
  "total_contributions": 420,
  "active_days": 150,
  "first_date": "2025-12-12",
  "last_date": "2026-08-15",
  "records": [
    {
      "date": "2025-12-12",
      "contribution_count": 2,
      "intensity": 2,
      "weekday": 6
    },
    ...
  ]
}
```

Each record contains:
- `date`: ISO date string (YYYY-MM-DD)
- `contribution_count`: Number of contributions that day
- `intensity`: Bucket 0-4 for color mapping
- `weekday`: 0=Sunday, 1=Monday, ..., 6=Saturday (GitHub convention)

### Validation Rules

Before committing, the workflow validates:
1. Records are non-empty
2. Dates are valid ISO format
3. Dates are in chronological order
4. No duplicate dates
5. All contribution counts are non-negative
6. Generated SVG is valid XML
7. Historical data has not been accidentally discarded

### Color Mapping

| Intensity | Contributions | Color | Hex |
|-----------|--------------|-------|-----|
| 0 | 0 | Empty | `#0a0e27` |
| 1 | 1-2 | Low | `#0e2a3d` |
| 2 | 3-5 | Medium | `#0d4a5e` |
| 3 | 6-9 | High | `#00d4ff` |
| 4 | 10+ | Peak | `#7b61ff` |

## How the Airplane Position is Calculated

The airplane is positioned at the **latest date with a non-zero contribution count**.

Calculation:
1. Scan all records for the most recent date where `contribution_count > 0`
2. Compute the week index: `(date - grid_start_sunday).days // 7`
3. Compute the day row: `(weekday + 1) % 7` (converts Mon=0..Sun=6 to Sun=0..Sat=6)
4. Map to pixel coordinates using the cell pitch

The airplane position updates naturally as new contributions appear. The historical grid remains intact; only the airplane's endpoint moves.

## How to Run Locally

### Prerequisites

- Python 3.8+
- A GitHub personal access token (for GraphQL access)

### Step 1: Fetch Contribution History

```bash
export GITHUB_TOKEN=ghp_your_token_here
python scripts/fetch_contributions.py --user aryan-sonsurkar --output data/contributions.json
```

### Step 2: Generate Flight Map

```bash
python scripts/generate_flight_map.py --input data/contributions.json --output assets/flight-map.svg
```

### Step 3: Open in Browser

Open `assets/flight-map.svg` directly in a browser to preview.

### Manual Update (Any Time)

```bash
# Full refresh - re-fetches all history and regenerates
export GITHUB_TOKEN=ghp_your_token_here
python scripts/fetch_contributions.py --user aryan-sonsurkar
python scripts/generate_flight_map.py
```

## How GitHub Actions Updates the Profile

### Workflow: `update-profile.yml`

- **Schedule**: Weekly on Sunday at 00:00 UTC
- **Manual**: Supports `workflow_dispatch` for on-demand updates
- **Steps**:
  1. Checkout repository
  2. Set up Python 3.11
  3. Fetch **full** contribution history via GraphQL
  4. Validate contribution data integrity
  5. Generate flight map SVG from data
  6. Validate SVG is well-formed XML
  7. Check if anything actually changed (`git diff`)
  8. Commit and push **only if** files changed

### Key Behavior

- **Full rebuild each time**: Does not append to existing data. Reconstructs the complete historical map from the API response.
- **No unnecessary commits**: Checks `git diff --cached --quiet` before committing.
- **No infinite loops**: Does not trigger on push events. Only runs on schedule and manual dispatch.
- **Deterministic output**: Same input data produces identical SVG (verified with MD5 hash comparison).

### Preventing Infinite Loops

| Trigger | Runs workflow? | Notes |
|---------|---------------|-------|
| `schedule` (cron) | Yes | Weekly on Sunday 00:00 UTC |
| `workflow_dispatch` | Yes | Manual trigger |
| Push to main | **No** | Workflow commits are ignored |
| Pull request | **No** | Not configured |

### Secrets Required

| Secret | Purpose | Required |
|--------|---------|----------|
| `GITHUB_TOKEN` | GraphQL API access | Auto-provided by GitHub |

No manual secrets configuration is needed.

### Failure Behavior

If the API fails:
- The workflow step fails with an error message
- The existing `data/contributions.json` and `assets/flight-map.svg` remain unchanged
- No empty/zeroed data is committed

## How to Modify Colors

### Flight Map Colors

Edit the color constants at the top of `scripts/generate_flight_map.py`:

```python
COLOR_EMPTY = "#0a0e27"    # Empty cell
COLOR_LOW = "#0e2a3d"      # Low activity
COLOR_MEDIUM = "#0d4a5e"   # Medium activity
COLOR_HIGH = "#00d4ff"     # High activity
COLOR_PEAK = "#7b61ff"     # Peak activity
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

1. **GraphQL over REST**: The contribution calendar API provides full history in one query; REST events API only returns 90 days
2. **Separate fetch and generate**: Decouples data acquisition from visualization, enabling offline SVG regeneration
3. **Committed data file**: `data/contributions.json` is committed so the full history is preserved and the SVG can be regenerated without API access
4. **Full rebuild**: Each run reconstructs the entire map from scratch, preventing stale data accumulation
5. **Static SVGs over GIFs**: SVGs are smaller, scalable, and maintain quality
6. **No CSS animations**: GitHub strips them; static design is more reliable
7. **Dark theme**: Aviation/space aesthetic for professionalism
8. **Curated projects**: Only meaningful work is highlighted
9. **Real data**: Contribution map uses actual GitHub API data, never fabricated
10. **Automated updates**: Weekly workflow keeps the profile current without manual effort
