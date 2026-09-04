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
DURATION_MS = 60000
SNAKE_LEN = 4
# Per-scenario timeline fractions within each half of the loop
HOLD_BEFORE = 0.08   # blank pause before word appears
HOLD_VISIBLE = 0.18  # word fully visible before snake starts eating
EAT_PORTION = 0.58   # time spent eating through the word
HOLD_AFTER = 0.08    # blank pause after clear


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
    """Serpentine left→right / right→left through letter cells."""
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
        hide_end = min(base + span - span * HOLD_AFTER * 0.25, 0.999)
        scenarios.append(
            {
                "word": word,
                "cells": cells,
                "path": path,
                "show_start": show_start,
                "eat_start": eat_start,
                "eat_end": eat_end,
                "hide_end": hide_end,
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


def build_snake_frames(scenarios: List[dict], offset: int = 0) -> str:
    """Build keyframes for one snake segment, lagged by `offset` cells behind the head."""
    frames: List[str] = []
    # Off-screen while idle
    frames.append("0%{transform:translate(-24px,-24px)}")

    for scenario in scenarios:
        path = scenario["path"]
        if not path:
            continue
        eat_start = scenario["eat_start"]
        eat_end = scenario["eat_end"]
        eat_span = eat_end - eat_start
        n = len(path)

        # Appear at first cell (or lagged start)
        start_idx = min(offset, n - 1)
        start_t = eat_start + (start_idx / max(n - 1, 1)) * eat_span
        sx, sy = cell_center(*path[start_idx])
        frames.append(f"{pct(start_t - 0.0001)}{{transform:translate(-24px,-24px)}}")
        frames.append(f"{pct(start_t)}{{transform:translate({sx - 8:.1f}px,{sy - 8:.1f}px)}}")

        for i in range(start_idx, n):
            t = eat_start + (i / max(n - 1, 1)) * eat_span
            x, y = cell_center(*path[i])
            frames.append(f"{pct(t)}{{transform:translate({x - 8:.1f}px,{y - 8:.1f}px)}}")

        # Hide after finishing this word
        lx, ly = cell_center(*path[-1])
        frames.append(f"{pct(eat_end)}{{transform:translate({lx - 8:.1f}px,{ly - 8:.1f}px)}}")
        frames.append(f"{pct(eat_end + 0.001)}{{transform:translate(-24px,-24px)}}")

    frames.append("100%{transform:translate(-24px,-24px)}")
    return ",".join(frames)


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
            "stroke:var(--cb);width:12px;height:12px}"
        ),
        ".s{shape-rendering:geometricPrecision;fill:var(--cs)}",
    ]

    rects: List[str] = []
    anim_index = 0

    for row in range(ROWS):
        for col in range(COLS):
            x = ORIGIN_X + col * STEP
            y = ORIGIN_Y + row * STEP
            classes = "c"
            for scenario in scenarios:
                if (col, row) not in scenario["cells"]:
                    continue
                anim_name = f"a{anim_index}"
                anim_index += 1
                classes += f" {anim_name}"
                show = scenario["show_start"]
                eaten = eat_time_for_cell(scenario, col, row)
                # Stay green until this cell is eaten, then clear permanently for this scenario.
                css_parts.append(
                    f"@keyframes {anim_name}{{"
                    f"0%,{pct(show)}{{fill:var(--ce)}}"
                    f"{pct(show)},{pct(eaten)}{{fill:var(--c2)}}"
                    f"{pct(eaten + 0.0005)},100%{{fill:var(--ce)}}"
                    "}}"
                )
                css_parts.append(
                    f".{anim_name}{{animation:{anim_name} {DURATION_MS}ms linear infinite}}"
                )
            rects.append(f'<rect class="{classes}" x="{x}" y="{y}" rx="2" ry="2"/>')

    snake_markup: List[str] = []
    sizes = [
        (0.8, 14.4, 4.5),
        (1.8, 12.3, 4.1),
        (2.6, 10.8, 3.6),
        (3.0, 9.9, 3.3),
    ]
    for offset, (inset, size, radius) in enumerate(sizes):
        frames = build_snake_frames(scenarios, offset=offset)
        name = f"snake{offset}"
        css_parts.append(f"@keyframes {name}{{{frames}}}")
        css_parts.append(
            f".{name}{{animation:{name} {DURATION_MS}ms linear infinite}}"
        )
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
