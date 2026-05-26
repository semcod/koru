#!/usr/bin/env python3
"""Write deterministic autopilot plugin build metadata into package.json."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
PLUGINS_ROOT = REPO_ROOT / "plugins"
SHARED_SRC = PLUGINS_ROOT / "koru-autopilot-shared" / "src"

EXCLUDED_DIRS = {"node_modules", "out", ".git", ".planfile"}
EXCLUDED_SUFFIXES = {".vsix"}


def _iter_hash_files(plugin_dir: Path) -> list[Path]:
    roots = [plugin_dir / "src", SHARED_SRC]
    files: list[Path] = []
    for root in roots:
        if not root.is_dir():
            continue
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            rel = path.relative_to(plugin_dir if path.is_relative_to(plugin_dir) else REPO_ROOT)
            if any(part in EXCLUDED_DIRS for part in rel.parts):
                continue
            if len(rel.parts) >= 2 and rel.parts[0] == "src" and rel.parts[1] == "_shared":
                continue
            if path.suffix in EXCLUDED_SUFFIXES:
                continue
            files.append(path)
    package_json = plugin_dir / "package.json"
    if package_json.is_file():
        files.append(package_json)
    return sorted(set(files))


def _package_without_build_metadata(package_json: Path) -> bytes:
    data = json.loads(package_json.read_text(encoding="utf-8"))
    if isinstance(data, dict):
        data.pop("koruAutopilotBuild", None)
    return json.dumps(data, sort_keys=True, separators=(",", ":")).encode("utf-8")


def compute_build_sha(plugin_dir: Path) -> str:
    digest = hashlib.sha256()
    for path in _iter_hash_files(plugin_dir):
        rel = path.relative_to(REPO_ROOT).as_posix()
        digest.update(rel.encode("utf-8"))
        digest.update(b"\0")
        if path.name == "package.json" and path.parent == plugin_dir:
            digest.update(_package_without_build_metadata(path))
        else:
            digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()[:16]


def update_package(plugin_dir: Path) -> bool:
    package_json = plugin_dir / "package.json"
    data: dict[str, Any] = json.loads(package_json.read_text(encoding="utf-8"))
    sha = compute_build_sha(plugin_dir)
    build = data.get("koruAutopilotBuild")
    if not isinstance(build, dict):
        build = {}
    new_build = {
        **build,
        "schema": 1,
        "sha": sha,
    }
    if data.get("koruAutopilotBuild") == new_build:
        print(f"  ✓ {plugin_dir.name} build sha already {sha}")
        return False
    data["koruAutopilotBuild"] = new_build
    package_json.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    print(f"  ✓ Updated {plugin_dir.name} build sha to {sha}")
    return True


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plugin", help="Plugin directory name, e.g. koru-autopilot-vscodium")
    args = parser.parse_args()
    names = [args.plugin] if args.plugin else [
        path.name for path in sorted(PLUGINS_ROOT.glob("koru-autopilot-*"))
        if (path / "package.json").is_file() and path.name != "koru-autopilot-shared"
    ]
    for name in names:
        plugin_dir = PLUGINS_ROOT / name
        if not plugin_dir.is_dir():
            raise SystemExit(f"unknown plugin directory: {plugin_dir}")
        update_package(plugin_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
