#!/usr/bin/env python3
"""Sync per-IDE plugin version metadata.

Each per-IDE plugin (``plugins/koru-autopilot-<ide>/package.json``)
declares its own VSIX version. This script keeps the daemon-side
``EXPECTED_PLUGIN_VERSIONS`` table in
``packages/koruide/src/koruide/plugin_version.py`` aligned with whichever plugin we
just rebuilt — without touching the other plugin entries.

It replaces the legacy ``sync-vscode-plugin-version.py`` which
assumed a single VS Code-family VSIX and would cross-update Cursor
when a VS Code build bumped its version.

Usage:
    # Sync from a specific plugin's package.json (typical prepackage hook):
    python3 scripts/sync-plugin-version.py --plugin koru-autopilot-cursor
    python3 scripts/sync-plugin-version.py --plugin koru-autopilot-vscode

    # Or specify the IDE id directly:
    python3 scripts/sync-plugin-version.py --ide cursor

The plugin directory and IDE id are linked via the table below.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

# plugin dir name → IDE id used inside plugin_version.py and the
# daemon-side ``expected_plugin_version_for_ide()`` lookup.
PLUGIN_DIR_TO_IDE: dict[str, str] = {
    "koru-autopilot-cursor": "cursor",
    "koru-autopilot-vscode": "vscode",
    "koru-autopilot-vscodium": "vscodium",
    "koru-autopilot-windsurf": "windsurf",
    "koru-autopilot-antigravity": "antigravity",
}
IDE_TO_PLUGIN_DIR: dict[str, str] = {ide: dir_name for dir_name, ide in PLUGIN_DIR_TO_IDE.items()}


def _read_package_version(plugin_dir: Path) -> str:
    package_json = plugin_dir / "package.json"
    data = json.loads(package_json.read_text(encoding="utf-8"))
    version = data.get("version")
    if not version:
        raise ValueError(f"missing 'version' in {package_json}")
    return str(version)


def _update_expected_versions(ide_id: str, version: str) -> bool:
    """Patch only the ``"<ide>": "<version>"`` entry in
    ``EXPECTED_PLUGIN_VERSIONS``. Returns True when the file changed."""

    version_file = (
        REPO_ROOT / "packages" / "koruide" / "src" / "koruide" / "plugin_version.py"
    )
    content = version_file.read_text(encoding="utf-8")
    pattern = rf'("{re.escape(ide_id)}"\s*:\s*")[^"]+(")'
    updated, count = re.subn(pattern, rf"\g<1>{version}\g<2>", content, count=1)
    if count == 0:
        print(
            f"  ⚠ EXPECTED_PLUGIN_VERSIONS['{ide_id}'] entry not found in "
            f"{version_file} (skipping)",
            file=sys.stderr,
        )
        return False
    if content == updated:
        print(f"  ✓ plugin_version.py[{ide_id}] already at {version}")
        return False
    version_file.write_text(updated, encoding="utf-8")
    print(f"  ✓ Updated plugin_version.py[{ide_id}] to {version}")
    return True


def _update_workflow_version(version: str) -> None:
    """Keep the GitHub Actions matrix in sync with the VS Code-family VSIX
    (only the umbrella plugin drives matrix tests; per-IDE plugins reuse
    the same fake-extension version for now)."""

    workflow_file = REPO_ROOT / ".github" / "workflows" / "native-ide-matrix.yml"
    if not workflow_file.is_file():
        return
    content = workflow_file.read_text(encoding="utf-8")
    updated = re.sub(
        r'KORU_FAKE_EXTENSION_VERSION",\s*"([^"]+)"',
        f'KORU_FAKE_EXTENSION_VERSION", "{version}"',
        content,
    )
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
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--plugin",
        help="Plugin directory name (e.g. koru-autopilot-cursor)",
    )
    group.add_argument(
        "--ide",
        help="IDE id (e.g. cursor, vscode, vscodium, windsurf, antigravity)",
    )
    args = parser.parse_args()

    if args.plugin:
        plugin_dir_name = args.plugin
        ide_id = PLUGIN_DIR_TO_IDE.get(plugin_dir_name)
    elif args.ide:
        ide_id = args.ide.lower()
        plugin_dir_name = IDE_TO_PLUGIN_DIR.get(ide_id)
    else:
        parser.error("either --plugin or --ide is required")

    if not plugin_dir_name or not ide_id:
        print(
            f"unknown plugin/ide; valid plugins: {list(PLUGIN_DIR_TO_IDE)}",
            file=sys.stderr,
        )
        return 1

    plugin_dir = REPO_ROOT / "plugins" / plugin_dir_name
    if not plugin_dir.is_dir():
        print(f"plugin dir not found: {plugin_dir}", file=sys.stderr)
        return 1

    version = _read_package_version(plugin_dir)
    print(f"Syncing {plugin_dir_name} (ide={ide_id}) → version {version}")
    _update_expected_versions(ide_id, version)
    # Only the umbrella VS Code-family build drives the CI matrix env var.
    if ide_id == "vscode":
        _update_workflow_version(version)
    return 0


if __name__ == "__main__":
    sys.exit(main())
