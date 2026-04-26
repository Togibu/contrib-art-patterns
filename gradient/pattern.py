from __future__ import annotations

import sys
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import yaml


GLYPHS = ["·", "░", "▒", "▓", "█"]
COLORS_256 = [238, 22, 28, 34, 40]
LEVEL_COMMITS = [0, 1, 3, 5, 8]


def _write_schedule(path: Path, data: dict[str, Any]) -> None:
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")


def _glyph_str(grid: list[list[int]]) -> str:
    return "\n".join(
        "".join(GLYPHS[max(0, min(4, lvl))] for lvl in row) for row in grid
    )


def _render(grid: list[list[int]], color: bool | None = None) -> str:
    if color is None:
        color = sys.stdout.isatty()
    if not color:
        return _glyph_str(grid)
    lines = []
    for row in grid:
        cells = []
        for lvl in row:
            lvl = max(0, min(4, lvl))
            cells.append(f"\033[38;5;{COLORS_256[lvl]}m{GLYPHS[lvl]}\033[0m")
        lines.append("".join(cells))
    return "\n".join(lines)


def _generate_gradient(num_weeks: int, direction: str) -> list[list[int]]:
    """
    4-level gradient across the grid.

    direction:
      "left-right"  → level grows with column
      "right-left"  → level shrinks with column
      "top-bottom"  → level grows with row
      "bottom-top"  → level shrinks with row
    """
    grid = [[0] * num_weeks for _ in range(7)]

    def col_level(c: int) -> int:
        # Map column 0..num_weeks-1 to level 1..4
        return 1 + min(3, int(4 * c / max(1, num_weeks)))

    def row_level(r: int) -> int:
        # Map row 0..6 to level 1..4
        return 1 + min(3, int(4 * r / 7))

    for r in range(7):
        for c in range(num_weeks):
            if direction == "left-right":
                grid[r][c] = col_level(c)
            elif direction == "right-left":
                grid[r][c] = col_level(num_weeks - 1 - c)
            elif direction == "top-bottom":
                grid[r][c] = row_level(r)
            elif direction == "bottom-top":
                grid[r][c] = row_level(6 - r)

    return grid


def run(context: dict[str, Any]) -> None:
    print("Gradient pattern generator")

    weeks_str = input("Number of weeks (grid width) [52]: ").strip()
    num_weeks = int(weeks_str) if weeks_str else 52

    print("\nDirection:")
    print("  [1] Left → Right (light to dark)")
    print("  [2] Right → Left (dark to light)")
    print("  [3] Top → Bottom (light to dark)")
    print("  [4] Bottom → Top (dark to light)")
    choice = input("Choice [1/2/3/4] [1]: ").strip() or "1"
    direction = {
        "1": "left-right", "2": "right-left",
        "3": "top-bottom", "4": "bottom-top",
    }.get(choice, "left-right")

    start = input("Start date for first column (Sunday) [YYYY-MM-DD, blank=next Sunday]: ").strip()

    grid = _generate_gradient(num_weeks, direction)

    if start:
        start_date = date.fromisoformat(start)
    else:
        today = date.today()
        days_until_sun = (6 - today.weekday()) % 7
        start_date = today + timedelta(days=days_until_sun)

    end_date = start_date + timedelta(days=(num_weeks * 7 - 1))
    total_commits = sum(LEVEL_COMMITS[lvl] for row in grid for lvl in row)

    print("\nPreview (7 rows = Sun–Sat, glyph density = commit count):")
    print(_render(grid))

    print(f"\nDate range:    {start_date.isoformat()} .. {end_date.isoformat()}")
    print(f"Total commits: {total_commits}")

    if end_date.year > start_date.year:
        print(
            "\nWarning: the schedule crosses into another year. "
            "GitHub's contribution graph resets each year, so the pattern "
            "will be split across multiple graphs."
        )

    confirm = input("\nWrite schedule.yml? [Y/n]: ").strip().lower()
    if confirm not in ("", "y", "yes"):
        print("Aborted.")
        return

    schedule: dict[str, int] = {}
    for col in range(num_weeks):
        for r in range(7):
            level = grid[r][col]
            if level > 0:
                day = start_date + timedelta(days=(col * 7 + r))
                schedule[day.isoformat()] = LEVEL_COMMITS[level]

    data = {
        "pattern": "gradient",
        "meta": {
            "weeks": num_weeks,
            "direction": direction,
            "start_date": start_date.isoformat(),
            "level_commits": LEVEL_COMMITS,
            "preview": _glyph_str(grid),
        },
        "schedule": schedule,
    }
    _write_schedule(context["schedule_path"], data)
    print(f"Wrote schedule with {len(schedule)} days, {total_commits} total commits.")
