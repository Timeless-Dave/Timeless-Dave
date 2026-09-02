#!/usr/bin/env python3
"""Generate contribution-grid snake SVG that spells words before clearing them."""

from __future__ import annotations

import os
import sys
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
    "S": ["01110", "10000", "01100", "00010", "11100"],
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
DURATION_MS = 72000
PAUSE_START = 0.06
EAT_START = 0.10
EAT_END = 0.44
SCENARIO_GAP = 0.04


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
    ordered = sorted(cells, key=lambda c: (c[1], c[0]))
    rows: Dict[int, List[int]] = {}
    for col, row in ordered:
        rows.setdefault(row, []).append(col)
    path: List[Tuple[int, int]] = []
    for row in sorted(rows):
        cols = rows[row]
        if row % 2 == 0:
            path.extend((col, row) for col in cols)
        else:
            path.extend((col, row) for col in reversed(cols))
    return path


def build_scenario_windows() -> List[dict]:
    windows = []
    span = 1.0 / len(SCENARIOS)
    for index, word in enumerate(SCENARIOS):
        base = index * span
        windows.append(
            {
                "word": word,
                "cells": word_cells(word),
                "path": snake_eat_order(word_cells(word)),
                "show_start": base + PAUSE_START,
                "eat_start": base + EAT_START,
                "eat_end": base + EAT_END,
                "hide_end": base + span - SCENARIO_GAP,
            }
        )
    return windows


def pct(value: float) -> str:
    return f"{value * 100:.2f}%"


def build_svg(theme: str) -> str:
    if theme == "dark":
        vars_css = "--cb:#1b1f230a;--cs:#f97316;--ce:#0d1117;--c2:#26a641;"
    else:
        vars_css = "--cb:#1b1f230a;--cs:#e11d48;--ce:#ebedf0;--c2:#40c463;"

    scenarios = build_scenario_windows()
    css_parts: List[str] = [
        f":root{{{vars_css}}}",
        (
            ".c{shape-rendering:geometricPrecision;fill:var(--ce);stroke-width:1px;"
            "stroke:var(--cb);width:12px;height:12px}"
        ),
        (
            f".s{{shape-rendering:geometricPrecision;fill:var(--cs);"
            f"animation:snakeMove {DURATION_MS}ms linear infinite}}"
        ),
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
                eat_start = scenario["eat_start"]
                eat_end = scenario["eat_end"]
                hide = scenario["hide_end"]
                css_parts.append(
                    f"@keyframes {anim_name}{{"
                    f"0%,{pct(show)}{{fill:var(--ce)}}"
                    f"{pct(show)},{pct(eat_start)}{{fill:var(--c2)}}"
                    f"{pct(eat_end)},{pct(hide)}{{fill:var(--ce)}}"
                    f"{pct(hide)},100%{{fill:var(--ce)}}"
                    "}}"
                )
                css_parts.append(
                    f".{anim_name}{{animation:{anim_name} {DURATION_MS}ms linear infinite}}"
                )
            rects.append(f'<rect class="{classes}" x="{x}" y="{y}" rx="2" ry="2"/>')

    combined_frames: List[str] = ["0%,100%{transform:translate(-20px,-20px)}"]
    for scenario in scenarios:
        path = scenario["path"]
        if not path:
            continue
        eat_start = scenario["eat_start"]
        eat_end = scenario["eat_end"]
        eat_span = eat_end - eat_start
        n = len(path)
        for i, (col, row) in enumerate(path):
            t = eat_start + (i / max(n - 1, 1)) * eat_span
            x, y = cell_center(col, row)
            combined_frames.append(
                f"{pct(t)}{{transform:translate({x - 8:.1f}px,{y - 8:.1f}px)}}"
            )

    css_parts.append(f"@keyframes snakeMove{{{','.join(combined_frames)}}}")

    width = ORIGIN_X + COLS * STEP + 2
    height = ORIGIN_Y + ROWS * STEP + 2

    return (
        f'<svg viewBox="-16 -32 {width + 16} {height + 32}" width="{width}" height="{height}" '
        f'xmlns="http://www.w3.org/2000/svg">'
        f'<desc>Timeless text snake — Timeless / iCODE</desc>'
        f'<style>{"".join(css_parts)}</style>'
        f'{"".join(rects)}'
        '<rect class="s" x="0.8" y="0.8" width="14.4" height="14.4" rx="4.5" ry="4.5"/>'
        '<rect class="s" x="1.8" y="1.8" width="12.3" height="12.3" rx="4.1" ry="4.1"/>'
        '<rect class="s" x="2.6" y="2.6" width="10.8" height="10.8" rx="3.6" ry="3.6"/>'
        '<rect class="s" x="3.0" y="3.0" width="9.9" height="9.9" rx="3.3" ry="3.3"/>'
        "</svg>"
    )


def main() -> int:
    os.makedirs(os.path.dirname(OUTPUT_LIGHT) or ".", exist_ok=True)
    with open(OUTPUT_LIGHT, "w", encoding="utf-8") as f:
        f.write(build_svg("light"))
    with open(OUTPUT_DARK, "w", encoding="utf-8") as f:
        f.write(build_svg("dark"))
    print(f"Wrote {OUTPUT_LIGHT} and {OUTPUT_DARK}")
    for scenario in build_scenario_windows():
        print(f"  {scenario['word']}: {len(scenario['cells'])} cells")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
