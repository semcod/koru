#!/usr/bin/env python3
"""Sync VSCode plugin version across all files.

Source of truth: src/koruide/plugin_version.py
Targets:
- plugins/koru-autopilot-vscode/package.json
- .github/workflows/native-ide-matrix.yml

Usage:
    python3 scripts/sync-vscode-plugin-version.py           # sync from plugin_version.py
    python3 scripts/sync-vscode-plugin-version.py --from-package  # sync from package.json
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


def get_plugin_version_from_source(root: Path) -> str:
    """Read the plugin version from the source of truth."""
    version_file = root / "src" / "koruide" / "plugin_version.py"
    content = version_file.read_text(encoding="utf-8")
    match = re.search(r'EXPECTED_VSCODE_PLUGIN_VERSION\s*=\s*"([^"]+)"', content)
    if not match:
        raise ValueError(f"Could not find EXPECTED_VSCODE_PLUGIN_VERSION in {version_file}")
    return match.group(1)


def get_plugin_version_from_package(root: Path) -> str:
    """Read the plugin version from package.json."""
    package_json = root / "plugins" / "koru-autopilot-vscode" / "package.json"
    content = package_json.read_text(encoding="utf-8")
    match = re.search(r'"version":\s*"([^"]+)"', content)
    if not match:
        raise ValueError(f"Could not find version in {package_json}")
    return match.group(1)


def update_plugin_version_source(version: str, root: Path) -> None:
    """Update the version in plugin_version.py."""
    version_file = root / "src" / "koruide" / "plugin_version.py"
    content = version_file.read_text(encoding="utf-8")
    updated = re.sub(
        r'EXPECTED_VSCODE_PLUGIN_VERSION\s*=\s*"([^"]+)"',
        f'EXPECTED_VSCODE_PLUGIN_VERSION = "{version}"',
        content,
    )
    if content == updated:
        print(f"  ✓ plugin_version.py already at version {version}")
    else:
        version_file.write_text(updated, encoding="utf-8")
        print(f"  ✓ Updated plugin_version.py to {version}")


def update_package_json(version: str, root: Path) -> None:
    """Update the version in package.json."""
    package_json = root / "plugins" / "koru-autopilot-vscode" / "package.json"
    content = package_json.read_text(encoding="utf-8")
    updated = re.sub(r'"version":\s*"[^"]+"', f'"version": "{version}"', content)
    if content == updated:
        print(f"  ✓ package.json already at version {version}")
    else:
        package_json.write_text(updated, encoding="utf-8")
        print(f"  ✓ Updated package.json to {version}")


def update_github_workflow(version: str, root: Path) -> None:
    """Update the version in GitHub workflow file."""
    workflow_file = root / ".github" / "workflows" / "native-ide-matrix.yml"
    content = workflow_file.read_text(encoding="utf-8")
    
    # Update the default version in the Python script
    updated = re.sub(
        r'KORU_FAKE_EXTENSION_VERSION",\s*"([^"]+)"',
        f'KORU_FAKE_EXTENSION_VERSION", "{version}"',
        content,
    )
    
    # Update the env var values
    updated = re.sub(
        r'KORU_FAKE_EXTENSION_VERSION:\s*"([^"]+)"',
        f'KORU_FAKE_EXTENSION_VERSION: "{version}"',
        updated,
    )
    
    if content == updated:
        print(f"  ✓ native-ide-matrix.yml already at version {version}")
    else:
        workflow_file.write_text(updated, encoding="utf-8")
        print(f"  ✓ Updated native-ide-matrix.yml to {version}")


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Sync VSCode plugin version across all files")
    parser.add_argument(
        "--from-package",
        action="store_true",
        help="Read version from package.json instead of plugin_version.py",
    )
    args = parser.parse_args()
    
    root = Path(__file__).resolve().parents[1]
    
    if args.from_package:
        version = get_plugin_version_from_package(root)
        print(f"Syncing VSCode plugin version from package.json: {version}...")
        update_plugin_version_source(version, root)
    else:
        version = get_plugin_version_from_source(root)
        print(f"Syncing VSCode plugin version from plugin_version.py: {version}...")
    
    update_package_json(version, root)
    update_github_workflow(version, root)
    
    print("\nAll files synced successfully!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
