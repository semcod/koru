#!/usr/bin/env python3
"""Copy ``plugins/koru-autopilot-shared/src/*`` into each per-IDE plugin's
``src/_shared/`` directory.

Per-IDE plugins are independent VSIX packages so a regression in one
plugin cannot leak into another. They share a small handful of truly
stable utilities (NDJSON envelope sanitization, socket path resolution,
host-OS click point math) — duplicating those would be a maintenance
trap, so we centralise them in ``koru-autopilot-shared`` and copy the
files into each plugin's ``src/_shared/`` at prebuild time.

Run this directly:

    python3 scripts/sync-plugin-shared.py

Or via the root ``package.json`` script::

    npm run sync-shared

The destination directory is wiped before each copy so renamed/deleted
shared files do not leave stale artefacts behind. ``src/_shared/`` is
listed in each plugin's ``.gitignore``.
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SHARED_SRC = REPO_ROOT / "plugins" / "koru-autopilot-shared" / "src"
PLUGINS_DIR = REPO_ROOT / "plugins"

# Plugins that consume the shared bundle. ``koru-autopilot-shared`` and
# the JetBrains plugin (different language/runtime) are excluded.
TARGET_PLUGINS = (
    "koru-autopilot-cursor",
    "koru-autopilot-vscode",
    "koru-autopilot-vscodium",
    "koru-autopilot-windsurf",
    "koru-autopilot-antigravity",
)


def _sync_one(plugin_dir: Path) -> bool:
    """Mirror ``SHARED_SRC`` into ``plugin_dir / src / _shared``.

    Uses a symlink when the platform supports it (avoids code2llm
    duplicate-file noise) and falls back to a plain copy on Windows
    or when symlinks require privileges.

    Returns ``True`` if the plugin exists and was synced; ``False`` if
    the plugin directory is absent (allowed during partial rollouts).
    """

    src_root = plugin_dir / "src"
    if not src_root.exists():
        return False
    dest = src_root / "_shared"
    if dest.is_symlink():
        dest.unlink()
    elif dest.exists():
        shutil.rmtree(dest)

    try:
        dest.symlink_to(SHARED_SRC.resolve(), target_is_directory=True)
    except OSError:
        # Windows or other platforms where symlinks need privileges
        shutil.copytree(SHARED_SRC, dest)
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--plugin",
        action="append",
        default=None,
        help="Limit to a specific plugin directory name (repeatable). "
        "Defaults to every known per-IDE plugin.",
    )
    args = parser.parse_args()

    if not SHARED_SRC.exists():
        print(f"shared src dir missing: {SHARED_SRC}", file=sys.stderr)
        return 1

    targets = tuple(args.plugin) if args.plugin else TARGET_PLUGINS
    synced = []
    skipped = []
    for name in targets:
        plugin = PLUGINS_DIR / name
        if _sync_one(plugin):
            synced.append(name)
        else:
            skipped.append(name)

    for name in synced:
        print(f"synced shared → plugins/{name}/src/_shared/")
    for name in skipped:
        print(f"skipped (not present yet): plugins/{name}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
