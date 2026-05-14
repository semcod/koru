"""Tests for :mod:`koru.ide_router`."""

from __future__ import annotations

from koru.ide_router import is_headless_environment, resolve_ide_route


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
