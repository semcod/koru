"""Bundled IDE plugin version metadata.

Each per-IDE VSIX (``plugins/koru-autopilot-<ide>/``) is built and
versioned independently so a regression in one plugin cannot ride
along with another's release. The mapping below is the daemon-side
contract that the strict version check uses to reject any IDE
connection whose ``hello`` envelope reports a stale version.

The legacy ``EXPECTED_VSCODE_PLUGIN_VERSION`` constant is kept as an
alias for backward compatibility with code that has not migrated to
``expected_plugin_version_for_ide(...)`` yet.
"""

from __future__ import annotations

# Each per-IDE plugin tracks its own version. When you bump a plugin,
# bump only the matching entry — do NOT lockstep all IDEs.
EXPECTED_PLUGIN_VERSIONS: dict[str, str] = {
    "cursor": "0.2.27",
    "vscode": "0.2.4",
    "vscodium": "0.2.27",
    "windsurf": "0.2.5",
    "antigravity": "0.2.11",
}

# Legacy alias: points at the VS Code-only umbrella plugin.
EXPECTED_VSCODE_PLUGIN_VERSION = EXPECTED_PLUGIN_VERSIONS["vscode"]


def expected_plugin_version_for_ide(ide_id: str | None) -> str:
    """Return the expected VSIX version for ``ide_id``.

    Unknown / missing IDE falls back to the umbrella plugin version so
    legacy callers that pass ``None`` keep their previous behaviour.
    """

    if not ide_id:
        return EXPECTED_VSCODE_PLUGIN_VERSION
    return EXPECTED_PLUGIN_VERSIONS.get(ide_id.lower(), EXPECTED_VSCODE_PLUGIN_VERSION)


__all__ = [
    "EXPECTED_PLUGIN_VERSIONS",
    "EXPECTED_VSCODE_PLUGIN_VERSION",
    "expected_plugin_version_for_ide",
]
