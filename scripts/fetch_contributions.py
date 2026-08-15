#!/usr/bin/env python3
"""
Fetch full historical GitHub contribution data via GraphQL API.

Produces data/contributions.json with the complete contribution calendar.
This is the single source of truth for the flight map visualization.

Usage:
    python scripts/fetch_contributions.py [--user USERNAME] [--token TOKEN] [--output PATH]

Environment Variables:
    GITHUB_USERNAME  - GitHub username (default: aryan-sonsurkar)
    GITHUB_TOKEN     - GitHub API token (required for GraphQL)
"""

import argparse
import json
import os
import sys
import urllib.request
import urllib.error
from datetime import datetime, timezone


GRAPHQL_QUERY = """
query($username: String!) {
  user(login: $username) {
    contributionCalendar {
      totalContributions
      weeks {
        contributionDays {
          contributionCount
          date
          weekday
        }
      }
    }
  }
}
"""


def fetch_contribution_calendar(username: str, token: str) -> dict:
    """Fetch the full contribution calendar via GitHub GraphQL API."""
    url = "https://api.github.com/graphql"
    payload = json.dumps({
        "query": GRAPHQL_QUERY,
        "variables": {"username": username}
    }).encode("utf-8")

    headers = {
        "Authorization": f"bearer {token}",
        "Content-Type": "application/json",
        "User-Agent": "profile-readme-generator"
    }

    req = urllib.request.Request(url, data=payload, headers=headers)

    try:
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode() if e.fp else ""
        print(f"GraphQL error {e.code}: {body}", file=sys.stderr)
        sys.exit(1)
    except urllib.error.URLError as e:
        print(f"Network error: {e.reason}", file=sys.stderr)
        sys.exit(1)

    if "errors" in data:
        for err in data["errors"]:
            print(f"GraphQL error: {err.get('message', err)}", file=sys.stderr)
        sys.exit(1)

    user = data.get("data", {}).get("user")
    if not user:
        print(f"User '{username}' not found", file=sys.stderr)
        sys.exit(1)

    return user["contributionCalendar"]


def process_calendar(calendar: dict) -> list:
    """Convert GraphQL calendar response into a flat list of daily records."""
    records = []
    total = calendar.get("totalContributions", 0)

    for week in calendar.get("weeks", []):
        for day in week.get("contributionDays", []):
            date_str = day["date"]
            count = day["contributionCount"]
            weekday = day["weekday"]  # 0=Sunday in GitHub's convention

            # Compute intensity bucket (0-4)
            if count == 0:
                intensity = 0
            elif count <= 2:
                intensity = 1
            elif count <= 5:
                intensity = 2
            elif count <= 9:
                intensity = 3
            else:
                intensity = 4

            records.append({
                "date": date_str,
                "contribution_count": count,
                "intensity": intensity,
                "weekday": weekday,
            })

    return records, total


def validate_records(records: list) -> bool:
    """Validate the contribution records."""
    if not records:
        print("ERROR: No contribution records", file=sys.stderr)
        return False

    dates = [r["date"] for r in records]

    # Check chronological order
    if dates != sorted(dates):
        print("ERROR: Dates not in chronological order", file=sys.stderr)
        return False

    # Check no duplicates
    if len(dates) != len(set(dates)):
        print("ERROR: Duplicate dates found", file=sys.stderr)
        return False

    # Check non-negative counts
    for r in records:
        if r["contribution_count"] < 0:
            print(f"ERROR: Negative count on {r['date']}", file=sys.stderr)
            return False

    # Check valid dates
    for r in records:
        try:
            datetime.strptime(r["date"], "%Y-%m-%d")
        except ValueError:
            print(f"ERROR: Invalid date {r['date']}", file=sys.stderr)
            return False

    return True


def main():
    parser = argparse.ArgumentParser(description="Fetch full GitHub contribution history")
    parser.add_argument("--user", default=os.environ.get("GITHUB_USERNAME", "aryan-sonsurkar"),
                        help="GitHub username")
    parser.add_argument("--token", default=os.environ.get("GITHUB_TOKEN"),
                        help="GitHub API token (required)")
    parser.add_argument("--output", default="data/contributions.json",
                        help="Output JSON path")
    args = parser.parse_args()

    if not args.token:
        print("ERROR: GITHUB_TOKEN is required for GraphQL API access", file=sys.stderr)
        print("Set it via environment variable or --token flag", file=sys.stderr)
        sys.exit(1)

    print(f"Fetching full contribution calendar for {args.user}...")
    calendar = fetch_contribution_calendar(args.user, args.token)

    total = calendar.get("totalContributions", 0)
    print(f"  Total contributions reported by GitHub: {total}")

    records, _ = process_calendar(calendar)
    print(f"  Daily records: {len(records)}")

    if not validate_records(records):
        sys.exit(1)

    # Determine date range
    first_date = records[0]["date"]
    last_date = records[-1]["date"]
    non_zero = sum(1 for r in records if r["contribution_count"] > 0)
    actual_total = sum(r["contribution_count"] for r in records)

    print(f"  Date range: {first_date} to {last_date}")
    print(f"  Active days: {non_zero}")
    print(f"  Total contributions: {actual_total}")

    output = {
        "username": args.user,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "total_contributions": actual_total,
        "active_days": non_zero,
        "first_date": first_date,
        "last_date": last_date,
        "records": records,
    }

    # Ensure output directory exists
    output_dir = os.path.dirname(args.output)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)

    print(f"  Written to {args.output}")
    print("Done!")


if __name__ == "__main__":
    main()
