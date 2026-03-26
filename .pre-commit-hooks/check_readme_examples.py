#!/usr/bin/env python3

import re
import sys
from pathlib import Path
import fnmatch

TARGET_DIRS = ["python", "cpp", "csharp"]
HEADER = "## Included Examples"

SCRIPT_DIR = Path(__file__).parent
IGNORE_FILE = SCRIPT_DIR / ".check_readme_examples_ignore"


def load_ignore_patterns() -> list[str]:
    if not IGNORE_FILE.exists():
        return []
    return [
        line.strip()
        for line in IGNORE_FILE.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]


def is_ignored(path: Path, patterns: list[str], base: Path) -> bool:
    rel_path = path.relative_to(base).as_posix()

    for pat in patterns:
        pat = pat.strip()

        # Directory pattern (e.g. "bin/" or "*build*/")
        if pat.endswith("/"):
            dir_pat = pat.rstrip("/")
            if path.is_dir() and fnmatch.fnmatch(path.name, dir_pat):
                return True

        # General pattern (match anywhere in path)
        if fnmatch.fnmatch(rel_path, pat) or fnmatch.fnmatch(path.name, pat):
            return True

    return False


def get_section(text: str) -> str:
    match = re.search(rf"{HEADER}(.*?)(\n## |\Z)", text, re.S)
    return match.group(1) if match else ""


def parse_entries(section: str) -> set[str]:
    return set(re.findall(r"\[.*?\]\((.*?)\)", section))


def folder_has_relevant_items(folder: Path, ignore_patterns: list[str], base: Path) -> bool:
    for p in folder.iterdir():
        if not is_ignored(p, ignore_patterns, base):
            return True
    return False


def get_subfolders(path: Path, ignore_patterns: list[str]) -> set[str]:
    result = set()

    for p in path.iterdir():
        if not p.is_dir() or p.name.startswith("."):
            continue

        if is_ignored(p, ignore_patterns, path):
            continue

        if folder_has_relevant_items(p, ignore_patterns, path):
            result.add(p.name)

    return result


def check_directory(base: Path) -> bool:
    readme = base / "README.md"

    if not readme.exists():
        print(f"{base}: README.md not found")
        return True  # don't fail commit

    text = readme.read_text(encoding="utf-8")
    section = get_section(text)

    if not section:
        print(f"{base}: Missing '{HEADER}' section")
        return False

    ignore_patterns = load_ignore_patterns()

    readme_entries = parse_entries(section)
    actual_folders = get_subfolders(base, ignore_patterns)

    missing_in_readme = actual_folders - readme_entries
    missing_folders = readme_entries - actual_folders

    ok = True

    if missing_in_readme:
        print(f"{base}: Folders missing in README:")
        for f in sorted(missing_in_readme):
            print(f"   - {f}")
        ok = False

    if missing_folders:
        print(f"{base}: README references non-existing folders:")
        for f in sorted(missing_folders):
            print(f"   - {f}")
        ok = False

    return ok


def main() -> None:
    repo_root = Path.cwd()
    success = True

    for d in TARGET_DIRS:
        path = repo_root / d
        if path.exists():
            if not check_directory(path):
                success = False

    if not success:
        sys.exit(1)


if __name__ == "__main__":
    main()
