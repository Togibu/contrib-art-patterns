from __future__ import annotations

import random
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import yaml


def _write_schedule(path: Path, data: dict[str, Any]) -> None:
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")


def _generate_heartbeat(
    num_weeks: int,
    min_amplitude: int = 1,
    max_amplitude: int = 3,
    min_interval: int = 8,
    max_interval: int = 16,
    seed: int | None = None,
) -> list[list[bool]]:
    """
    Each beat picks a random amplitude and interval within the given ranges.

    UP spike (amplitude=A, gap width=A+1):
      diagonal left ascent + vertical right drop, baseline absent.

    DOWN spike / S-wave (amplitude=A, gap width=A, approach 1 col before):
      vertical descent left + diagonal right ascent, baseline absent.
    """
    rng = random.Random(seed)
    BASELINE = 3
    grid = [[False] * num_weeks for _ in range(7)]

    col = 0
    while col < num_weeks:
        amplitude = rng.randint(min_amplitude, max_amplitude)
        amplitude_s = amplitude
        beat_inner = (amplitude + 1) + 2 + amplitude_s  # up_gap + flat_between + down_gap
        interval = rng.randint(min_interval, max_interval)
        flat_before = max(0, interval - beat_inner)

        # Flat baseline before the beat
        for c in range(col, min(col + flat_before, num_weeks)):
            grid[BASELINE][c] = True
        col += flat_before

        if col >= num_weeks:
            break

        # UP spike: diagonal left ascent + vertical right drop
        if col + amplitude + 1 > num_weeks:
            for c in range(col, num_weeks):
                grid[BASELINE][c] = True
            break
        for i in range(amplitude):
            r = BASELINE - 1 - i
            c_ = col + i
            if r >= 0 and c_ < num_weeks:
                grid[r][c_] = True
        right_col = col + amplitude
        if right_col < num_weeks:
            for i in range(1, amplitude):
                r = BASELINE - amplitude + i
                if r >= 0:
                    grid[r][right_col] = True
        col += amplitude + 1

        if col >= num_weeks:
            break

        # ST flat + approach col (2 cols, baseline present in both)
        for c in range(col, min(col + 2, num_weeks)):
            grid[BASELINE][c] = True
        approach_col = col + 1
        if approach_col < num_weeks:
            grid[BASELINE + 1][approach_col] = True
        col += 2

        if col >= num_weeks:
            break

        # DOWN spike (S-wave): vertical descent + diagonal ascent
        if col + amplitude_s > num_weeks:
            for c in range(col, num_weeks):
                grid[BASELINE][c] = True
            break
        for depth in range(2, amplitude_s + 1):
            r = BASELINE + depth
            if r <= 6:
                grid[r][col] = True
        for i in range(1, amplitude_s):
            r = BASELINE + amplitude_s - i
            c_ = col + i
            if r <= 6 and c_ < num_weeks:
                grid[r][c_] = True
        col += amplitude_s

    # Fill any remaining cols with baseline
    for c in range(col, num_weeks):
        grid[BASELINE][c] = True

    return grid


def run(context: dict[str, Any]) -> None:
    print("Heartbeat pattern generator")

    weeks_str = input("Number of weeks (grid width) [52]: ").strip()
    num_weeks = int(weeks_str) if weeks_str else 52

    min_amp_str = input("Min spike amplitude (1–3) [1]: ").strip()
    min_amplitude = int(min_amp_str) if min_amp_str else 1
    min_amplitude = max(1, min(3, min_amplitude))

    max_amp_str = input("Max spike amplitude (1–3) [3]: ").strip()
    max_amplitude = int(max_amp_str) if max_amp_str else 3
    max_amplitude = max(min_amplitude, min(3, max_amplitude))

    min_int_str = input("Min columns between beats [8]: ").strip()
    min_interval = int(min_int_str) if min_int_str else 8
    min_interval = max(1, min_interval)

    max_int_str = input("Max columns between beats [16]: ").strip()
    max_interval = int(max_int_str) if max_int_str else 16
    max_interval = max(min_interval, max_interval)

    seed_str = input("Random seed (blank=random): ").strip()
    seed = int(seed_str) if seed_str else None

    start = input("Start date for first column (Sunday) [YYYY-MM-DD, blank=next Sunday]: ").strip()
    commits_str = input("Commits per filled cell [1]: ").strip()
    commits_per_fill = int(commits_str) if commits_str else 1

    grid = _generate_heartbeat(num_weeks, min_amplitude, max_amplitude, min_interval, max_interval, seed)

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
        "pattern": "heartbeat",
        "meta": {
            "weeks": num_weeks,
            "min_amplitude": min_amplitude,
            "max_amplitude": max_amplitude,
            "min_interval": min_interval,
            "max_interval": max_interval,
            "seed": seed,
            "start_date": start_date.isoformat(),
            "commits_per_fill": commits_per_fill,
            "preview": preview_str,
        },
        "schedule": schedule,
    }
    _write_schedule(context["schedule_path"], data)
    print(f"Wrote schedule with {len(schedule)} days.")
