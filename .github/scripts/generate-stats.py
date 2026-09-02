#!/usr/bin/env python3
"""Generate stats card SVG from live GitHub GraphQL data."""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from github_stats_lib import fetch_stats

USERNAME = os.environ.get("USERNAME", "Timeless-Dave")
OUTPUT = os.environ.get("OUTPUT_PATH", "dist/analytics/stats.svg")


def build_svg(stats: dict[str, int]) -> str:
    rows = [
        ("Total Stars", stats["stars"]),
        ("Total Commits", stats["commits"]),
        ("Total PRs", stats["prs"]),
        ("Total Issues", stats["issues"]),
        ("Contributed to", stats["contributed_to"]),
    ]
    row_svg = ""
    y = 72
    for label, value in rows:
        row_svg += f"""
  <text x="24" y="{y}" fill="#8b949e" font-size="14" font-family="ui-monospace, monospace">{label}</text>
  <text x="276" y="{y}" fill="#c9d1d9" font-size="14" text-anchor="end" font-family="ui-monospace, monospace">{value:,}</text>"""
        y += 28

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="300" height="220" viewBox="0 0 300 220" role="img" aria-label="GitHub stats for {USERNAME}">
  <rect width="300" height="220" rx="12" fill="#1a1b27"/>
  <circle cx="42" cy="36" r="18" fill="#a78bfa"/>
  <path d="M42 28c-4 0-7 3-7 7s3 7 7 7 7-3 7-7-3-7-7-7zm0 10c-2 0-3-1-3-3s1-3 3-3 3 1 3 3-1 3-3 3z" fill="#0d1117"/>
  <path d="M30 52c0-6 5-10 12-10s12 4 12 10v2H30v-2z" fill="#0d1117"/>
  <text x="72" y="42" fill="#a78bfa" font-size="18" font-weight="700" font-family="ui-monospace, monospace">Stats</text>
  {row_svg}
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
    print(f"Wrote {OUTPUT} — commits={stats['commits']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
