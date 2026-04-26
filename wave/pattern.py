from __future__ import annotations

import math
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import yaml


def _write_schedule(path: Path, data: dict[str, Any]) -> None:
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")


def _generate_wave(
    num_weeks: int,
    amplitude: int,
    wavelength: int,
    thickness: int,
    phase: float,
) -> list[list[bool]]:
    """
    Sine wave centred on the middle row (row 3 of 7).
    For each column, fill `thickness` cells around y = 3 + amplitude * sin(2π * col / wavelength + phase).
    """
    grid = [[False] * num_weeks for _ in range(7)]
    center = 3
    half = (thickness - 1) / 2

    for col in range(num_weeks):
        y = center + amplitude * math.sin(2 * math.pi * col / wavelength + phase)
        top = int(round(y - half))
        bottom = int(round(y + half))
        for r in range(top, bottom + 1):
            if 0 <= r <= 6:
                grid[r][col] = True

    return grid


def run(context: dict[str, Any]) -> None:
    print("Wave pattern generator")

    weeks_str = input("Number of weeks (grid width) [52]: ").strip()
    num_weeks = int(weeks_str) if weeks_str else 52

    amp_str = input("Amplitude (1–3) [3]: ").strip()
    amplitude = int(amp_str) if amp_str else 3
    amplitude = max(1, min(3, amplitude))

    wl_str = input("Wavelength in columns [12]: ").strip()
    wavelength = int(wl_str) if wl_str else 12
    wavelength = max(2, wavelength)

    thick_str = input("Line thickness in cells [1]: ").strip()
    thickness = int(thick_str) if thick_str else 1
    thickness = max(1, min(7, thickness))

    phase_str = input("Phase shift in columns [0]: ").strip()
    phase_cols = float(phase_str) if phase_str else 0.0
    phase = 2 * math.pi * phase_cols / wavelength

    start = input("Start date for first column (Sunday) [YYYY-MM-DD, blank=next Sunday]: ").strip()
    commits_str = input("Commits per filled cell [1]: ").strip()
    commits_per_fill = int(commits_str) if commits_str else 1

    grid = _generate_wave(num_weeks, amplitude, wavelength, thickness, phase)

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
        "pattern": "wave",
        "meta": {
            "weeks": num_weeks,
            "amplitude": amplitude,
            "wavelength": wavelength,
            "thickness": thickness,
            "phase_cols": phase_cols,
            "start_date": start_date.isoformat(),
            "commits_per_fill": commits_per_fill,
            "preview": preview_str,
        },
        "schedule": schedule,
    }
    _write_schedule(context["schedule_path"], data)
    print(f"Wrote schedule with {len(schedule)} days.")
