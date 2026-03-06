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
    entry_row = rng.randint(0, 6)

    for col in range(num_weeks):
        exit_row = rng.randint(0, 6)
        r_min = min(entry_row, exit_row)
        r_max = max(entry_row, exit_row)
        for row in range(r_min, r_max + 1):
            grid[row][col] = True
        entry_row = exit_row

    return grid


def run(context: dict[str, Any]) -> None:
    print("Snake pattern generator")

    weeks_str = input("Number of weeks (length of snake): ").strip()
    try:
        num_weeks = int(weeks_str)
        if num_weeks < 1:
            raise ValueError
    except ValueError:
        print("Invalid number of weeks.")
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

    print("\nPreview (7 rows = Sun–Sat, # = filled):")
    for row in grid:
        print("".join("#" if cell else "." for cell in row))

    print(f"\nDate range: {start_date.isoformat()} .. {end_date.isoformat()}")
    filled = sum(cell for row in grid for cell in row)
    print(f"Filled cells: {filled} / {num_weeks * 7}")

    confirm = input("\nWrite schedule.yml? [Y/n]: ").strip().lower()
    if confirm not in ("", "y", "yes"):
        print("Aborted.")
        return

    preview_str = "\n".join(
        "".join("#" if cell else "." for cell in row) for row in grid
    )

    schedule: dict[str, int] = {}
    for col in range(num_weeks):
        for row in range(7):
            if grid[row][col]:
                day = start_date + timedelta(days=(col * 7 + row))
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
