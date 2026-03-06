from __future__ import annotations

import random
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import yaml


def _write_schedule(path: Path, data: dict[str, Any]) -> None:
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")


def _generate_snake(num_weeks: int, seed: int | None = None) -> list[list[bool]]:
    rng = random.Random(seed)
    grid = [[False] * num_weeks for _ in range(7)]
    visited: set[tuple[int, int]] = set()

    def mark(r: int, c: int) -> bool:
        if 0 <= r < 7 and 0 <= c < num_weeks and (r, c) not in visited:
            grid[r][c] = True
            visited.add((r, c))
            return True
        return False

    row = rng.randint(0, 3)
    col = 0
    mark(row, col)

    h_dir = 1  # start going right

    while True:
        # Long horizontal run
        h_run = rng.randint(3, max(4, num_weeks // 3))
        for _ in range(h_run):
            if not mark(row, col + h_dir):
                break
            col += h_dir

        # Vertical turn: prefer moving toward the opposite half to stay in bounds
        if row < 3:
            v_dir = 1
        elif row > 3:
            v_dir = -1
        else:
            v_dir = rng.choice([-1, 1])
        # small chance to go the other way anyway
        if rng.random() < 0.2:
            v_dir = -v_dir

        max_v = (6 - row) if v_dir == 1 else row
        if max_v < 1:
            v_dir = -v_dir
            max_v = (6 - row) if v_dir == 1 else row
        if max_v < 1:
            break

        v_run = rng.randint(2, min(5, max_v))
        moved = 0
        for _ in range(v_run):
            if not mark(row + v_dir, col):
                break
            row += v_dir
            moved += 1

        if moved == 0:
            break

        # Flip horizontal direction for the next run
        h_dir = -h_dir

        # Stop if the next horizontal step is out of bounds or blocked
        if not (0 <= col + h_dir < num_weeks) or (row, col + h_dir) in visited:
            break

    return grid


def run(context: dict[str, Any]) -> None:
    print("Snake pattern generator")

    weeks_str = input("Number of weeks (grid width): ").strip()
    try:
        num_weeks = int(weeks_str)
        if num_weeks < 4:
            raise ValueError
    except ValueError:
        print("Please enter a number >= 4.")
        return

    start = input("Start date for first column (Sunday) [YYYY-MM-DD, blank=next Sunday]: ").strip()
    commits_per_fill = int(input("Commits per filled cell: ").strip())
    seed_str = input("Random seed (blank=random): ").strip()
    seed = int(seed_str) if seed_str else None

    grid = _generate_snake(num_weeks, seed)

    if start:
        start_date = date.fromisoformat(start)
    else:
        today = date.today()
        days_until_sun = (6 - today.weekday()) % 7
        start_date = today + timedelta(days=days_until_sun)

    end_date = start_date + timedelta(days=(num_weeks * 7 - 1))
    filled = sum(cell for row in grid for cell in row)

    print("\nPreview (7 rows = Sun–Sat, # = filled):")
    for row in grid:
        print("".join("#" if cell else "." for cell in row))

    print(f"\nDate range:   {start_date.isoformat()} .. {end_date.isoformat()}")
    print(f"Filled cells: {filled}")

    confirm = input("\nWrite schedule.yml? [Y/n]: ").strip().lower()
    if confirm not in ("", "y", "yes"):
        print("Aborted.")
        return

    preview_str = "\n".join(
        "".join("#" if cell else "." for cell in row) for row in grid
    )

    schedule: dict[str, int] = {}
    for col in range(num_weeks):
        for r in range(7):
            if grid[r][col]:
                day = start_date + timedelta(days=(col * 7 + r))
                schedule[day.isoformat()] = commits_per_fill

    data = {
        "pattern": "snake",
        "meta": {
            "weeks": num_weeks,
            "start_date": start_date.isoformat(),
            "commits_per_fill": commits_per_fill,
            "seed": seed,
            "preview": preview_str,
        },
        "schedule": schedule,
    }
    _write_schedule(context["schedule_path"], data)
    print(f"Wrote schedule with {len(schedule)} days.")
