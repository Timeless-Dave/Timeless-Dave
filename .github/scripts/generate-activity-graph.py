#!/usr/bin/env python3
"""Generate contribution activity graph SVG from GitHub GraphQL."""

from __future__ import annotations

import json
import os
import sys
import urllib.request
from datetime import date, timedelta

USERNAME = os.environ.get("USERNAME", "Timeless-Dave")
TOKEN = os.environ.get("GITHUB_TOKEN", "")
OUTPUT = os.environ.get("OUTPUT_PATH", "dist/analytics/activity-graph.svg")
WIDTH = 900
HEIGHT = 220
PADDING = 40

QUERY = """
query($login: String!, $from: DateTime!, $to: DateTime!) {
  user(login: $login) {
    contributionsCollection(from: $from, to: $to) {
      contributionCalendar {
        totalContributions
        weeks {
          contributionDays {
            date
            contributionCount
          }
        }
      }
    }
  }
}
"""


def fetch_contributions() -> list[int]:
    today = date.today()
    start = today - timedelta(days=364)
    payload = json.dumps(
        {
            "query": QUERY,
            "variables": {
                "login": USERNAME,
                "from": start.isoformat() + "T00:00:00Z",
                "to": today.isoformat() + "T23:59:59Z",
            },
        }
    ).encode()
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

    weeks = body["data"]["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]
    counts: list[int] = []
    for week in weeks:
        for day in week["contributionDays"]:
            counts.append(day["contributionCount"])
    return counts[-365:] if len(counts) > 365 else counts


def build_svg(counts: list[int]) -> str:
    if not counts:
        counts = [0]

    max_count = max(counts) or 1
    plot_width = WIDTH - PADDING * 2
    plot_height = HEIGHT - PADDING * 2
    step = plot_width / max(len(counts) - 1, 1)

    points = []
    area_points = [f"{PADDING},{HEIGHT - PADDING}"]
    for index, count in enumerate(counts):
        x = PADDING + index * step
        y = HEIGHT - PADDING - (count / max_count) * plot_height
        points.append(f"{x:.1f},{y:.1f}")
        area_points.append(f"{x:.1f},{y:.1f}")
    area_points.append(f"{PADDING + (len(counts) - 1) * step:.1f},{HEIGHT - PADDING}")

    polyline = " ".join(points)
    area = " ".join(area_points)
    total = sum(counts)

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}" role="img" aria-label="Contribution activity for {USERNAME}">
  <rect width="{WIDTH}" height="{HEIGHT}" rx="12" fill="#0d1117"/>
  <text x="{PADDING}" y="28" fill="#a78bfa" font-size="16" font-weight="700" font-family="ui-monospace, monospace">Contribution Activity</text>
  <text x="{PADDING}" y="48" fill="#8b949e" font-size="11" font-family="ui-monospace, monospace">{total} contributions in the last year</text>
  <polygon points="{area}" fill="#1a0e3340"/>
  <polyline points="{polyline}" fill="none" stroke="#a78bfa" stroke-width="2.5" stroke-linejoin="round" stroke-linecap="round"/>
  {"".join(f'<circle cx="{PADDING + i * step:.1f}" cy="{HEIGHT - PADDING - (c / max_count) * plot_height:.1f}" r="2.5" fill="#ffffff"/>' for i, c in enumerate(counts) if c > 0)}
</svg>
"""


def main() -> int:
    if not TOKEN:
        print("GITHUB_TOKEN is required", file=sys.stderr)
        return 1

    counts = fetch_contributions()
    os.makedirs(os.path.dirname(OUTPUT) or ".", exist_ok=True)
    with open(OUTPUT, "w", encoding="utf-8") as handle:
        handle.write(build_svg(counts))
    print(f"Wrote {OUTPUT} ({len(counts)} days, {sum(counts)} contributions)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
