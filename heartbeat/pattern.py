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
    """
    Baseline at row 3. Each beat = flat section + upward V-spike.
    The baseline is absent (broken) at spike positions.

    V-spike shape (amplitude=3, width=6):
      col: 0  1  2  3  4  5
      row0: .  .  #  #  .  .
      row1: .  #  .  .  #  .
      row2: #  .  .  .  .  #
      row3: .  .  .  .  .  .  <- baseline absent here
    """
    BASELINE = 3
    grid = [[False] * num_weeks for _ in range(7)]

    spike_width = 2 * amplitude
    flat_before = max(1, interval - spike_width)

    col = 0
    while col < num_weeks:
        # Flat baseline section before spike
        for c in range(col, min(col + flat_before, num_weeks)):
            grid[BASELINE][c] = True
        col += flat_before

        if col >= num_weeks:
            break

        # If not enough room for a full spike, fill baseline to end
        if col + spike_width > num_weeks:
            for c in range(col, num_weeks):
                grid[BASELINE][c] = True
            break

        # V-spike: symmetric, left and right diagonals meeting at top
        for i in range(amplitude):
            row = BASELINE - 1 - i  # row2, row1, row0 for amplitude=3
            c_left = col + i
            c_right = col + spike_width - 1 - i
            if row >= 0:
                if c_left < num_weeks:
                    grid[row][c_left] = True
                if c_right < num_weeks and c_right != c_left:
                    grid[row][c_right] = True

        col += spike_width

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

    spike_width = 2 * amplitude
    if interval <= spike_width:
        print(f"Note: interval adjusted to {spike_width + 1} (must be > spike width of {spike_width}).")
        interval = spike_width + 1

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
