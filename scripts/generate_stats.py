#!/usr/bin/env python3
"""
Stats Generator for GitHub Profile README.

Fetches real GitHub statistics and generates a stats summary.

Usage:
    python generate_stats.py [--user USERNAME] [--token TOKEN] [--output PATH]

Environment Variables:
    GITHUB_USERNAME  - GitHub username (default: aryan-sonsurkar)
    GITHUB_TOKEN     - GitHub API token (optional)
"""

import argparse
import json
import os
import sys
import urllib.request
import urllib.error
from typing import Dict, List, Tuple


def fetch_user_data(username: str, token: str = None) -> Dict:
    """Fetch user profile data."""
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "profile-readme-generator"
    }
    if token:
        headers["Authorization"] = f"token {token}"

    url = f"https://api.github.com/users/{username}"
    req = urllib.request.Request(url, headers=headers)

    try:
        with urllib.request.urlopen(req) as response:
            return json.loads(response.read().decode())
    except Exception as e:
        print(f"Warning: Error fetching user data: {e}", file=sys.stderr)
        return {}


def fetch_repos(username: str, token: str = None) -> List[Dict]:
    """Fetch all public repositories."""
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "profile-readme-generator"
    }
    if token:
        headers["Authorization"] = f"token {token}"

    repos = []
    page = 1
    while page <= 5:
        url = f"https://api.github.com/users/{username}/repos?per_page=100&page={page}&type=public"
        req = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(req) as response:
                data = json.loads(response.read().decode())
                if not data:
                    break
                repos.extend(data)
                page += 1
        except Exception:
            break

    return repos


def fetch_languages(username: str, token: str = None) -> Dict[str, int]:
    """Fetch language distribution."""
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "profile-readme-generator"
    }
    if token:
        headers["Authorization"] = f"token {token}"

    repos = fetch_repos(username, token)
    languages = {}

    for repo in repos:
        if repo.get("fork"):
            continue
        lang_url = repo.get("languages_url")
        if lang_url:
            req = urllib.request.Request(lang_url, headers=headers)
            try:
                with urllib.request.urlopen(req) as resp:
                    repo_langs = json.loads(resp.read().decode())
                    for lang, count in repo_langs.items():
                        languages[lang] = languages.get(lang, 0) + count
            except Exception:
                pass

    return languages


def generate_stats_md(user_data: Dict, repos: List[Dict], languages: Dict[str, int]) -> str:
    """Generate a markdown stats section."""
    username = user_data.get("login", "unknown")
    name = user_data.get("name", username)
    bio = user_data.get("bio", "")
    followers = user_data.get("followers", 0)
    following = user_data.get("following", 0)
    public_repos = user_data.get("public_repos", 0)

    # Calculate total stars
    total_stars = sum(repo.get("stargazers_count", 0) for repo in repos)

    # Top languages
    sorted_langs = sorted(languages.items(), key=lambda x: x[1], reverse=True)
    total_bytes = sum(languages.values()) if languages else 1
    top_langs = []
    for lang, bytes_count in sorted_langs[:6]:
        pct = (bytes_count / total_bytes) * 100
        top_langs.append((lang, round(pct, 1)))

    # Language bar colors
    lang_colors = {
        "Python": "#3572A5",
        "JavaScript": "#f1e05a",
        "TypeScript": "#3178c6",
        "C": "#555555",
        "C++": "#f34b7d",
        "HTML": "#e34c26",
        "CSS": "#563d7c",
        "Shell": "#89e051",
        "Java": "#b07219",
        "Go": "#00ADD8",
        "Rust": "#dea584",
        "Ruby": "#701516",
    }

    return {
        "total_contributions": "N/A (requires authenticated API)",
        "repos": public_repos,
        "stars": total_stars,
        "followers": followers,
        "following": following,
        "top_languages": top_langs,
        "lang_colors": lang_colors,
    }


def main():
    parser = argparse.ArgumentParser(description="Generate GitHub stats")
    parser.add_argument("--user", default=os.environ.get("GITHUB_USERNAME", "aryan-sonsurkar"))
    parser.add_argument("--token", default=os.environ.get("GITHUB_TOKEN"))
    parser.add_argument("--output", default="assets/stats.json")
    args = parser.parse_args()

    print(f"Fetching data for {args.user}...")

    user_data = fetch_user_data(args.user, args.token)
    repos = fetch_repos(args.user, args.token)
    languages = fetch_languages(args.user, args.token)

    stats = generate_stats_md(user_data, repos, languages)

    output_dir = os.path.dirname(args.output)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2)

    print(f"  Stats written to {args.output}")
    print(f"  Repos: {stats['repos']}, Stars: {stats['stars']}")
    print(f"  Top languages: {', '.join(l[0] for l in stats['top_languages'][:5])}")
    print("Done!")


if __name__ == "__main__":
    main()
