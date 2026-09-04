#!/usr/bin/env python3
"""Generate contribution-grid snake SVG that spells words before clearing them."""

from __future__ import annotations

import os
from typing import Dict, List, Set, Tuple

OUTPUT_LIGHT = os.environ.get("OUTPUT_LIGHT", "dist/github-contribution-grid-snake.svg")
OUTPUT_DARK = os.environ.get("OUTPUT_DARK", "dist/github-contribution-grid-snake-dark.svg")

# 5-row bitmap font (1 = filled cell)
FONT: Dict[str, List[str]] = {
    "T": ["11111", "00100", "00100", "00100", "00100"],
    "I": ["11111", "00100", "00100", "00100", "11111"],
    "M": ["10001", "11011", "10101", "10001", "10001"],
    "E": ["11111", "10000", "11110", "10000", "11111"],
    "L": ["10000", "10000", "10000", "10000", "11111"],
    "S": ["01111", "10000", "01110", "00001", "11110"],
    "i": ["00100", "00000", "01100", "00100", "01110"],
    "C": ["01110", "10001", "10000", "10001", "01110"],
    "O": ["01110", "10001", "10001", "10001", "01110"],
    "D": ["11100", "10010", "10001", "10010", "11100"],
}

SCENARIOS = ["Timeless", "iCODE"]
COLS = 52
ROWS = 7
CELL = 12
STEP = 16
ORIGIN_X = 2
ORIGIN_Y = 2
DURATION_MS = 48000
# Per-scenario timeline fractions within each half of the loop
HOLD_BEFORE = 0.04
HOLD_VISIBLE = 0.22
EAT_PORTION = 0.58
HOLD_AFTER = 0.08


def cell_center(col: int, row: int) -> Tuple[float, float]:
    x = ORIGIN_X + col * STEP + CELL / 2
    y = ORIGIN_Y + row * STEP + CELL / 2
    return x, y


