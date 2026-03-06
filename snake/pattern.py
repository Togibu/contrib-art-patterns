from __future__ import annotations

import random
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import yaml


def _write_schedule(path: Path, data: dict[str, Any]) -> None:
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")


def _generate_snake(num_weeks: int, seed: int | None = None, wrap: bool = False) -> list[list[bool]]:
    rng = random.Random(seed)
    grid = [[False] * num_weeks for _ in range(7)]
    visited: set[tuple[int, int]] = set()

    # 0=right, 1=down, 2=left, 3=up
    DIRS = [(0, 1), (1, 0), (0, -1), (-1, 0)]
    IS_HORIZ = {0: True, 1: False, 2: True, 3: False}

    def next_pos(r: int, c: int, dr: int, dc: int) -> tuple[int, int]:
        nr = (r + dr) % 7 if wrap else r + dr
        return nr, c + dc

    def mark(r: int, c: int) -> bool:
        if 0 <= r < 7 and 0 <= c < num_weeks and (r, c) not in visited:
            grid[r][c] = True
            visited.add((r, c))
            return True
        return False

    def count_reachable(start_r: int, start_c: int) -> int:
        """How many unvisited cells are reachable from (start_r, start_c)?"""
        seen: set[tuple[int, int]] = set()
        stack = [(start_r, start_c)]
        while stack:
            cr, cc = stack.pop()
            if (cr, cc) in seen:
                continue
            seen.add((cr, cc))
            for dr, dc in DIRS:
                nr, nc = next_pos(cr, cc, dr, dc)
                if 0 <= nr < 7 and 0 <= nc < num_weeks and (nr, nc) not in visited and (nr, nc) not in seen:
                    stack.append((nr, nc))
        return len(seen)

    def choose_direction(r: int, c: int, options: list[int]) -> int:
        if len(options) == 1:
            return options[0]
        # Score each option by how many cells remain reachable afterwards
        scores = []
        for d in options:
            dr, dc = DIRS[d]
            nr, nc = next_pos(r, c, dr, dc)
            scores.append(count_reachable(nr, nc))
        # Pick randomly among the options that keep at least 70% of max reachable space
        max_score = max(scores)
        good = [d for d, s in zip(options, scores) if s >= max_score * 0.7]
        return rng.choice(good)

    row = rng.randint(0, 4)
    col = 0
    mark(row, col)
    direction = 0  # start right

    while True:
        run = rng.randint(3, 12) if IS_HORIZ[direction] else rng.randint(2, 5)
        dr, dc = DIRS[direction]
        for _ in range(run):
            nr, nc = next_pos(row, col, dr, dc)
            if not mark(nr, nc):
                break
            row, col = nr, nc

        # Prefer 90-degree turns; fall back to straight if needed
        left_turn = (direction - 1) % 4
        right_turn = (direction + 1) % 4

        available = []
        for d in [left_turn, right_turn]:
            dr2, dc2 = DIRS[d]
            nr, nc = next_pos(row, col, dr2, dc2)
            if 0 <= nr < 7 and 0 <= nc < num_weeks and (nr, nc) not in visited:
                available.append(d)

        if not available:
            dr2, dc2 = DIRS[direction]
            nr, nc = next_pos(row, col, dr2, dc2)
            if 0 <= nr < 7 and 0 <= nc < num_weeks and (nr, nc) not in visited:
                available.append(direction)

        if not available:
            break

        direction = choose_direction(row, col, available)

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
    commits_str = input("Commits per filled cell [1]: ").strip()
    commits_per_fill = int(commits_str) if commits_str else 1
    seed_str = input("Random seed (blank=random): ").strip()
    seed = int(seed_str) if seed_str else None
    wrap_str = input("Wrap vertically? [y/N]: ").strip().lower()
    wrap = wrap_str in ("y", "yes")

    grid = _generate_snake(num_weeks, seed, wrap=wrap)

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
            "wrap": wrap,
            "preview": preview_str,
        },
        "schedule": schedule,
    }
    _write_schedule(context["schedule_path"], data)
    print(f"Wrote schedule with {len(schedule)} days.")
