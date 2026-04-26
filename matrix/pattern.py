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


def _generate_matrix(
    num_weeks: int,
    density: float,
    min_length: int,
    max_length: int,
    seed: int | None,
) -> list[list[int]]:
    """
    Matrix-style digital rain. Each column has probability `density` of
    containing a falling stream. A stream is a vertical streak of length L;
    the bottom-most cell is the head (level 4), fading linearly up to level 1
    at the tail. Streams can overlap: where they do, the brighter level wins.
    """
    rng = random.Random(seed)
    grid = [[0] * num_weeks for _ in range(7)]
    for c in range(num_weeks):
        if rng.random() < density:
            length = rng.randint(min_length, max_length)
            head_row = rng.randint(length - 1, 6)
            for i in range(length):
                r = head_row - i
                if r < 0:
                    break
                # i=0 is head (darkest=4), i=length-1 is tail (lightest=1)
                if length == 1:
                    level = 4
                else:
                    level = 4 - int(round(3 * i / (length - 1)))
                level = max(1, min(4, level))
                if level > grid[r][c]:
                    grid[r][c] = level
    return grid


def run(context: dict[str, Any]) -> None:
    print("Matrix pattern generator")

    weeks_str = input("Number of weeks (grid width) [52]: ").strip()
    num_weeks = int(weeks_str) if weeks_str else 52

    density_str = input("Stream density 0.0–1.0 [0.30]: ").strip()
    density = float(density_str) if density_str else 0.30
    density = max(0.0, min(1.0, density))

    min_l_str = input("Min stream length (1–7) [2]: ").strip()
    min_length = int(min_l_str) if min_l_str else 2
    min_length = max(1, min(7, min_length))

    max_l_str = input("Max stream length (1–7) [4]: ").strip()
    max_length = int(max_l_str) if max_l_str else 4
    max_length = max(min_length, min(7, max_length))

    seed_str = input("Random seed (blank=random): ").strip()
    seed = int(seed_str) if seed_str else None

    start = input("Start date for first column (Sunday) [YYYY-MM-DD, blank=next Sunday]: ").strip()

    grid = _generate_matrix(num_weeks, density, min_length, max_length, seed)

    if start:
        start_date = date.fromisoformat(start)
    else:
        today = date.today()
        days_until_sun = (6 - today.weekday()) % 7
        start_date = today + timedelta(days=days_until_sun)

    end_date = start_date + timedelta(days=(num_weeks * 7 - 1))
    streams = sum(1 for c in range(num_weeks) if any(grid[r][c] for r in range(7)))
    total_commits = sum(LEVEL_COMMITS[lvl] for row in grid for lvl in row)

    print("\nPreview (7 rows = Sun–Sat, glyph density = commit count):")
    print(_render(grid))

    print(f"\nDate range:    {start_date.isoformat()} .. {end_date.isoformat()}")
    print(f"Streams:       {streams}")
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
        "pattern": "matrix",
        "meta": {
            "weeks": num_weeks,
            "density": density,
            "min_length": min_length,
            "max_length": max_length,
            "seed": seed,
            "start_date": start_date.isoformat(),
            "level_commits": LEVEL_COMMITS,
            "preview": _glyph_str(grid),
        },
        "schedule": schedule,
    }
    _write_schedule(context["schedule_path"], data)
    print(f"Wrote schedule with {len(schedule)} days, {total_commits} total commits.")
