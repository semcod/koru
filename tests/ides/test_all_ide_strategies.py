"""Smoke tests: every supported autopilot IDE has a registered strategy."""

from __future__ import annotations

from pathlib import Path

import pytest

from koruide.ides import get_strategy, strategy_ids

_EXPECTED = frozenset(
    {
        "antigravity",
        "cursor",
        "jetbrains",
        "vscodium",
        "vscode",
        "windsurf",
        "zed",
    }
)


def test_all_supported_ides_registered() -> None:
    registered = frozenset(strategy_ids())
    assert _EXPECTED <= registered, f"missing strategies: {_EXPECTED - registered}"


@pytest.mark.parametrize(
    ("ide", "strict_ack", "vscode_plugin", "trusted"),
    [
        ("cursor", False, True, True),
        ("vscode", True, True, True),
        ("vscodium", True, True, True),
        ("windsurf", False, True, False),
        ("antigravity", False, True, False),
        ("jetbrains", False, False, False),
        ("zed", False, False, False),
    ],
)
def test_plugin_policy_flags(
    ide: str,
    strict_ack: bool,
    vscode_plugin: bool,
    trusted: bool,
) -> None:
    strategy = get_strategy(ide)
    assert strategy is not None
    assert strategy.plugin.strict_plugin_ack_required is strict_ack
    assert strategy.plugin.supports_vscode_extension is vscode_plugin
    assert strategy.plugin.requires_trusted_publisher is trusted


def test_vscodium_paths(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    from koru.ide_adapters import shared

    assert shared.config_home_for_ide("vscodium") == tmp_path / "VSCodium"
    ws = tmp_path / "proj" / ".vscode" / "settings.json"
    ws.parent.mkdir(parents=True)
    ws.write_text("{}\n", encoding="utf-8")
    assert shared.workspace_settings_path(tmp_path / "proj", "vscodium") == ws
