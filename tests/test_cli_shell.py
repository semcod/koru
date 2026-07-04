"""koru shell — config persistence, dispatch, and checkbox fallback."""

from __future__ import annotations

import io
import json
from pathlib import Path

import pytest

from koru.cli_shell import (
    INTEGRATION_CATALOG,
    INTEGRATIONS_SECTION,
    SHELL_SECTION,
    ShellContext,
    _dispatch,
    enabled_integrations,
    load_config,
    save_config,
    shell_settings,
)


@pytest.fixture()
def project(tmp_path: Path) -> Path:
    return tmp_path


def test_shell_settings_defaults(project: Path) -> None:
    settings = shell_settings(load_config(project))
    assert settings["llm_model"] == "qwen/qwen3-coder-next"
    assert settings["drain_batch"] == 10


def test_enabled_integrations_defaults(project: Path) -> None:
    enabled = enabled_integrations(load_config(project))
    assert "openrouter" in enabled
    assert "planfile_queue" in enabled
    assert "qoder_chat" not in enabled


def test_save_and_reload_config(project: Path) -> None:
    config = load_config(project)
    config[SHELL_SECTION] = {"llm_model": "qwen/qwen3-coder-plus", "drain_batch": 3}
    config[INTEGRATIONS_SECTION] = {"enabled": ["openrouter", "qoder_chat"]}
    save_config(project, config)

    reloaded = load_config(project)
    assert shell_settings(reloaded)["llm_model"] == "qwen/qwen3-coder-plus"
    assert shell_settings(reloaded)["drain_batch"] == 3
    assert enabled_integrations(reloaded) == {"openrouter", "qoder_chat"}
    # file is the shared `koru configure` store
    assert json.loads((project / ".koru" / "config.json").read_text())[SHELL_SECTION]


def test_dispatch_exact_command_beats_alias_prefix(project: Path, monkeypatch, capsys) -> None:
    """/integration must resolve despite the /integrations alias."""
    ctx = ShellContext(project=project, config=load_config(project))
    monkeypatch.setattr("sys.stdin", io.StringIO("q\n"))
    monkeypatch.setattr("sys.stdin.isatty", lambda: False, raising=False)
    assert _dispatch(ctx, "/integration") is True
    out = capsys.readouterr().out
    assert "ambiguous" not in out
    assert "cancelled" in out


def test_dispatch_integration_numeric_toggle_persists(project: Path, monkeypatch, capsys) -> None:
    ctx = ShellContext(project=project, config=load_config(project))
    monkeypatch.setattr("sys.stdin", io.StringIO("2\n"))
    monkeypatch.setattr("sys.stdin.isatty", lambda: False, raising=False)
    assert _dispatch(ctx, "/integration") is True
    assert "qoder_chat" in enabled_integrations(load_config(project))
    assert "saved" in capsys.readouterr().out


def test_dispatch_exit_and_unknown(project: Path, capsys) -> None:
    ctx = ShellContext(project=project, config=load_config(project))
    assert _dispatch(ctx, "/exit") is False
    assert _dispatch(ctx, "/nosuchcommand") is True
    assert "unknown command" in capsys.readouterr().out


def test_catalog_keys_unique() -> None:
    keys = [item.key for item in INTEGRATION_CATALOG]
    assert len(keys) == len(set(keys))
