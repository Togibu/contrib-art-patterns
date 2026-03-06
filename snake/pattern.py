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

    row = rng.randint(0, 2)  # start in upper rows
    col = 0
    h_dir = 1  # start going right

    grid[row][col] = True

    while True:
        # Go toward the opposite edge with a small random indent
        indent = rng.randint(0, min(3, max(1, num_weeks // 15)))
        target_col = (num_weeks - 1 - indent) if h_dir == 1 else indent

        # Ensure we actually move forward
        if h_dir == 1 and target_col <= col:
            break
        if h_dir == -1 and target_col >= col:
            break

        # Mark horizontal segment
        step = 1 if h_dir == 1 else -1
        while col != target_col:
            col += step
            grid[row][col] = True

        # Go down 1–3 rows
        max_down = 6 - row
        if max_down == 0:
            break
        v_steps = rng.randint(1, min(3, max_down))
        for _ in range(v_steps):
            row += 1
            grid[row][col] = True
            if row >= 6:
                break

        if row >= 6:
            break

        h_dir = -h_dir

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
