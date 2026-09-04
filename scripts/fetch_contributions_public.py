#!/usr/bin/env python3
"""
Fetch GitHub contribution data via the PUBLIC profile page (no token required).

Scrapes https://github.com/users/<username>/contributions which embeds
per-day `data-date`, `data-level` and the exact count in each day's tooltip,
e.g. `<td data-date="2026-08-30" data-level="4">` +
`<tool-tip>13 contributions on August 30th.</tool-tip>`.

Produces data/contributions.json in the SAME schema as
fetch_contributions.py (GraphQL), so all downstream generators
(generate_flight_map.py, generate_flight_animation.py) work unchanged.

Why this exists: the GraphQL `contributionCalendar` API needs a
GITHUB_TOKEN, which is auto-provided in GitHub Actions but usually absent
on a local machine. The public page needs no auth and covers the trailing
12 months, which contains this account's full history.

Usage:
    python scripts/fetch_contributions_public.py [--user USERNAME] [--output PATH]
"""

import argparse
import json
import os
import re
import sys
import urllib.request
import urllib.error
from datetime import datetime, timezone

DAY_RE = re.compile(r'data-date="(\d{4}-\d{2}-\d{2})"[^>]*?data-level="(\d)"')
TIP_RE = re.compile(r"<tool-tip[^>]*>([^<]+)</tool-tip>")
TIP_OK_RE = re.compile(r"^(No contributions|\d+\s+contribution)")
TOTAL_RE = re.compile(r"(\d[\d,]*)\s+contributions\s+in the last year")


def parse_count(text: str) -> int:
    text = text.strip()
    if text.startswith("No contributions"):
        return 0
    m = re.match(r"(\d+)\s+contribution", text)
    if not m:
        raise ValueError(f"Unparseable tooltip: {text!r}")
    return int(m.group(1))


def intensity(count: int) -> int:
    # Same buckets as fetch_contributions.py (GraphQL path)
    if count == 0:
        return 0
    if count <= 2:
        return 1
    if count <= 5:
        return 2
    if count <= 9:
        return 3
    return 4


def fetch_page(username: str) -> str:
    url = f"https://github.com/users/{username}/contributions"
    req = urllib.request.Request(
        url, headers={"User-Agent": "profile-readme-generator"}
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        print(f"HTTP error {e.code} fetching {url}", file=sys.stderr)
        sys.exit(1)
    except urllib.error.URLError as e:
        print(f"Network error: {e.reason}", file=sys.stderr)
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Fetch GitHub contributions via public page (no token)"
    )
    parser.add_argument(
        "--user",
        default=os.environ.get("GITHUB_USERNAME", "aryan-sonsurkar"),
        help="GitHub username",
    )
    parser.add_argument("--output", default="data/contributions.json")
    args = parser.parse_args()

    print(f"Fetching public contribution page for {args.user}...")
    html = fetch_page(args.user)

    days = DAY_RE.findall(html)
    tips = [t for t in TIP_RE.findall(html) if TIP_OK_RE.match(t.strip())]
    print(f"  Day cells: {len(days)}, day tooltips: {len(tips)}")

    if not days:
        print("ERROR: no contribution cells found - page layout changed?",
              file=sys.stderr)
        sys.exit(1)
    if len(days) != len(tips):
        print(f"ERROR: cells ({len(days)}) != tooltips ({len(tips)}) - "
              f"refusing to guess pairings", file=sys.stderr)
        sys.exit(1)

    records = []
    for (date_str, _level), tip in zip(days, tips):
        # Validate ISO date and derive GitHub weekday (0=Sunday)
        try:
            dt = datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            print(f"ERROR: invalid date {date_str}", file=sys.stderr)
            sys.exit(1)
        count = parse_count(tip)
        if count < 0:
            print(f"ERROR: negative count on {date_str}", file=sys.stderr)
            sys.exit(1)
        records.append({
            "date": date_str,
            "contribution_count": count,
            "intensity": intensity(count),
            "weekday": (dt.weekday() + 1) % 7,
        })

    # Table is weekday-major (one <tr> per weekday), so sort chronologically.
    # Pairing is safe: each record already carries its own date + count.
    records.sort(key=lambda r: r["date"])

    dates = [r["date"] for r in records]
    if dates != sorted(dates):
        print("ERROR: dates not in chronological order", file=sys.stderr)
        sys.exit(1)
    if len(dates) != len(set(dates)):
        print("ERROR: duplicate dates found", file=sys.stderr)
        sys.exit(1)

    total = sum(r["contribution_count"] for r in records)
    active = sum(1 for r in records if r["contribution_count"] > 0)

    # Cross-check against the page's own reported total
    m = TOTAL_RE.search(html)
    if m:
        reported = int(m.group(1).replace(",", ""))
        print(f"  Page reports {reported} contributions, parsed sum {total}")
        if reported != total:
            print("  WARNING: parsed sum differs from reported total",
                  file=sys.stderr)
    else:
        print("  WARNING: could not find reported total on page",
              file=sys.stderr)

    output = {
        "username": args.user,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "total_contributions": total,
        "active_days": active,
        "first_date": records[0]["date"],
        "last_date": records[-1]["date"],
        "records": records,
    }

    out_dir = os.path.dirname(args.output)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)

    print(f"  Range: {records[0]['date']} to {records[-1]['date']}")
    print(f"  Days: {len(records)}, active: {active}, total: {total}")
    print(f"  Written to {args.output}")
    print("Done!")


if __name__ == "__main__":
    main()
