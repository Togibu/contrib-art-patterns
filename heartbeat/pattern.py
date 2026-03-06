from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path
from typing import Any

import yaml


def _write_schedule(path: Path, data: dict[str, Any]) -> None:
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")


def _generate_heartbeat(
    num_weeks: int,
    interval: int = 12,
    amplitude: int = 3,
) -> list[list[bool]]:
    """
    One beat cycle = flat + UP spike + flat gap (ST) + DOWN spike (S-wave).

    UP spike (amplitude=3, gap width=4):
      col: 0  1  2  3
      row0: .  .  #  .   <- diagonal left reaches peak
      row1: .  #  .  #   <- diagonal left / vertical right drop
      row2: #  .  .  #   <- start of diagonal / vertical right drop
      row3: .  .  .  .   <- baseline absent

    DOWN spike / S-wave (amplitude=3, gap width=3, approach 1 col before):
      col: -1  0  1  2   (col 0 = gap start)
      row3:  #  .  .  .  <- col -1 has baseline, cols 0-2 gap
      row4:  #  .  .  #  <- approach at col -1, exit at col +2
      row5:  .  #  #  .  <- vertical descent / start of ascent
      row6:  .  #  .  .  <- bottom of spike
    """
    BASELINE = 3
    grid = [[False] * num_weeks for _ in range(7)]

    amplitude_s = amplitude          # S-wave depth equals QRS amplitude
    up_gap = amplitude + 1           # UP spike gap width
    flat_between = 2                 # ST-segment + approach col
    down_gap = amplitude_s           # DOWN spike gap width
    beat_inner = up_gap + flat_between + down_gap
    flat_before = max(0, interval - beat_inner)

    col = 0
    while col < num_weeks:
        # Flat baseline before the beat
        for c in range(col, min(col + flat_before, num_weeks)):
            grid[BASELINE][c] = True
        col += flat_before

        if col >= num_weeks:
            break

        # UP spike: diagonal left ascent + vertical right drop
        if col + up_gap > num_weeks:
            for c in range(col, num_weeks):
                grid[BASELINE][c] = True
            break
        # Diagonal left: (row2,col0) → (row1,col1) → (row0,col2) for amplitude=3
        for i in range(amplitude):
            r = BASELINE - 1 - i
            c_ = col + i
            if r >= 0 and c_ < num_weeks:
                grid[r][c_] = True
        # Vertical right drop: col+amplitude, from row(BASELINE-1) down to row(BASELINE-amplitude+1)
        right_col = col + amplitude
        if right_col < num_weeks:
            for i in range(1, amplitude):
                r = BASELINE - amplitude + i
                if r >= 0:
                    grid[r][right_col] = True
        col += up_gap

        if col >= num_weeks:
            break

        # ST flat + approach col (2 cols, baseline present in both)
        for c in range(col, min(col + flat_between, num_weeks)):
            grid[BASELINE][c] = True
        approach_col = col + flat_between - 1
        # Approach: 1 row below baseline, 1 col before the DOWN gap
        if approach_col < num_weeks:
            grid[BASELINE + 1][approach_col] = True
        col += flat_between

        if col >= num_weeks:
            break

        # DOWN spike (S-wave): vertical descent left + diagonal ascent right
        if col + down_gap > num_weeks:
            for c in range(col, num_weeks):
                grid[BASELINE][c] = True
            break
        # Vertical descent at col (gap start): rows BASELINE+2 to BASELINE+amplitude_s
        for depth in range(2, amplitude_s + 1):
            r = BASELINE + depth
            if r <= 6:
                grid[r][col] = True
        # Diagonal ascent: (BASELINE+amplitude_s-1, col+1) ... (BASELINE+1, col+amplitude_s-1)
        for i in range(1, amplitude_s):
            r = BASELINE + amplitude_s - i
            c_ = col + i
            if r <= 6 and c_ < num_weeks:
                grid[r][c_] = True
        col += down_gap

    # Fill any remaining cols with baseline
    for c in range(col, num_weeks):
        grid[BASELINE][c] = True

    return grid


def run(context: dict[str, Any]) -> None:
    print("Heartbeat pattern generator")

    weeks_str = input("Number of weeks (grid width) [52]: ").strip()
    num_weeks = int(weeks_str) if weeks_str else 52

    amplitude_str = input("Spike amplitude (1–3) [3]: ").strip()
    amplitude = int(amplitude_str) if amplitude_str else 3
    amplitude = max(1, min(3, amplitude))

    beat_inner = (amplitude + 1) + 2 + amplitude
    min_interval = beat_inner + 1
    interval_str = input(f"Columns per heartbeat cycle (min {min_interval}) [12]: ").strip()
    interval = int(interval_str) if interval_str else 12
    if interval < min_interval:
        print(f"Note: interval adjusted to {min_interval}.")
        interval = min_interval

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
