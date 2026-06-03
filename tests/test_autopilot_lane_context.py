"""Tests for autopilot lane autodetection."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from koru.autopilot import lane_context as lc


def test_instance_from_socket_path_cursor_main() -> None:
    assert lc.instance_from_socket_path("/run/user/1000/koru-autopilot-cursor-main.sock") == "cursor-main"


def test_resolve_instance_from_ide_user_settings(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    settings = tmp_path / "settings.json"
    settings.write_text(
        json.dumps(
            {"koruAutopilot.socketPath": "/run/user/1000/koru-autopilot-cursor-main.sock"},
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(lc, "user_settings_path", lambda _ide: settings)
    monkeypatch.delenv("KORU_AUTOPILOT_INSTANCE", raising=False)
    monkeypatch.delenv("KORU_AUTOPILOT_SOCKET", raising=False)

    instance, source = lc.resolve_autopilot_instance(requested_ide="cursor", project=tmp_path)

    assert instance == "cursor-main"
    assert source == "ide-settings:cursor"


def test_resolve_client_socket_path_uses_cursor_main_not_cursor(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    settings = tmp_path / "settings.json"
    settings.write_text(
        json.dumps(
            {"koruAutopilot.socketPath": "/run/user/1000/koru-autopilot-cursor-main.sock"},
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(lc, "user_settings_path", lambda _ide: settings)
    monkeypatch.delenv("KORU_AUTOPILOT_INSTANCE", raising=False)
    monkeypatch.delenv("KORU_AUTOPILOT_SOCKET", raising=False)

    from types import SimpleNamespace

    args = SimpleNamespace(socket=None, ide="cursor", project=tmp_path)
    path = lc.resolve_client_socket_path(args, project=tmp_path)

    assert path.name == "koru-autopilot-cursor-main.sock"


def test_autopilot_env_command_prints_exports(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    settings = tmp_path / "settings.json"
    settings.write_text(
        json.dumps(
            {"koruAutopilot.socketPath": "/run/user/1000/koru-autopilot-cursor-main.sock"},
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(lc, "user_settings_path", lambda _ide: settings)
    monkeypatch.delenv("KORU_AUTOPILOT_INSTANCE", raising=False)
    monkeypatch.delenv("KORU_AUTOPILOT_SOCKET", raising=False)

    from koru.autopilot.cli_command import autopilot_main

    rc = autopilot_main(["env", "--ide", "cursor", "--project", str(tmp_path)])
    out = capsys.readouterr().out

    assert rc == 0
    assert "export KORU_AUTOPILOT_INSTANCE='cursor-main'" in out
    assert "export KORU_AUTOPILOT_IDE='cursor'" in out
    assert "koru-autopilot-cursor-main.sock" in out
