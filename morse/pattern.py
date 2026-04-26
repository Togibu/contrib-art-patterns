from __future__ import annotations

import sys
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import yaml


GLYPHS = ["·", "░", "▒", "▓", "█"]
COLORS_256 = [238, 22, 28, 34, 40]
LEVEL_COMMITS = [0, 1, 3, 5, 8]


MORSE: dict[str, str] = {
    "A": ".-",   "B": "-...", "C": "-.-.", "D": "-..",  "E": ".",
    "F": "..-.", "G": "--.",  "H": "....", "I": "..",   "J": ".---",
    "K": "-.-",  "L": ".-..", "M": "--",   "N": "-.",   "O": "---",
    "P": ".--.", "Q": "--.-", "R": ".-.",  "S": "...",  "T": "-",
    "U": "..-",  "V": "...-", "W": ".--",  "X": "-..-", "Y": "-.--",
    "Z": "--..",
    "0": "-----","1": ".----","2": "..---","3": "...--","4": "....-",
    "5": ".....","6": "-....","7": "--...","8": "---..","9": "----.",
    ".": ".-.-.-", ",": "--..--", "?": "..--..", "!": "-.-.--",
    "/": "-..-.", ":": "---...", ";": "-.-.-.", "=": "-...-",
    "+": ".-.-.", "-": "-....-", "@": ".--.-.", "(": "-.--.",
    ")": "-.--.-", "'": ".----.", '"': ".-..-.",
}


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


def _required_columns(message: str) -> int:
    """How many columns the encoded message needs."""
    cols = 0
    msg = message.upper()
    for word_idx, word in enumerate(msg.split()):
        if word_idx > 0:
            cols += 7  # word gap
        for letter_idx, char in enumerate(word):
            if char not in MORSE:
                continue
            if letter_idx > 0:
                cols += 3  # letter gap
            morse = MORSE[char]
            for sym_idx, symbol in enumerate(morse):
                if sym_idx > 0:
                    cols += 1  # intra-letter gap
                cols += 1 if symbol == "." else 3
    return cols


def _generate_morse(
    num_weeks: int,
    message: str,
    level: int,
    top_row: int,
    bot_row: int,
) -> tuple[list[list[int]], int, int]:
    """
    Encode `message` into the grid, occupying rows top_row..bot_row inclusive.
    Each dot = 1 col, dash = 3 cols, intra-letter gap = 1 col, letter gap = 3, word gap = 7.
    Returns (grid, characters_drawn, total_characters).
    Truncates silently at num_weeks; the run() caller warns.
    """
    grid = [[0] * num_weeks for _ in range(7)]
    col = 0
    drawn = 0
    msg = message.upper()
    total_chars = sum(1 for w in msg.split() for ch in w if ch in MORSE)

    for word_idx, word in enumerate(msg.split()):
        if word_idx > 0:
            col += 7
            if col >= num_weeks:
                return grid, drawn, total_chars
        for letter_idx, char in enumerate(word):
            if char not in MORSE:
                continue
            if letter_idx > 0:
                col += 3
            morse = MORSE[char]
            letter_start = col
            fits = True
            for sym_idx, symbol in enumerate(morse):
                if sym_idx > 0:
                    col += 1
                width = 1 if symbol == "." else 3
                if col + width > num_weeks:
                    fits = False
                    break
                for c2 in range(col, col + width):
                    for r in range(top_row, bot_row + 1):
                        grid[r][c2] = level
                col += width
            if not fits:
                # Roll back partial letter
                for c2 in range(letter_start, num_weeks):
                    for r in range(top_row, bot_row + 1):
                        grid[r][c2] = 0
                return grid, drawn, total_chars
            drawn += 1

    return grid, drawn, total_chars


def run(context: dict[str, Any]) -> None:
    print("Morse pattern generator")

    message = input("Message to encode: ").strip()
    if not message:
        print("Aborted (empty message).")
        return

    num_weeks = _required_columns(message)
    if num_weeks == 0:
        print("Aborted (no encodable characters in message).")
        return

    level_str = input("Brightness level (1–4) [4]: ").strip()
    level = int(level_str) if level_str else 4
    level = max(1, min(4, level))

    print("\nVertical layout:")
    print("  [1] Center 3 rows (rows 2–4)")
    print("  [2] All 7 rows (full column fill — most visible)")
    print("  [3] Single row (row 3 only — most compact)")
    layout_choice = input("Choice [1/2/3] [1]: ").strip() or "1"
    if layout_choice == "2":
        top_row, bot_row = 0, 6
    elif layout_choice == "3":
        top_row, bot_row = 3, 3
    else:
        top_row, bot_row = 2, 4

    start = input("Start date for first column (Sunday) [YYYY-MM-DD, blank=next Sunday]: ").strip()

    grid, drawn, total = _generate_morse(num_weeks, message, level, top_row, bot_row)

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

    print(f"\nMessage:       {message.upper()}")
    print(f"Width:         {num_weeks} weeks (auto-sized for message)")
    print(f"Date range:    {start_date.isoformat()} .. {end_date.isoformat()}")
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
            lvl = grid[r][col]
            if lvl > 0:
                day = start_date + timedelta(days=(col * 7 + r))
                schedule[day.isoformat()] = LEVEL_COMMITS[lvl]

    data = {
        "pattern": "morse",
        "meta": {
            "message": message.upper(),
            "weeks": num_weeks,
            "level": level,
            "rows": [top_row, bot_row],
            "encoded_chars": drawn,
            "total_chars": total,
            "start_date": start_date.isoformat(),
            "level_commits": LEVEL_COMMITS,
            "preview": _glyph_str(grid),
        },
        "schedule": schedule,
    }
    _write_schedule(context["schedule_path"], data)
    print(f"Wrote schedule with {len(schedule)} days, {total_commits} total commits.")
