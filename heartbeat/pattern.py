from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path
from typing import Any

import yaml


def _write_schedule(path: Path, data: dict[str, Any]) -> None:
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")


def _generate_heartbeat(
    num_weeks: int,
    interval: int = 8,
    amplitude: int = 3,
) -> list[list[bool]]:
    BASELINE = 3  # middle row (0=top/Sun, 6=bottom/Sat)
    grid = [[False] * num_weeks for _ in range(7)]

    # Fill flat baseline across all columns
    for col in range(num_weeks):
        grid[BASELINE][col] = True

    # Spike shape (col_offset from spike_start, absolute row):
    #   +1: rising (P-wave)
    #   +2: QRS peak
    #   +3: S-dip below baseline
    #   +5: T-wave bump
    peak_row = BASELINE - amplitude
    dip_row = min(BASELINE + amplitude - 1, 6)
    rise_row = max(BASELINE - (amplitude - 1), 0)
    t_row = max(BASELINE - amplitude // 2, 0)

    spike_shape = [
        (1, rise_row),  # rising
        (2, peak_row),  # QRS peak
        (3, dip_row),   # S dip
        (5, t_row),     # T wave
    ]

    for spike_start in range(0, num_weeks, interval):
        for col_offset, row in spike_shape:
            col = spike_start + col_offset
            if 0 <= col < num_weeks and 0 <= row < 7:
                grid[row][col] = True

    return grid


def run(context: dict[str, Any]) -> None:
    print("Heartbeat pattern generator")

    weeks_str = input("Number of weeks (grid width) [52]: ").strip()
    num_weeks = int(weeks_str) if weeks_str else 52

    interval_str = input("Columns between spikes [8]: ").strip()
    interval = int(interval_str) if interval_str else 8

    amplitude_str = input("Spike amplitude (1–3) [3]: ").strip()
    amplitude = int(amplitude_str) if amplitude_str else 3
    amplitude = max(1, min(3, amplitude))

    start = input("Start date for first column (Sunday) [YYYY-MM-DD, blank=next Sunday]: ").strip()
    commits_str = input("Commits per filled cell [1]: ").strip()
    commits_per_fill = int(commits_str) if commits_str else 1

    grid = _generate_heartbeat(num_weeks, interval, amplitude)

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
            f"\nWarning: the schedule crosses into {end_date.year}. "
            "GitHub's contribution graph resets each year, so the pattern "
            "will be split across two graphs."
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
        "pattern": "heartbeat",
        "meta": {
            "weeks": num_weeks,
            "interval": interval,
            "amplitude": amplitude,
            "start_date": start_date.isoformat(),
            "commits_per_fill": commits_per_fill,
            "preview": preview_str,
        },
        "schedule": schedule,
    }
    _write_schedule(context["schedule_path"], data)
    print(f"Wrote schedule with {len(schedule)} days.")
