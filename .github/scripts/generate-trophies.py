#!/usr/bin/env python3
"""Generate GitHub trophy-style SVG from live GraphQL stats."""

from __future__ import annotations

import json
import os
import sys
import urllib.request

USERNAME = os.environ.get("USERNAME", "Timeless-Dave")
TOKEN = os.environ.get("GITHUB_TOKEN", "")
OUTPUT = os.environ.get("OUTPUT_PATH", "dist/analytics/trophies.svg")

QUERY = """
query($login: String!) {
  user(login: $login) {
    repositoriesContributedTo { totalCount }
    repositories(ownerAffiliations: OWNER) { totalCount }
    followers { totalCount }
    contributionsCollection {
      totalCommitContributions
      totalPullRequestContributions
      totalIssueContributions
      restrictedContributionsCount
    }
  }
}
"""

RANKS = [
    (10000, "SSS"),
    (5000, "SS"),
    (2000, "S"),
    (1000, "A"),
    (500, "B"),
    (100, "C"),
    (0, "D"),
]


def rank(value: int) -> str:
    for threshold, label in RANKS:
        if value >= threshold:
            return label
    return "D"


def fetch_stats() -> dict[str, int]:
    payload = json.dumps({"query": QUERY, "variables": {"login": USERNAME}}).encode()
    request = urllib.request.Request(
        "https://api.github.com/graphql",
        data=payload,
        headers={
            "Authorization": f"Bearer {TOKEN}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        body = json.loads(response.read())

    if body.get("errors"):
        raise RuntimeError(json.dumps(body["errors"]))

    user = body["data"]["user"]
    contrib = user["contributionsCollection"]

    repos_req = urllib.request.Request(
        f"https://api.github.com/users/{USERNAME}/repos?per_page=100&type=owner",
        headers={"Authorization": f"Bearer {TOKEN}", "Accept": "application/vnd.github+json"},
    )
    with urllib.request.urlopen(repos_req, timeout=60) as response:
        repos = json.loads(response.read())
    stars = sum(repo.get("stargazers_count", 0) for repo in repos)

    return {
        "commits": contrib["totalCommitContributions"],
        "repos": user["repositories"]["totalCount"],
        "stars": stars,
        "prs": contrib["totalPullRequestContributions"],
        "issues": contrib["totalIssueContributions"],
        "followers": user["followers"]["totalCount"],
    }


def trophy_card(x: int, y: int, title: str, value: int, grade: str, color: str) -> str:
    return f"""
    <g>
      <rect x="{x}" y="{y}" width="140" height="110" rx="10" fill="#1a1b27" stroke="#30363d"/>
      <text x="{x + 70}" y="{y + 28}" fill="#a78bfa" font-size="11" text-anchor="middle" font-family="ui-monospace, monospace">{title}</text>
      <text x="{x + 70}" y="{y + 62}" fill="#ffffff" font-size="28" font-weight="700" text-anchor="middle" font-family="ui-monospace, monospace">{grade}</text>
      <text x="{x + 70}" y="{y + 88}" fill="#8b949e" font-size="11" text-anchor="middle" font-family="ui-monospace, monospace">{value:,}</text>
      <rect x="{x + 8}" y="{y + 8}" width="6" height="6" fill="{color}"/>
    </g>"""


def build_svg(stats: dict[str, int]) -> str:
    cards = [
        ("Commits", stats["commits"], rank(stats["commits"]), "#f97316"),
        ("Stars", stats["stars"], rank(stats["stars"]), "#a78bfa"),
        ("Repos", stats["repos"], rank(stats["repos"]), "#3b82f6"),
        ("PRs", stats["prs"], rank(stats["prs"]), "#22c55e"),
        ("Issues", stats["issues"], rank(stats["issues"]), "#eab308"),
        ("Followers", stats["followers"], rank(stats["followers"]), "#ec4899"),
    ]
    width = 900
    height = 130
    svg_cards = "".join(trophy_card(20 + i * 148, 10, title, value, grade, color) for i, (title, value, grade, color) in enumerate(cards))
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="GitHub trophies for {USERNAME}">
  <rect width="{width}" height="{height}" rx="12" fill="#0d1117"/>
  {svg_cards}
</svg>
"""


def main() -> int:
    if not TOKEN:
        print("GITHUB_TOKEN is required", file=sys.stderr)
        return 1

    stats = fetch_stats()
    os.makedirs(os.path.dirname(OUTPUT) or ".", exist_ok=True)
    with open(OUTPUT, "w", encoding="utf-8") as handle:
        handle.write(build_svg(stats))
    print(f"Wrote {OUTPUT}")
    print(json.dumps(stats))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
