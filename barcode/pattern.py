from __future__ import annotations

import random
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


def _generate_barcode(
    num_weeks: int,
    density: float,
    min_height: int,
    max_height: int,
    seed: int | None,
) -> list[list[int]]:
    """
    For each column, with probability `density` place a bar growing from the bottom.
    Bar height is random in [min_height, max_height], level is random in 1..4.
    """
    rng = random.Random(seed)
    grid = [[0] * num_weeks for _ in range(7)]
    for c in range(num_weeks):
        if rng.random() < density:
            height = rng.randint(min_height, max_height)
            level = rng.randint(1, 4)
            for i in range(height):
                r = 6 - i
                if r >= 0:
                    grid[r][c] = level
    return grid


def run(context: dict[str, Any]) -> None:
    print("Barcode pattern generator")

    weeks_str = input("Number of weeks (grid width) [52]: ").strip()
    num_weeks = int(weeks_str) if weeks_str else 52

    density_str = input("Bar density 0.0–1.0 [0.55]: ").strip()
    density = float(density_str) if density_str else 0.55
    density = max(0.0, min(1.0, density))

    min_h_str = input("Min bar height (1–7) [1]: ").strip()
    min_height = int(min_h_str) if min_h_str else 1
    min_height = max(1, min(7, min_height))

    max_h_str = input("Max bar height (1–7) [7]: ").strip()
    max_height = int(max_h_str) if max_h_str else 7
    max_height = max(min_height, min(7, max_height))

    seed_str = input("Random seed (blank=random): ").strip()
    seed = int(seed_str) if seed_str else None

    start = input("Start date for first column (Sunday) [YYYY-MM-DD, blank=next Sunday]: ").strip()

    grid = _generate_barcode(num_weeks, density, min_height, max_height, seed)

    if start:
        start_date = date.fromisoformat(start)
    else:
        today = date.today()
        days_until_sun = (6 - today.weekday()) % 7
        start_date = today + timedelta(days=days_until_sun)

    end_date = start_date + timedelta(days=(num_weeks * 7 - 1))
    bars = sum(1 for c in range(num_weeks) if any(grid[r][c] for r in range(7)))
    total_commits = sum(LEVEL_COMMITS[lvl] for row in grid for lvl in row)

    print("\nPreview (7 rows = Sun–Sat, glyph density = commit count):")
    print(_render(grid))

    print(f"\nDate range:    {start_date.isoformat()} .. {end_date.isoformat()}")
    print(f"Bars:          {bars}")
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
        "pattern": "barcode",
        "meta": {
            "weeks": num_weeks,
            "density": density,
            "min_height": min_height,
            "max_height": max_height,
            "seed": seed,
            "start_date": start_date.isoformat(),
            "level_commits": LEVEL_COMMITS,
            "preview": _glyph_str(grid),
        },
        "schedule": schedule,
    }
    _write_schedule(context["schedule_path"], data)
    print(f"Wrote schedule with {len(schedule)} days, {total_commits} total commits.")
