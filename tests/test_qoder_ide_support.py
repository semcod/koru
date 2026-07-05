"""Qoder (VS Code fork) is a first-class autopilot IDE."""

from __future__ import annotations

from koruide.ide import (
    _IDE_SIGNATURES,
    _matches,
    ide_binary_candidates,
    normalize_ide_id,
    vscode_extension_plugin_ide_ids,
)
from koruide.plugin_installer import (
    _EXTENSION_IDS,
    _IDE_COMMANDS,
    SUPPORTED_IDES,
    plugin_dir_names_for_ide,
)


def test_qoder_signature_matches_real_process() -> None:
    patterns, label = _IDE_SIGNATURES["qoder"]
    assert label == "Qoder"
    # comm of the running Electron main process
    assert _matches("Qoder", "/home/tom/.qoder/shared_client/bin/0.19.5/x86_64_linux/Qoder start", patterns)


def test_qoder_signature_ignores_qoderwake_daemon() -> None:
    patterns, _ = _IDE_SIGNATURES["qoder"]
    assert not _matches(
        "qoderwake", "/home/tom/.qoderwake/qoderwake __daemon --host 127.0.0.1 --port 19820", patterns
    )


def test_qoder_is_vscode_extension_family() -> None:
    assert "qoder" in vscode_extension_plugin_ide_ids()
    assert "qoder" in SUPPORTED_IDES


def test_qoder_alias_and_binaries() -> None:
    assert normalize_ide_id("qoder") == "qoder"
    assert "qoder" in ide_binary_candidates("qoder")


def test_qoder_plugin_install_mappings() -> None:
    # falls back to the umbrella VS Code VSIX until a dedicated build exists
    assert plugin_dir_names_for_ide("qoder") == ("koru-autopilot-qoder", "koru-autopilot-vscode")
    assert _EXTENSION_IDS["qoder"] == "semcod.koru-autopilot-vscode"
    assert _IDE_COMMANDS["qoder"][0] == "qoder"
