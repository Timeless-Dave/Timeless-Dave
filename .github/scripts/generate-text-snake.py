#!/usr/bin/env python3
"""Generate contribution-grid snake SVG that spells words before clearing them.

Movement matches Platane/snk: one cell step at a time on a continuous path,
with a 4-segment body trailing behind the head.
"""

from __future__ import annotations

import os
from collections import deque
from typing import Dict, List, Optional, Set, Tuple

OUTPUT_LIGHT = os.environ.get("OUTPUT_LIGHT", "dist/github-contribution-grid-snake.svg")
OUTPUT_DARK = os.environ.get("OUTPUT_DARK", "dist/github-contribution-grid-snake-dark.svg")

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

# Timeline within each half of the loop
HOLD_BEFORE = 0.06
HOLD_VISIBLE = 0.20
EAT_PORTION = 0.60


Point = Tuple[int, int]


def snake_translate(col: int, row: int) -> str:
    """Match Platane/snk positioning: 16px grid, snake rects anchored near origin."""
    return f"translate({col * STEP}px,{row * STEP - 16}px)"


def word_cells(word: str) -> Set[Point]:
    width = len(word) * 6 - 1
    start_col = max(0, (COLS - width) // 2)
    start_row = 1
    cells: Set[Point] = set()
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


def letter_visit_order(cells: Set[Point]) -> List[Point]:
    """Serpentine visit order through letter cells only."""
    rows: Dict[int, List[int]] = {}
    for col, row in cells:
        rows.setdefault(row, []).append(col)
    order: List[Point] = []
    for row in sorted(rows):
        cols = sorted(rows[row])
        if row % 2 == 0:
            order.extend((col, row) for col in cols)
        else:
            order.extend((col, row) for col in reversed(cols))
    return order


def neighbors(col: int, row: int) -> List[Point]:
    opts = [(col + 1, row), (col - 1, row), (col, row + 1), (col, row - 1)]
    return [(c, r) for c, r in opts if 0 <= c < COLS and 0 <= r < ROWS]


def bfs_path(start: Point, goal: Point) -> List[Point]:
    """Shortest 4-connected path from start to goal (inclusive)."""
    if start == goal:
        return [start]
    queue: deque[Point] = deque([start])
    came_from: Dict[Point, Optional[Point]] = {start: None}
    while queue:
        current = queue.popleft()
        for nxt in neighbors(*current):
            if nxt in came_from:
                continue
            came_from[nxt] = current
            if nxt == goal:
                queue.clear()
                break
            queue.append(nxt)
    if goal not in came_from:
        # Fallback: jump directly (shouldn't happen on open grid)
        return [start, goal]
    path: List[Point] = []
    node: Optional[Point] = goal
    while node is not None:
        path.append(node)
        node = came_from[node]
    path.reverse()
    return path


def continuous_path(letter_order: List[Point]) -> List[Point]:
    """Connect letter targets with adjacent steps so the snake never teleports."""
    if not letter_order:
        return []
    # Enter from one cell left of the first letter for a clean approach.
    first = letter_order[0]
    entry = (max(0, first[0] - 1), first[1])
    path: List[Point] = []
    waypoints = [entry, *letter_order]
    for i in range(len(waypoints) - 1):
        segment = bfs_path(waypoints[i], waypoints[i + 1])
        if path and segment and path[-1] == segment[0]:
            path.extend(segment[1:])
        else:
            path.extend(segment)
    return path


def build_scenarios() -> List[dict]:
    scenarios = []
    span = 1.0 / len(SCENARIOS)
    for index, word in enumerate(SCENARIOS):
        base = index * span
        letters = word_cells(word)
        order = letter_visit_order(letters)
        move = continuous_path(order)
        # Map each letter cell -> first index on continuous path where head eats it
        eat_index: Dict[Point, int] = {}
        for i, cell in enumerate(move):
            if cell in letters and cell not in eat_index:
                eat_index[cell] = i
        show_start = base + span * HOLD_BEFORE
        eat_start = show_start + span * HOLD_VISIBLE
        eat_end = eat_start + span * EAT_PORTION
        scenarios.append(
            {
                "word": word,
                "letters": letters,
                "move": move,
                "eat_index": eat_index,
                "show_start": show_start,
                "eat_start": eat_start,
                "eat_end": eat_end,
            }
        )
    return scenarios


def pct(value: float) -> str:
    return f"{max(0.0, min(value, 1.0)) * 100:.2f}%"


def time_at_step(scenario: dict, step: int) -> float:
    move = scenario["move"]
    n = max(len(move) - 1, 1)
    return scenario["eat_start"] + (step / n) * (scenario["eat_end"] - scenario["eat_start"])


def build_cell_keyframes(col: int, row: int, scenarios: List[dict]) -> str | None:
    events: List[Tuple[float, str]] = [(0.0, "empty")]
    used = False
    for scenario in scenarios:
        cell = (col, row)
        if cell not in scenario["letters"]:
            continue
        used = True
        show = scenario["show_start"]
        step = scenario["eat_index"].get(cell, len(scenario["move"]) - 1)
        eaten = time_at_step(scenario, step)
        events.append((show, "green"))
        events.append((eaten, "empty"))
    if not used:
        return None

    events.append((1.0, "empty"))
    events.sort(key=lambda item: item[0])

    parts: List[str] = []
    for i in range(len(events) - 1):
        t0, state = events[i]
        t1 = events[i + 1][0]
        if t1 <= t0:
            continue
        fill = "var(--c2)" if state == "green" else "var(--ce)"
        parts.append(f"{pct(t0)},{pct(t1)}{{fill:{fill}}}")
    return "".join(parts)


def build_snake_frames(scenarios: List[dict], offset: int) -> str:
    """Platane/snk-style: same continuous path, body segments lag by `offset` steps."""
    frames: List[str] = [f"0%{{transform:{snake_translate(-2, -1)}}}"]

    for scenario in scenarios:
        move = scenario["move"]
        if not move:
            continue
        eat_start = scenario["eat_start"]
        eat_end = scenario["eat_end"]
        n = max(len(move) - 1, 1)

        # Stay parked until this scenario's eat window (lagged for body).
        park = snake_translate(-2, -1)
        first_step = min(offset, len(move) - 1)
        first_t = eat_start + (first_step / n) * (eat_end - eat_start)
        frames.append(f"{pct(max(0.0, first_t - 0.0001))}{{transform:{park}}}")

        for step in range(first_step, len(move)):
            # Body follows the head: at head-step `step`, this segment is at step-offset
            pos_index = max(0, step - offset)
            col, row = move[pos_index]
            t = eat_start + (step / n) * (eat_end - eat_start)
            frames.append(f"{pct(t)}{{transform:{snake_translate(col, row)}}}")

        # Hold last pose briefly, then park for the next word
        last_col, last_row = move[max(0, len(move) - 1 - offset)]
        frames.append(f"{pct(eat_end)}{{transform:{snake_translate(last_col, last_row)}}}")
        frames.append(f"{pct(min(1.0, eat_end + 0.002))}{{transform:{park}}}")

    frames.append(f"100%{{transform:{snake_translate(-2, -1)}}}")
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
            name = f"a{anim_index}"
            anim_index += 1
            css_parts.append(f"@keyframes {name}{{{keyframes}}}")
            css_parts.append(f".c.{name}{{animation-name:{name}}}")
            rects.append(f'<rect class="c {name}" x="{x}" y="{y}" rx="2" ry="2"/>')

    # Same segment geometry as Platane/snk — layered so the body reads as one snake.
    sizes = [
        (0.8, 14.4, 4.5),
        (1.8, 12.3, 4.1),
        (2.6, 10.8, 3.6),
        (3.0, 9.9, 3.3),
    ]
    snake_markup: List[str] = []
    park = snake_translate(-2, -1)
    for offset, (inset, size, radius) in enumerate(sizes):
        name = f"s{offset}"
        frames = build_snake_frames(scenarios, offset=offset)
        css_parts.append(f"@keyframes {name}{{{frames}}}")
        css_parts.append(f".s.{name}{{animation-name:{name};transform:{park}}}")
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
        move = scenario["move"]
        jumps = 0
        for i in range(1, len(move)):
            c0, r0 = move[i - 1]
            c1, r1 = move[i]
            if abs(c0 - c1) + abs(r0 - r1) != 1:
                jumps += 1
        print(
            f"  {scenario['word']}: letters={len(scenario['letters'])} "
            f"path={len(move)} jumps={jumps} "
            f"show={scenario['show_start']:.2f} eat={scenario['eat_start']:.2f}-{scenario['eat_end']:.2f}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
