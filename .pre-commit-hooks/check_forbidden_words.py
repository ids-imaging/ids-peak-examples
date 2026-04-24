#!/usr/bin/env python3

import sys
import re
from pathlib import Path
from typing import List, Pattern

# ---- Config ----
FORBIDDEN_WORDS: List[str] = [
    "sample",
    "samples",
    "todo",
]

CASE_INSENSITIVE: bool = True
# ----------------


def build_pattern(words: List[str]) -> Pattern[str]:
    escaped = [re.escape(word) for word in words]
    pattern = r"\b(" + "|".join(escaped) + r")\b"
    flags = re.IGNORECASE if CASE_INSENSITIVE else 0
    return re.compile(pattern, flags)


def check_file(path: Path, pattern: Pattern[str]) -> int:
    errors: List[str] = []

    try:
        lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    except Exception as e:
        print(f"{path}: could not read file ({e})")
        return 1

    for lineno, line in enumerate(lines, 1):
        matches = pattern.findall(line)
        if matches:
            found = ", ".join(sorted(set(matches)))
            errors.append(f"{path}:{lineno} -> forbidden word(s): {found}")

    for err in errors:
        print(err)

    return 1 if errors else 0


def main() -> int:
    pattern = build_pattern(FORBIDDEN_WORDS)

    script_name = Path(__file__).name

    files: List[Path] = [
        Path(p)
        for p in sys.argv[1:]
        if Path(p).name != script_name
    ]

    if not files:
        return 0

    exit_code = 0
    for file in files:
        exit_code |= check_file(file, pattern)

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
