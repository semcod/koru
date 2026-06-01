#!/usr/bin/env python3
"""Bump koru version in pyproject.toml and package.json."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PYPROJECT = ROOT / "pyproject.toml"
PACKAGE_JSON = ROOT / "package.json"


def read_version() -> str:
    text = PYPROJECT.read_text(encoding="utf-8")
    match = re.search(r'^version\s*=\s*"([^"]+)"', text, re.MULTILINE)
    if not match:
        raise ValueError("version not found in pyproject.toml")
    return match.group(1)


def bump(version: str, part: str) -> str:
    major, minor, patch = (int(x) for x in version.split("."))
    if part == "major":
        return f"{major + 1}.0.0"
    if part == "minor":
        return f"{major}.{minor + 1}.0"
    if part == "patch":
        return f"{major}.{minor}.{patch + 1}"
    raise ValueError(f"Unknown bump part: {part!r}")


def update_pyproject(new_version: str, dry_run: bool) -> None:
    text = PYPROJECT.read_text(encoding="utf-8")
    updated = re.sub(
        r'^version\s*=\s*"[^"]+"',
        f'version = "{new_version}"',
        text,
        count=1,
        flags=re.MULTILINE,
    )
    if not dry_run:
        PYPROJECT.write_text(updated, encoding="utf-8")
    print(f"  {'[dry-run] ' if dry_run else ''}pyproject.toml → {new_version}")


def update_package_json(new_version: str, dry_run: bool) -> None:
    if not PACKAGE_JSON.is_file():
        return
    text = PACKAGE_JSON.read_text(encoding="utf-8")
    updated = re.sub(
        r'("version"\s*:\s*")[^"]+(")',
        rf"\g<1>{new_version}\g<2>",
        text,
        count=1,
    )
    if not dry_run:
        PACKAGE_JSON.write_text(updated, encoding="utf-8")
    print(f"  {'[dry-run] ' if dry_run else ''}package.json   → {new_version}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Semantic version bump for koru")
    parser.add_argument("part", nargs="?", choices=["major", "minor", "patch"])
    parser.add_argument("--show", action="store_true", help="Print current version")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    current = read_version()
    if args.show:
        print(current)
        return

    if not args.part:
        parser.error("Specify bump part: major | minor | patch")

    new_version = bump(current, args.part)
    print(f"Bumping koru {current} → {new_version} ({args.part})")
    update_pyproject(new_version, args.dry_run)
    update_package_json(new_version, args.dry_run)
    if args.dry_run:
        print("[dry-run] No files modified.")
    else:
        print(f"✓ Version is now {new_version}")


if __name__ == "__main__":
    try:
        main()
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)
