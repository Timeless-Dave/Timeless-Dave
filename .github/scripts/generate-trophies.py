#!/usr/bin/env python3
"""Generate GitHub trophy SVG with cup icons and RyotaK-compatible ranks."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from github_stats_lib import fetch_stats

USERNAME = os.environ.get("USERNAME", "Timeless-Dave")
OUTPUT = os.environ.get("OUTPUT_PATH", "dist/analytics/trophies.svg")

# Rank thresholds from ryo-ma/github-profile-trophy
RANK_RULES: dict[str, list[tuple[str, int, str]]] = {
    "Commits": [
        ("SSS", 4000, "God Committer"),
        ("SS", 2000, "Deep Committer"),
        ("S", 1000, "Super Committer"),
        ("AAA", 500, "Ultra Committer"),
        ("AA", 200, "Hyper Committer"),
        ("A", 100, "High Committer"),
        ("B", 10, "Middle Committer"),
        ("C", 1, "First Commit"),
    ],
    "Stars": [
        ("SSS", 2000, "Super Stargazer"),
        ("SS", 700, "High Stargazer"),
        ("S", 200, "Stargazer"),
        ("AAA", 100, "Super Star"),
        ("AA", 50, "High Star"),
        ("A", 30, "You are a Star"),
        ("B", 10, "Middle Star"),
        ("C", 1, "First Star"),
    ],
    "Repos": [
        ("SSS", 50, "God Repo Creator"),
        ("SS", 45, "Deep Repo Creator"),
        ("S", 40, "Super Repo Creator"),
        ("AAA", 35, "Ultra Repo Creator"),
        ("AA", 30, "Hyper Repo Creator"),
        ("A", 20, "High Repo Creator"),
        ("B", 10, "Middle Repo Creator"),
        ("C", 1, "First Repository"),
    ],
    "PRs": [
        ("SSS", 1000, "God Puller"),
        ("SS", 500, "Deep Puller"),
        ("S", 200, "Super Puller"),
        ("AAA", 100, "Ultra Puller"),
        ("AA", 50, "Hyper Puller"),
        ("A", 20, "High Puller"),
        ("B", 10, "Middle Puller"),
        ("C", 1, "First Pull"),
    ],
    "Issues": [
        ("SSS", 1000, "God Issuer"),
        ("SS", 500, "Deep Issuer"),
        ("S", 200, "Super Issuer"),
        ("AAA", 100, "Ultra Issuer"),
        ("AA", 50, "Hyper Issuer"),
        ("A", 20, "High Issuer"),
        ("B", 10, "Middle Issuer"),
        ("C", 1, "First Issue"),
    ],
    "Followers": [
        ("SSS", 1000, "Super Celebrity"),
        ("SS", 400, "Ultra Celebrity"),
        ("S", 200, "Hyper Celebrity"),
        ("AAA", 100, "Famous User"),
        ("AA", 50, "Active User"),
        ("A", 20, "Dynamic User"),
        ("B", 10, "Many Friends"),
        ("C", 1, "First Friend"),
    ],
}

RANK_COLORS: dict[str, tuple[str, str]] = {
    "SSS": ("#ffd700", "#fbbf24"),
    "SS": ("#f59e0b", "#d97706"),
    "S": ("#f97316", "#ea580c"),
    "AAA": ("#22c55e", "#16a34a"),
    "AA": ("#10b981", "#059669"),
    "A": ("#34d399", "#10b981"),
    "B": ("#3b82f6", "#2563eb"),
    "C": ("#6b7280", "#4b5563"),
    "—": ("#30363d", "#21262d"),
}


def resolve_rank(score: int, rules: list[tuple[str, int, str]]) -> tuple[str, str]:
    rank, message = "—", "No data"
    for label, threshold, msg in reversed(rules):
        if score >= threshold:
            return label, msg
    return rank, message


def trophy_cup(cx: int, cy: int, rank: str) -> str:
    fill, stroke = RANK_COLORS.get(rank, RANK_COLORS["—"])
    label = rank if rank != "—" else "·"
    font_size = 11 if len(label) <= 2 else 9
    return f"""
    <g transform="translate({cx - 50}, {cy})">
      <rect x="10" y="78" width="80" height="8" rx="3" fill="{stroke}"/>
      <rect x="6" y="86" width="88" height="6" rx="2" fill="#161b22"/>
      <path d="M26 18 h48 v6 c0 22-10 34-24 38 c-14-4-24-16-24-38 v-6z" fill="{fill}" stroke="{stroke}" stroke-width="2"/>
      <path d="M22 18 h56 v8 h-56z" fill="{stroke}" opacity="0.35"/>
      <ellipse cx="50" cy="18" rx="28" ry="6" fill="{stroke}"/>
      <text x="50" y="48" text-anchor="middle" fill="#ffffff" font-size="{font_size}" font-weight="700" font-family="ui-monospace, monospace">{label}</text>
    </g>"""


def trophy_panel(x: int, title: str, value: int, rank: str, message: str) -> str:
    return f"""
    <g transform="translate({x}, 0)">
      <rect x="0" y="0" width="140" height="150" rx="10" fill="#1a1b27" stroke="#30363d"/>
      <text x="70" y="18" fill="#a78bfa" font-size="11" text-anchor="middle" font-family="ui-monospace, monospace">{title}</text>
      {trophy_cup(70, 8, rank)}
      <text x="70" y="112" fill="#c9d1d9" font-size="10" text-anchor="middle" font-family="ui-monospace, monospace">{message}</text>
      <text x="70" y="132" fill="#8b949e" font-size="12" text-anchor="middle" font-family="ui-monospace, monospace">{value:,}</text>
    </g>"""


def build_svg(stats: dict[str, int]) -> str:
    cards = [
        ("Commits", stats["commits"], "Commits"),
        ("Stars", stats["stars"], "Stars"),
        ("Repos", stats["repos"], "Repos"),
        ("PRs", stats["prs"], "PRs"),
        ("Issues", stats["issues"], "Issues"),
        ("Followers", stats["followers"], "Followers"),
    ]
    panels = ""
    for index, (title, value, key) in enumerate(cards):
        rank, message = resolve_rank(value, RANK_RULES[key])
        panels += trophy_panel(12 + index * 148, title, value, rank, message)

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="900" height="150" viewBox="0 0 900 150" role="img" aria-label="GitHub trophies for {USERNAME}">
  <rect width="900" height="150" rx="12" fill="#0d1117"/>
  {panels}
</svg>
"""


def main() -> int:
    try:
        stats = fetch_stats()
    except Exception as error:  # noqa: BLE001
        print(f"Failed to fetch stats: {error}", file=sys.stderr)
        return 1

    os.makedirs(os.path.dirname(OUTPUT) or ".", exist_ok=True)
    with open(OUTPUT, "w", encoding="utf-8") as handle:
        handle.write(build_svg(stats))
    print(f"Wrote {OUTPUT}")
    print(json.dumps(stats, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
