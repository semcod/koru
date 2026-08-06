"""Contract tests for :class:`CursorStrategy`.

These tests must depend ONLY on :mod:`koruide.ides.cursor` and the strategy
ABC. They must not import :mod:`koru.autonomous_cycle`, the daemon, or other
IDEs' modules — that isolation is the whole point of the per-IDE split.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from koruide.ides import get_strategy, strategy_ids
from koruide.ides.base import IdeStrategy
from koruide.ides.cursor import CursorStrategy


@pytest.fixture
def cursor() -> IdeStrategy:
    strategy = get_strategy("cursor")
    assert strategy is not None, "CursorStrategy must self-register on import"
    return strategy


def test_cursor_is_registered() -> None:
    assert "cursor" in strategy_ids()
    assert isinstance(get_strategy("cursor"), CursorStrategy)


def test_cursor_identity(cursor: IdeStrategy) -> None:
    assert cursor.id == "cursor"
    assert cursor.label == "Cursor"


def test_cursor_detection_signature(cursor: IdeStrategy) -> None:
    detection = cursor.detection
    assert "cursor" in detection.comm_patterns
    assert detection.label == "Cursor"


def test_cursor_terminal_signature(cursor: IdeStrategy) -> None:
    terminal = cursor.terminal
    assert "CURSOR_AGENT" in terminal.env_keys
    assert "CURSOR_CLI" in terminal.env_keys
    assert "cursor" in terminal.env_value_substrings
    assert "cursor" in terminal.parent_comm_substrings


def test_cursor_aliases(cursor: IdeStrategy) -> None:
    aliases = cursor.aliases
    assert aliases.canonical == "cursor"
    assert "cursor" in aliases.aliases


def test_cursor_config_home_uses_xdg(
    cursor: IdeStrategy,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    # No classic userdata override — fall back to XDG Cursor folder.
    monkeypatch.setattr(
        "koruide.ides.cursor.resolve_cursor_user_data_dirs",
        lambda **_kwargs: [],
    )
    home = cursor.config_home()
    assert home == tmp_path / "Cursor"


def test_cursor_config_home_prefers_classic_user_data_env(
    cursor: IdeStrategy,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    classic = tmp_path / "classic-userdata"
    classic.mkdir()
    agents = tmp_path / "config"
    agents.mkdir()
    monkeypatch.setenv("XDG_CONFIG_HOME", str(agents))
    monkeypatch.setenv("CURSOR_CLASSIC_USER_DATA_DIR", str(classic))
    assert cursor.config_home() == classic


def test_cursor_config_home_reads_koru_settings(
    cursor: IdeStrategy,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    classic = tmp_path / "from-settings"
    classic.mkdir()
    project = tmp_path / "proj"
    (project / ".koru").mkdir(parents=True)
    (project / ".koru" / "config.json").write_text(
        json.dumps({"ides": {"cursor": {"user_data_dir": str(classic)}}}) + "\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    monkeypatch.delenv("CURSOR_CLASSIC_USER_DATA_DIR", raising=False)
    monkeypatch.delenv("KORU_CURSOR_USER_DATA_DIR", raising=False)
    monkeypatch.setenv("KORU_PROJECT", str(project))
    monkeypatch.chdir(project)
    assert cursor.config_home() == classic


def test_cursor_user_settings_path(
    cursor: IdeStrategy,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    monkeypatch.setattr(
        "koruide.ides.cursor.resolve_cursor_user_data_dirs",
        lambda **_kwargs: [],
    )
    assert cursor.user_settings_path() == tmp_path / "Cursor" / "User" / "settings.json"


def test_cursor_workspace_settings_path(cursor: IdeStrategy, tmp_path: Path) -> None:
    # workspace_settings_path returns the candidate path; existence is the
    # caller's concern. We assert the LAYOUT contract here.
    candidate = cursor.workspace_settings_path(tmp_path)
    assert candidate == tmp_path / ".cursor" / "settings.json"


def test_cursor_extensions_metadata_path(cursor: IdeStrategy) -> None:
    expected = Path.home() / ".cursor" / "extensions" / "extensions.json"
    assert cursor.extensions_metadata_path() == expected


def test_cursor_state_vscdb_path(
    cursor: IdeStrategy,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    monkeypatch.setattr(
        "koruide.ides.cursor.resolve_cursor_user_data_dirs",
        lambda **_kwargs: [],
    )
    expected = tmp_path / "Cursor" / "User" / "globalStorage" / "state.vscdb"
    assert cursor.state_vscdb_path() == expected


def test_cursor_plugin_policy(cursor: IdeStrategy) -> None:
    plugin = cursor.plugin
    assert plugin.supports_vscode_extension is True
    # Cursor enforces extensions.trustedPublishers (this was the root cause
    # of the "plugin installed but never activates" issue).
    assert plugin.requires_trusted_publisher is True
    # Cursor uses its own paste/submit protocol (composer.sendToAgent); the
    # strict vscode/vscodium ack contract must NOT be applied here.
    assert plugin.strict_plugin_ack_required is False
    assert plugin.install_blocked_reason is None


def test_cursor_keyboard_policy(cursor: IdeStrategy) -> None:
    keyboard = cursor.keyboard
    assert keyboard.submit_key == "Return"
    assert keyboard.os_injector_tool_id == "cursor"
    assert keyboard.keyboard_fallback_default is False


def test_cursor_editor_cli_candidates(cursor: IdeStrategy) -> None:
    assert cursor.editor_cli_candidates() == ("cursor",)


def test_cursor_window_name_hints(cursor: IdeStrategy) -> None:
    assert cursor.window_name_hints() == ("Cursor",)


def test_shared_layer_uses_cursor_strategy(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``koru.ide_adapters.shared`` must delegate Cursor paths to the strategy."""
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    monkeypatch.setattr(
        "koruide.ides.cursor.resolve_cursor_user_data_dirs",
        lambda **_kwargs: [],
    )
    from koru.ide_adapters import shared

    assert shared.config_home_for_ide("cursor") == tmp_path / "Cursor"
    assert shared.user_settings_path("cursor") == (
        tmp_path / "Cursor" / "User" / "settings.json"
    )
    # workspace_settings_path returns None when the file does not exist.
    assert shared.workspace_settings_path(tmp_path, "cursor") is None
    settings = tmp_path / ".cursor" / "settings.json"
    settings.parent.mkdir(parents=True, exist_ok=True)
    settings.write_text("{}\n", encoding="utf-8")
    assert shared.workspace_settings_path(tmp_path, "cursor") == settings
    assert shared.extension_metadata_path("cursor") == (
        Path.home() / ".cursor" / "extensions" / "extensions.json"
    )


def test_ide_reload_layer_uses_cursor_strategy() -> None:
    """``koru.ide_adapters.ide_reload`` must source Cursor hints from the strategy."""
    from koru.ide_adapters import ide_reload

    assert ide_reload._window_name_hints("cursor") == ("Cursor",)
    assert ide_reload._editor_cli_candidates("cursor") == ("cursor",)


def test_registry_adapter_for_cursor_built_from_strategy() -> None:
    """Diagnostic ``VSCodeFamilyAdapter`` for Cursor mirrors the strategy."""
    from koru.ide_adapters.registry import get_adapter

    adapter = get_adapter("cursor")
    assert adapter is not None
    assert adapter.ide_id == "cursor"
    assert adapter.label == "Cursor"
    assert adapter.requires_trusted_publisher is True
