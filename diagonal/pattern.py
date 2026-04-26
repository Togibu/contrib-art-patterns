from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path
from typing import Any

import yaml


def _write_schedule(path: Path, data: dict[str, Any]) -> None:
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")


def _generate_diagonal(
    num_weeks: int,
    width: int,
    spacing: int,
    direction: str,
) -> list[list[bool]]:
    """
    Diagonal stripes.

    direction "down-right" (\\): cell (r, c) filled if (c + r) % period < width.
    direction "up-right" (/):    cell (r, c) filled if (c - r) % period < width.
    """
    grid = [[False] * num_weeks for _ in range(7)]
    period = width + spacing

    for r in range(7):
        for c in range(num_weeks):
            offset = (c + r) if direction == "down-right" else (c - r)
            if offset % period < width:
                grid[r][c] = True

    return grid


def run(context: dict[str, Any]) -> None:
    print("Diagonal pattern generator")

    weeks_str = input("Number of weeks (grid width) [52]: ").strip()
    num_weeks = int(weeks_str) if weeks_str else 52

    width_str = input("Stripe width in cells [1]: ").strip()
    width = int(width_str) if width_str else 1
    width = max(1, width)

    spacing_str = input("Gap between stripes in cells [2]: ").strip()
    spacing = int(spacing_str) if spacing_str else 2
    spacing = max(1, spacing)

    print("\nDirection:")
    print("  [1] Down-right  (\\)")
    print("  [2] Up-right    (/)")
    dir_choice = input("Choice [1/2] [1]: ").strip() or "1"
    direction = "down-right" if dir_choice == "1" else "up-right"

    start = input("Start date for first column (Sunday) [YYYY-MM-DD, blank=next Sunday]: ").strip()
    commits_str = input("Commits per filled cell [1]: ").strip()
    commits_per_fill = int(commits_str) if commits_str else 1

    grid = _generate_diagonal(num_weeks, width, spacing, direction)

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
        "pattern": "diagonal",
        "meta": {
            "weeks": num_weeks,
            "width": width,
            "spacing": spacing,
            "direction": direction,
            "start_date": start_date.isoformat(),
            "commits_per_fill": commits_per_fill,
            "preview": preview_str,
        },
        "schedule": schedule,
    }
    _write_schedule(context["schedule_path"], data)
    print(f"Wrote schedule with {len(schedule)} days.")
