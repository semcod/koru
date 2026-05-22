"""Tests for :mod:`koru.ide_router`."""

from __future__ import annotations

import json
import sys

import pytest

from koru.ide_router import is_headless_environment, resolve_ide_route


def test_is_headless_false_minimal_env() -> None:
    assert is_headless_environment({}) is False


def test_is_headless_koru_headless_yes() -> None:
    assert is_headless_environment({"KORU_HEADLESS": "yes"}) is True


def test_is_headless_koru_headless_on() -> None:
    assert is_headless_environment({"KORU_HEADLESS": "on"}) is True


def test_is_headless_koru_headless_false_explicit() -> None:
    assert is_headless_environment({"KORU_HEADLESS": "0"}) is False
    assert is_headless_environment({"KORU_HEADLESS": "false"}) is False


def test_is_headless_ide_mode_whitespace_case_insensitive() -> None:
    env = {"KORU_IDE_MODE": "  HEADLESS  "}
    assert is_headless_environment(env) is True


@pytest.mark.skipif(sys.platform == "win32", reason="SSH+DISPLAY heuristic is POSIX-specific")
def test_is_headless_ssh_empty_display_still_headless() -> None:
    env = {"SSH_CONNECTION": "127.0.0.1 1 127.0.0.1 22", "DISPLAY": ""}
    assert is_headless_environment(env) is True


def test_resolve_ide_route_env_ide_case_insensitive() -> None:
    env = {"KORU_AUTOPILOT_IDE": "  CuRsOr  "}
    r = resolve_ide_route(cli_autopilot_ide="vscode", environ=env)
    assert r.autopilot_ide == "cursor"


def test_resolve_ide_route_normalizes_vscode_family_alias() -> None:
    env = {"KORU_AUTOPILOT_IDE": "codium"}
    r = resolve_ide_route(cli_autopilot_ide="vscode", environ=env)
    assert r.autopilot_ide == "vscodium"


def test_resolve_ide_route_normalizes_zed_alias() -> None:
    r = resolve_ide_route(cli_autopilot_ide="zed-editor", environ={})
    assert r.autopilot_ide == "zed"


def test_resolve_ide_route_headless_sets_primary_surface() -> None:
    r = resolve_ide_route(cli_autopilot_ide="cursor", environ={"KORU_HEADLESS": "1"})
    assert r.primary_surface == "headless_terminal"
    assert r.recommend_autopilot_drive is False


def test_resolve_ide_route_ide_shell_surface() -> None:
    r = resolve_ide_route(cli_autopilot_ide="windsurf", environ={})
    assert r.primary_surface == "ide_shell"


def test_ide_router_main_help_exits_zero() -> None:
    from koru.cli import ide_router_main

    with pytest.raises(SystemExit) as exc:
        ide_router_main(["--help"])
    assert exc.value.code == 0


def test_ide_router_main_unknown_flag_exits_nonzero() -> None:
    from koru.cli import ide_router_main

    with pytest.raises(SystemExit) as exc:
        ide_router_main(["--not-a-flag"])
    assert exc.value.code == 2


