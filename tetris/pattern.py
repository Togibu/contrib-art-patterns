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


# Each piece: list of rotations; each rotation: list of (row, col) offsets from top-left of bbox.
PIECES: dict[str, list[list[tuple[int, int]]]] = {
    "I": [
        [(0, 0), (0, 1), (0, 2), (0, 3)],
        [(0, 0), (1, 0), (2, 0), (3, 0)],
    ],
    "O": [
        [(0, 0), (0, 1), (1, 0), (1, 1)],
    ],
    "T": [
        [(0, 1), (1, 0), (1, 1), (1, 2)],
        [(0, 0), (1, 0), (1, 1), (2, 0)],
        [(0, 0), (0, 1), (0, 2), (1, 1)],
        [(0, 1), (1, 0), (1, 1), (2, 1)],
    ],
    "S": [
        [(0, 1), (0, 2), (1, 0), (1, 1)],
        [(0, 0), (1, 0), (1, 1), (2, 1)],
    ],
    "Z": [
        [(0, 0), (0, 1), (1, 1), (1, 2)],
        [(0, 1), (1, 0), (1, 1), (2, 0)],
    ],
    "L": [
        [(0, 0), (1, 0), (2, 0), (2, 1)],
        [(0, 0), (0, 1), (0, 2), (1, 0)],
        [(0, 0), (0, 1), (1, 1), (2, 1)],
        [(0, 2), (1, 0), (1, 1), (1, 2)],
    ],
    "J": [
        [(0, 1), (1, 1), (2, 0), (2, 1)],
        [(0, 0), (1, 0), (1, 1), (1, 2)],
        [(0, 0), (0, 1), (1, 0), (2, 0)],
        [(0, 0), (0, 1), (0, 2), (1, 2)],
    ],
}

# Distinct levels per piece type so they're visually distinguishable.
PIECE_LEVEL: dict[str, int] = {
    "I": 4, "O": 2, "T": 3, "S": 1, "Z": 4, "L": 2, "J": 3,
}


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


def _generate_tetris(
    num_weeks: int,
    target_density: float,
    seed: int | None,
) -> tuple[list[list[int]], dict[str, int]]:
    """
    Place random non-overlapping Tetris pieces until ~target_density of cells are filled.
    Each piece type gets a fixed level so the pieces stand out from each other.
    Returns (grid, piece_counts).
    """
    rng = random.Random(seed)
    grid = [[0] * num_weeks for _ in range(7)]
    total_cells = num_weeks * 7
    target_filled = int(total_cells * target_density)
    filled = 0
    counts: dict[str, int] = {name: 0 for name in PIECES}
    piece_names = list(PIECES.keys())
    max_attempts = max(target_filled * 20, 500)
    attempts = 0

    while filled < target_filled and attempts < max_attempts:
        attempts += 1
        name = rng.choice(piece_names)
        rotations = PIECES[name]
        cells = rng.choice(rotations)
        max_r = max(r for r, _ in cells)
        max_c = max(c for _, c in cells)
        if max_r >= 7 or max_c >= num_weeks:
            continue
        r0 = rng.randint(0, 6 - max_r)
        c0 = rng.randint(0, num_weeks - 1 - max_c)
        if all(grid[r0 + r][c0 + c] == 0 for r, c in cells):
            level = PIECE_LEVEL[name]
            for r, c in cells:
                grid[r0 + r][c0 + c] = level
            filled += 4
            counts[name] += 1

    return grid, counts


def run(context: dict[str, Any]) -> None:
    print("Tetris pattern generator")

    weeks_str = input("Number of weeks (grid width) [52]: ").strip()
    num_weeks = int(weeks_str) if weeks_str else 52

    density_str = input("Target fill density 0.0–1.0 [0.45]: ").strip()
    density = float(density_str) if density_str else 0.45
    density = max(0.0, min(1.0, density))

    seed_str = input("Random seed (blank=random): ").strip()
    seed = int(seed_str) if seed_str else None

    start = input("Start date for first column (Sunday) [YYYY-MM-DD, blank=next Sunday]: ").strip()

    grid, counts = _generate_tetris(num_weeks, density, seed)

    if start:
        start_date = date.fromisoformat(start)
    else:
        today = date.today()
        days_until_sun = (6 - today.weekday()) % 7
        start_date = today + timedelta(days=days_until_sun)

    end_date = start_date + timedelta(days=(num_weeks * 7 - 1))
    filled_cells = sum(1 for row in grid for lvl in row if lvl > 0)
    actual_density = filled_cells / (num_weeks * 7)
    total_commits = sum(LEVEL_COMMITS[lvl] for row in grid for lvl in row)
    total_pieces = sum(counts.values())

    print("\nPreview (7 rows = Sun–Sat, glyph density = commit count):")
    print(_render(grid))

    print(f"\nDate range:    {start_date.isoformat()} .. {end_date.isoformat()}")
    print(f"Pieces:        {total_pieces}  ({', '.join(f'{n}={c}' for n, c in counts.items() if c)})")
    print(f"Density:       {actual_density:.2f} (target {density:.2f})")
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
        "pattern": "tetris",
        "meta": {
            "weeks": num_weeks,
            "target_density": density,
            "actual_density": round(actual_density, 4),
            "seed": seed,
            "piece_counts": counts,
            "piece_levels": PIECE_LEVEL,
            "start_date": start_date.isoformat(),
            "level_commits": LEVEL_COMMITS,
            "preview": _glyph_str(grid),
        },
        "schedule": schedule,
    }
    _write_schedule(context["schedule_path"], data)
    print(f"Wrote schedule with {len(schedule)} days, {total_commits} total commits.")
