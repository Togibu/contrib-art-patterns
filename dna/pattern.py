from __future__ import annotations

import math
import sys
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import yaml


GLYPHS = ["·", "░", "▒", "▓", "█"]
COLORS_256 = [238, 22, 28, 34, 40]
LEVEL_COMMITS = [0, 1, 3, 5, 8]


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


def _generate_dna(
    num_weeks: int,
    amplitude: int,
    wavelength: int,
    thickness: int,
    strand_a_level: int,
    strand_b_level: int,
) -> list[list[int]]:
    """
    Two sine strands centred on row 3, π out of phase (so they cross every wavelength/2).
    Strand A and strand B get different levels so they're distinguishable.
    On overlap (the crossings), the brighter level wins.
    """
    grid = [[0] * num_weeks for _ in range(7)]
    center = 3
    half = (thickness - 1) / 2

    for col in range(num_weeks):
        phase = 2 * math.pi * col / wavelength
        y_a = center + amplitude * math.sin(phase)
        y_b = center + amplitude * math.sin(phase + math.pi)

        for r in range(7):
            if abs(r - y_a) <= half + 0.5:
                if strand_a_level > grid[r][col]:
                    grid[r][col] = strand_a_level
            if abs(r - y_b) <= half + 0.5:
                if strand_b_level > grid[r][col]:
                    grid[r][col] = strand_b_level

    return grid


def run(context: dict[str, Any]) -> None:
    print("DNA pattern generator")

    weeks_str = input("Number of weeks (grid width) [52]: ").strip()
    num_weeks = int(weeks_str) if weeks_str else 52

    amp_str = input("Amplitude (1–3) [3]: ").strip()
    amplitude = int(amp_str) if amp_str else 3
    amplitude = max(1, min(3, amplitude))

    wl_str = input("Wavelength in columns [12]: ").strip()
    wavelength = int(wl_str) if wl_str else 12
    wavelength = max(2, wavelength)

    thick_str = input("Strand thickness in cells [1]: ").strip()
    thickness = int(thick_str) if thick_str else 1
    thickness = max(1, min(3, thickness))

    a_str = input("Strand A level (1–4) [4]: ").strip()
    strand_a_level = int(a_str) if a_str else 4
    strand_a_level = max(1, min(4, strand_a_level))

    b_str = input("Strand B level (1–4) [2]: ").strip()
    strand_b_level = int(b_str) if b_str else 2
    strand_b_level = max(1, min(4, strand_b_level))

    start = input("Start date for first column (Sunday) [YYYY-MM-DD, blank=next Sunday]: ").strip()

    grid = _generate_dna(
        num_weeks, amplitude, wavelength, thickness, strand_a_level, strand_b_level
    )

    if start:
        start_date = date.fromisoformat(start)
    else:
        today = date.today()
        days_until_sun = (6 - today.weekday()) % 7
        start_date = today + timedelta(days=days_until_sun)

    end_date = start_date + timedelta(days=(num_weeks * 7 - 1))
    total_commits = sum(LEVEL_COMMITS[lvl] for row in grid for lvl in row)

    print("\nPreview (7 rows = Sun–Sat, glyph density = commit count):")
    print(_render(grid))

    print(f"\nDate range:    {start_date.isoformat()} .. {end_date.isoformat()}")
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
        "pattern": "dna",
        "meta": {
            "weeks": num_weeks,
            "amplitude": amplitude,
            "wavelength": wavelength,
            "thickness": thickness,
            "strand_a_level": strand_a_level,
            "strand_b_level": strand_b_level,
            "start_date": start_date.isoformat(),
            "level_commits": LEVEL_COMMITS,
            "preview": _glyph_str(grid),
        },
        "schedule": schedule,
    }
    _write_schedule(context["schedule_path"], data)
    print(f"Wrote schedule with {len(schedule)} days, {total_commits} total commits.")