def test_ide_router_main_bad_format_exits_nonzero(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from koru.cli import ide_router_main

    monkeypatch.delenv("KORU_AUTOPILOT_IDE", raising=False)
    with pytest.raises(SystemExit) as exc:
        ide_router_main(["--format", "yaml"])
    assert exc.value.code == 2


@pytest.mark.skipif(sys.platform == "win32", reason="SSH+DISPLAY heuristic is POSIX-specific")
def test_is_headless_ssh_without_display() -> None:
    env = {"SSH_CONNECTION": "127.0.0.1 12345 127.0.0.1 22"}
    assert is_headless_environment(env) is True


@pytest.mark.skipif(sys.platform == "win32", reason="DISPLAY pairing is POSIX-specific here")
def test_is_headless_ssh_with_display_not_headless() -> None:
    env = {"SSH_CONNECTION": "127.0.0.1 12345 127.0.0.1 22", "DISPLAY": ":0"}
    assert is_headless_environment(env) is False


def test_is_headless_windows_ignores_ssh_without_display(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "platform", "win32")
    env = {"SSH_CONNECTION": "127.0.0.1 12345 127.0.0.1 22"}
    assert is_headless_environment(env) is False


def test_resolve_ide_route_bad_env_uses_cli() -> None:
    env = {"KORU_AUTOPILOT_IDE": "not-a-real-ide"}
    r = resolve_ide_route(cli_autopilot_ide="jetbrains", environ=env)
    assert r.autopilot_ide == "jetbrains"
    assert r.headless is False


def test_resolve_ide_route_whitespace_env_treated_as_missing() -> None:
    env = {"KORU_AUTOPILOT_IDE": "   "}
    r = resolve_ide_route(cli_autopilot_ide="zed", environ=env)
    assert r.autopilot_ide == "zed"


def test_resolve_ide_route_cli_invalid_env_empty_uses_auto() -> None:
    r = resolve_ide_route(cli_autopilot_ide="not-an-ide", environ={})
    assert r.autopilot_ide == "auto"


def test_resolve_ide_route_cli_auto_env_empty() -> None:
    r = resolve_ide_route(cli_autopilot_ide="auto", environ={})
    assert r.autopilot_ide == "auto"


def test_resolve_ide_route_headless_notes_mention_escape_hatch() -> None:
    r = resolve_ide_route(cli_autopilot_ide="cursor", environ={"KORU_HEADLESS": "1"})
    assert "KORU_HEADLESS_ALLOW_AUTOPILOT" in r.notes


def test_resolve_ide_route_ide_shell_notes_mention_mcp() -> None:
    r = resolve_ide_route(cli_autopilot_ide="vscode", environ={})
    assert "MCP" in r.notes


def test_ide_router_main_json(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.delenv("KORU_AUTOPILOT_IDE", raising=False)
    monkeypatch.delenv("KORU_HEADLESS", raising=False)
    monkeypatch.delenv("KORU_IDE_MODE", raising=False)

    from koru.cli import ide_router_main

    assert ide_router_main(["--format", "json", "--cli-ide", "jetbrains"]) == 0
    payload = json.loads(capsys.readouterr().out.strip())
    assert payload["autopilot_ide"] == "jetbrains"
    assert payload["headless"] is False


def test_ide_router_main_text(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.delenv("KORU_AUTOPILOT_IDE", raising=False)
    monkeypatch.delenv("KORU_HEADLESS", raising=False)

    from koru.cli import ide_router_main

    assert ide_router_main(["--cli-ide", "zed"]) == 0
    out = capsys.readouterr().out
    assert "autopilot_ide: zed" in out
    assert "primary_surface: ide_shell" in out


def test_resolve_ide_route_env_overrides_cli() -> None:
    env = {"KORU_AUTOPILOT_IDE": "cursor"}
    r = resolve_ide_route(cli_autopilot_ide="vscode", environ=env)
    assert r.autopilot_ide == "cursor"
    assert r.headless is False
    assert r.recommend_mcp is True


def test_resolve_ide_route_auto_env_does_not_override_cli() -> None:
    env = {"KORU_AUTOPILOT_IDE": "auto"}
    r = resolve_ide_route(cli_autopilot_ide="cursor", environ=env)
    assert r.autopilot_ide == "cursor"


def test_resolve_ide_route_headless_forces_auto() -> None:
    env = {"KORU_HEADLESS": "1", "KORU_AUTOPILOT_IDE": "cursor"}
    r = resolve_ide_route(cli_autopilot_ide="vscode", environ=env)
    assert r.autopilot_ide == "auto"
    assert r.headless is True
    assert r.recommend_mcp is False


def test_resolve_ide_route_headless_allow_autopilot_honors_env() -> None:
    env = {
        "KORU_HEADLESS": "1",
        "KORU_HEADLESS_ALLOW_AUTOPILOT": "1",
        "KORU_AUTOPILOT_IDE": "cursor",
    }
    r = resolve_ide_route(cli_autopilot_ide="vscode", environ=env)
    assert r.autopilot_ide == "cursor"
    assert r.headless is False


def test_is_headless_via_ide_mode() -> None:
    env = {"KORU_IDE_MODE": "headless"}
    assert is_headless_environment(env) is True


def test_resolve_ide_route_cli_ide_whitespace_normalized() -> None:
    r = resolve_ide_route(cli_autopilot_ide="  CuRsOr  ", environ={})
    assert r.autopilot_ide == "cursor"


def test_resolve_ide_route_headless_allow_autopilot_yes_string() -> None:
    env = {
        "KORU_HEADLESS": "1",
        "KORU_HEADLESS_ALLOW_AUTOPILOT": "yes",
        "KORU_AUTOPILOT_IDE": "windsurf",
    }
    r = resolve_ide_route(cli_autopilot_ide="vscode", environ=env)
    assert r.autopilot_ide == "windsurf"
    assert r.headless is False


def test_resolve_ide_route_environ_none_uses_os_environ(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("KORU_AUTOPILOT_IDE", "zed")
    monkeypatch.delenv("KORU_HEADLESS", raising=False)
    monkeypatch.delenv("KORU_IDE_MODE", raising=False)
    r = resolve_ide_route(cli_autopilot_ide="auto", environ=None)
    assert r.autopilot_ide == "zed"


def test_resolve_ide_route_headless_all_recommend_flags_false() -> None:
    r = resolve_ide_route(cli_autopilot_ide="cursor", environ={"KORU_HEADLESS": "true"})
    assert r.headless is True
    assert r.recommend_mcp is False
    assert r.recommend_autopilot_drive is False


def test_ide_router_main_json_when_headless(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("KORU_HEADLESS", "1")
    monkeypatch.delenv("KORU_AUTOPILOT_IDE", raising=False)

    from koru.cli import ide_router_main

    assert ide_router_main(["--format", "json", "--cli-ide", "cursor"]) == 0
    payload = json.loads(capsys.readouterr().out.strip())
    assert payload["headless"] is True
    assert payload["autopilot_ide"] == "auto"
    assert payload["recommend_mcp"] is False


def test_resolve_ide_route_vscode_explicit_env() -> None:
    r = resolve_ide_route(cli_autopilot_ide="auto", environ={"KORU_AUTOPILOT_IDE": "vscode"})
    assert r.autopilot_ide == "vscode"


def test_resolve_ide_route_env_instance_used_when_cli_auto_and_env_ide_missing() -> None:
    env = {"KORU_AUTOPILOT_INSTANCE": "windsurf"}
    r = resolve_ide_route(cli_autopilot_ide="auto", environ=env)
    assert r.autopilot_ide == "windsurf"


def test_resolve_ide_route_env_instance_ignored_when_cli_explicit() -> None:
    env = {"KORU_AUTOPILOT_INSTANCE": "windsurf"}
    r = resolve_ide_route(cli_autopilot_ide="jetbrains", environ=env)
    assert r.autopilot_ide == "jetbrains"


def test_resolve_ide_route_env_ide_wins_over_env_instance() -> None:
    env = {
        "KORU_AUTOPILOT_IDE": "cursor",
        "KORU_AUTOPILOT_INSTANCE": "windsurf",
    }
    r = resolve_ide_route(cli_autopilot_ide="auto", environ=env)
    assert r.autopilot_ide == "cursor"
