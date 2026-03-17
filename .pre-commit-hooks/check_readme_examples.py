#!/usr/bin/env python3

import re
import sys
from pathlib import Path

TARGET_DIRS = ["python", "cpp", "csharp"]
HEADER = "## Included Examples"


def get_section(text: str) -> str:
    match = re.search(rf"{HEADER}(.*?)(\n## |\Z)", text, re.S)
    return match.group(1) if match else ""


def parse_entries(section: str) -> set[str]:
    return set(re.findall(r"\[.*?\]\((.*?)\)", section))


def get_subfolders(path: Path) -> set[str]:
    return {
        p.name
        for p in path.iterdir()
        if p.is_dir() and not p.name.startswith(".")
    }


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

    readme_entries = parse_entries(section)
    actual_folders = get_subfolders(base)

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
