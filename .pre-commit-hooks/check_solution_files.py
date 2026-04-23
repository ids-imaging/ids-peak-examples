#!/usr/bin/env python3

import sys
import re
from pathlib import Path
from collections import defaultdict
from typing import DefaultDict, Set

CONFIG_LINE_RE = re.compile(r'^\s*([^=]+?)\s*=\s*([^=]+?)\s*$')
GUID_PREFIX_RE = re.compile(r'^\{([A-Fa-f0-9\-]+)\}\.')
PROJECT_LINE_RE = re.compile(r'^Project\(.*\)\s*=\s*".*?",\s*".*?",\s*"\{([A-Fa-f0-9\-]+)\}"')
SUFFIX_RE = re.compile(r'\.(ActiveCfg|Build\.0)$')

ALLOWED_PLATFORMS = {"x86", "x64", "ARM32", "ARM64", "Any CPU"}


def normalize_left(value: str) -> str:
    value = value.strip()
    value = GUID_PREFIX_RE.sub('', value)
    value = SUFFIX_RE.sub('', value)
    return value.strip()


def extract_guid_prefix(value: str) -> str | None:
    match = GUID_PREFIX_RE.match(value.strip())
    return match.group(1) if match else None


def extract_platform(config: str) -> str | None:
    """
    Extracts platform from 'Config|Platform'
    """
    if "|" not in config:
        return None
    return config.split("|", 1)[1].strip()


def validate_platform(config: str, path: Path, lineno: int, errors: list) -> None:
    platform = extract_platform(config)
    if platform is None:
        errors.append(f"{path}:{lineno} -> invalid config format: '{config}'")
        return

    if platform not in ALLOWED_PLATFORMS:
        errors.append(
            f"{path}:{lineno} -> invalid platform '{platform}' (allowed: {sorted(ALLOWED_PLATFORMS)})"
        )


def check_sln_file(path: Path) -> int:
    errors = []

    solution_configs = set()
    project_configs: DefaultDict[str, DefaultDict[str, Set[str]]] = defaultdict(
        lambda: defaultdict(set)
    )

    project_guids = []
    project_stack = []

    inside_solution_section = False
    inside_project_section = False

    with path.open("r", encoding="utf-8") as f:
        for lineno, line in enumerate(f, 1):
            stripped = line.strip()

            # ---- Project / EndProject tracking ----
            proj_match = PROJECT_LINE_RE.match(stripped)
            if proj_match:
                guid = proj_match.group(1)
                project_guids.append(guid)
                project_stack.append((guid, lineno))
                continue

            if stripped == "EndProject":
                if not project_stack:
                    errors.append(f"{path}:{lineno} -> EndProject without matching Project")
                else:
                    project_stack.pop()
                continue

            # ---- Section tracking ----
            if stripped.startswith("GlobalSection(SolutionConfigurationPlatforms)"):
                inside_solution_section = True
                continue

            if stripped.startswith("GlobalSection(ProjectConfigurationPlatforms)"):
                inside_project_section = True
                continue

            if stripped.startswith("EndGlobalSection"):
                inside_solution_section = False
                inside_project_section = False
                continue

            # Only process config lines inside relevant sections
            if not (inside_solution_section or inside_project_section):
                continue

            match = CONFIG_LINE_RE.match(line)
            if not match:
                continue

            left_raw, right_raw = match.groups()
            left_norm = normalize_left(left_raw)
            right_norm = right_raw.strip()

            # ---- Equality check ----
            if left_norm != right_norm:
                errors.append(
                    f"{path}:{lineno} -> mismatch: '{left_norm}' != '{right_norm}'"
                )

            # ---- Platform validation ----
            validate_platform(left_norm, path, lineno, errors)

            # ---- Collect solution configs ----
            if inside_solution_section:
                solution_configs.add(left_norm)

            # ---- Collect project configs ----
            if inside_project_section:
                guid = extract_guid_prefix(left_raw)
                if guid:
                    # Extract config and type
                    left_clean = left_raw.strip()
                    left_clean = GUID_PREFIX_RE.sub('', left_clean)

                    config = SUFFIX_RE.sub('', left_clean).strip()

                    suffix_match = re.search(r'\.(ActiveCfg|Build\.0)$', left_clean)
                    if suffix_match:
                        cfg_type = suffix_match.group(1)
                        project_configs[guid][config].add(cfg_type)

    # ---- Unmatched Project ----
    for guid, lineno in project_stack:
        errors.append(f"{path}:{lineno} -> Project without matching EndProject ({guid})")

    # ---- Project presence & completeness ----
    for guid in project_guids:
        if guid not in project_configs:
            errors.append(f"{path} -> Project {guid} missing from ProjectConfigurationPlatforms")
            continue

        for config in solution_configs:
            types = project_configs[guid].get(config, set())

            if "ActiveCfg" not in types:
                errors.append(
                    f"{path} -> Project {guid} missing ActiveCfg for {config}"
                )

            if "Build.0" not in types:
                errors.append(
                    f"{path} -> Project {guid} missing Build.0 for {config}"
                )

    # ---- Output ----
    for err in errors:
        print(err)

    return 1 if errors else 0


def main() -> int:
    files = [Path(p) for p in sys.argv[1:] if p.endswith(".sln")]

    if not files:
        return 0

    exit_code = 0
    for file in files:
        exit_code |= check_sln_file(file)

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