def word_cells(word: str) -> Set[Tuple[int, int]]:
    width = len(word) * 6 - 1
    start_col = max(0, (COLS - width) // 2)
    start_row = 1
    cells: Set[Tuple[int, int]] = set()
    cursor = start_col
    for char in word:
        bitmap = FONT.get(char, FONT.get(char.upper(), ["00000"] * 5))
        for row_idx, row_bits in enumerate(bitmap):
            for col_idx, bit in enumerate(row_bits):
                if bit == "1":
                    col = cursor + col_idx
                    row = start_row + row_idx
                    if 0 <= col < COLS and 0 <= row < ROWS:
                        cells.add((col, row))
        cursor += 6
    return cells


def snake_eat_order(cells: Set[Tuple[int, int]]) -> List[Tuple[int, int]]:
    rows: Dict[int, List[int]] = {}
    for col, row in cells:
        rows.setdefault(row, []).append(col)
    path: List[Tuple[int, int]] = []
    for row in sorted(rows):
        cols = sorted(rows[row])
        if row % 2 == 0:
            path.extend((col, row) for col in cols)
        else:
            path.extend((col, row) for col in reversed(cols))
    return path


def build_scenarios() -> List[dict]:
    scenarios = []
    span = 1.0 / len(SCENARIOS)
    for index, word in enumerate(SCENARIOS):
        base = index * span
        cells = word_cells(word)
        path = snake_eat_order(cells)
        show_start = base + span * HOLD_BEFORE
        eat_start = show_start + span * HOLD_VISIBLE
        eat_end = eat_start + span * EAT_PORTION
        scenarios.append(
            {
                "word": word,
                "cells": cells,
                "path": path,
                "show_start": show_start,
                "eat_start": eat_start,
                "eat_end": eat_end,
            }
        )
    return scenarios


def pct(value: float) -> str:
    return f"{max(0.0, min(value, 1.0)) * 100:.2f}%"


def eat_time_for_cell(scenario: dict, col: int, row: int) -> float:
    path = scenario["path"]
    try:
        index = path.index((col, row))
    except ValueError:
        return scenario["eat_end"]
    n = max(len(path) - 1, 1)
    return scenario["eat_start"] + (index / n) * (scenario["eat_end"] - scenario["eat_start"])


def build_cell_keyframes(col: int, row: int, scenarios: List[dict]) -> str | None:
    """One animation per cell covering every scenario that uses it."""
    events: List[Tuple[float, str]] = [(0.0, "empty")]
    used = False
    for scenario in scenarios:
        if (col, row) not in scenario["cells"]:
            continue
        used = True
        show = scenario["show_start"]
        eaten = eat_time_for_cell(scenario, col, row)
        events.append((show, "green"))
        events.append((eaten, "empty"))
    if not used:
        return None

    events.append((1.0, "empty"))
    events.sort(key=lambda item: item[0])

    # Collapse consecutive same-state events, keep ranges for CSS.
    parts: List[str] = []
    i = 0
    while i < len(events) - 1:
        t0, state = events[i]
        t1 = events[i + 1][0]
        fill = "var(--c2)" if state == "green" else "var(--ce)"
        # Skip zero-length ranges
        if t1 > t0:
            parts.append(f"{pct(t0)},{pct(t1)}{{fill:{fill}}}")
        i += 1
    return "".join(parts)


def build_snake_frames(scenarios: List[dict], offset: int = 0) -> str:
    """Build keyframes for one snake segment, lagged by `offset` cells behind the head.

    Important: keyframe blocks must be concatenated WITHOUT commas between them.
    Platane/snk style: `0%{...}10%{...}` not `0%{...},10%{...}`.
    """
    frames: List[str] = []
    frames.append("0%{transform:translate(-32px,-32px)}")

    for scenario in scenarios:
        path = scenario["path"]
        if not path:
            continue
        eat_start = scenario["eat_start"]
        eat_end = scenario["eat_end"]
        eat_span = eat_end - eat_start
        n = len(path)
        start_idx = min(offset, n - 1)
        start_t = eat_start + (start_idx / max(n - 1, 1)) * eat_span
        sx, sy = cell_center(*path[start_idx])

        frames.append(f"{pct(max(0.0, start_t - 0.0002))}{{transform:translate(-32px,-32px)}}")
        frames.append(f"{pct(start_t)}{{transform:translate({sx - 8:.1f}px,{sy - 8:.1f}px)}}")

        for i in range(start_idx, n):
            t = eat_start + (i / max(n - 1, 1)) * eat_span
            x, y = cell_center(*path[i])
            frames.append(f"{pct(t)}{{transform:translate({x - 8:.1f}px,{y - 8:.1f}px)}}")

        lx, ly = cell_center(*path[-1])
        frames.append(f"{pct(eat_end)}{{transform:translate({lx - 8:.1f}px,{ly - 8:.1f}px)}}")
        frames.append(f"{pct(min(1.0, eat_end + 0.002))}{{transform:translate(-32px,-32px)}}")

    frames.append("100%{transform:translate(-32px,-32px)}")
    return "".join(frames)


def build_svg(theme: str) -> str:
    if theme == "dark":
        vars_css = "--cb:#1b1f230a;--cs:#f97316;--ce:#0d1117;--c2:#26a641;"
    else:
        vars_css = "--cb:#1b1f230a;--cs:#e11d48;--ce:#ebedf0;--c2:#40c463;"

    scenarios = build_scenarios()
    css_parts: List[str] = [
        f":root{{{vars_css}}}",
        (
            ".c{shape-rendering:geometricPrecision;fill:var(--ce);stroke-width:1px;"
            "stroke:var(--cb);width:12px;height:12px;animation:none linear "
            f"{DURATION_MS}ms infinite}}"
        ),
        (
            ".s{shape-rendering:geometricPrecision;fill:var(--cs);"
            f"animation:none linear {DURATION_MS}ms infinite}}"
        ),
    ]

    rects: List[str] = []
    anim_index = 0

    for row in range(ROWS):
        for col in range(COLS):
            x = ORIGIN_X + col * STEP
            y = ORIGIN_Y + row * STEP
            keyframes = build_cell_keyframes(col, row, scenarios)
            if keyframes is None:
                rects.append(f'<rect class="c" x="{x}" y="{y}" rx="2" ry="2"/>')
                continue
            anim_name = f"a{anim_index}"
            anim_index += 1
            css_parts.append(f"@keyframes {anim_name}{{{keyframes}}}")
            css_parts.append(f".c.{anim_name}{{animation-name:{anim_name}}}")
            rects.append(f'<rect class="c {anim_name}" x="{x}" y="{y}" rx="2" ry="2"/>')

    snake_markup: List[str] = []
    sizes = [
        (0.8, 14.4, 4.5),
        (1.8, 12.3, 4.1),
        (2.6, 10.8, 3.6),
        (3.0, 9.9, 3.3),
    ]
    for offset, (inset, size, radius) in enumerate(sizes):
        frames = build_snake_frames(scenarios, offset=offset)
        name = f"s{offset}"
        css_parts.append(f"@keyframes {name}{{{frames}}}")
        css_parts.append(f".s.{name}{{animation-name:{name};transform:translate(-32px,-32px)}}")
        snake_markup.append(
            f'<rect class="s {name}" x="{inset}" y="{inset}" '
            f'width="{size}" height="{size}" rx="{radius}" ry="{radius}"/>'
        )

    width = ORIGIN_X + COLS * STEP + 2
    height = ORIGIN_Y + ROWS * STEP + 2

    return (
        f'<svg viewBox="-16 -32 {width + 16} {height + 32}" width="{width}" height="{height}" '
        f'xmlns="http://www.w3.org/2000/svg">'
        f"<desc>Timeless text snake — Timeless / iCODE</desc>"
        f'<style>{"".join(css_parts)}</style>'
        f'{"".join(rects)}'
        f'{"".join(snake_markup)}'
        "</svg>"
    )


def main() -> int:
    os.makedirs(os.path.dirname(OUTPUT_LIGHT) or ".", exist_ok=True)
    with open(OUTPUT_LIGHT, "w", encoding="utf-8") as handle:
        handle.write(build_svg("light"))
    with open(OUTPUT_DARK, "w", encoding="utf-8") as handle:
        handle.write(build_svg("dark"))
    print(f"Wrote {OUTPUT_LIGHT} and {OUTPUT_DARK}")
    for scenario in build_scenarios():
        print(
            f"  {scenario['word']}: {len(scenario['cells'])} cells | "
            f"show={scenario['show_start']:.2f} eat={scenario['eat_start']:.2f}-{scenario['eat_end']:.2f}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
