"""Integration tests for koruide daemon drive routing (wire protocol, plugins)."""

from __future__ import annotations

from unittest import mock

import pytest

from koruide.daemon.handlers_drive import (
    _active_pending_plugin_drive,
    _deliver_chat_via_plugin_socket,
    _drive_via_plugin,
    _pending_corr_owner_alive,
    _prefer_keyboard_drive,
    _resolve_keyboard_drive_selection,
    handle_drive,
)


def test_prefer_keyboard_drive_with_env_var(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("KORU_AUTOPILOT_PREFER_KEYBOARD", "1")
    assert _prefer_keyboard_drive() is True


def test_prefer_keyboard_drive_without_env_var(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("KORU_AUTOPILOT_PREFER_KEYBOARD", raising=False)
    monkeypatch.delenv("KORU_AUTOPILOT_VISIBLE_TYPING", raising=False)
    assert _prefer_keyboard_drive() is False


def test_prefer_keyboard_drive_with_visible_typing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("KORU_AUTOPILOT_VISIBLE_TYPING", "true")
    assert _prefer_keyboard_drive() is True


def test_handle_drive_rejects_missing_text() -> None:
    daemon = mock.Mock()
    client = mock.Mock()
    client.role = "unknown"

    msg = mock.Mock()
    msg.id = "test-123"
    msg.data = {"text": ""}

    handle_drive(daemon, client, msg)

    assert client.role == "cli"
    daemon._send.assert_called_once()
    call_args = daemon._send.call_args[0]
    assert call_args[0] == client
    assert "missing" in call_args[1].decode().lower()


def test_handle_drive_routes_via_plugin_when_available(monkeypatch: pytest.MonkeyPatch) -> None:
    daemon = mock.Mock()
    daemon._plugin_for.return_value = mock.Mock(
        ide="vscode",
        version="1.0.0",
        protocol_version=1,
        capabilities=[],
        sock=mock.Mock(fileno=lambda: 10),
    )
    daemon.project = "/tmp/test"

    client = mock.Mock()
    client.role = "unknown"
    client.sock.fileno.return_value = 11

    msg = mock.Mock()
    msg.id = "test-123"
    msg.data = {"text": "hello", "ide": "vscode", "submit": True, "require_plugin": False}

    monkeypatch.setattr(
        "koruide.daemon.handlers_drive._prefer_keyboard_drive",
        lambda: False,
    )

    with mock.patch("koruide.daemon.handlers_drive._drive_via_plugin") as mock_drive:
        handle_drive(daemon, client, msg)
        mock_drive.assert_called_once()


def test_handle_drive_blocks_when_plugin_required_but_not_found(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    daemon = mock.Mock()
    daemon._plugin_for.return_value = None
    daemon.project = "/tmp/test"

    client = mock.Mock()
    client.role = "cli"

    msg = mock.Mock()
    msg.id = "test-123"
    msg.data = {"text": "hello", "ide": "vscode", "submit": True, "require_plugin": True}

    with mock.patch("koruide.daemon.handlers_drive.DriveOrchestrator") as mock_orchestrator:
        mock_orchestrator.plugin_required_message.return_value = "Plugin required"
        handle_drive(daemon, client, msg)
        daemon._send.assert_called_once()
        daemon.audit.record.assert_called_once()


def test_resolve_keyboard_drive_selection(monkeypatch: pytest.MonkeyPatch) -> None:
    daemon = mock.Mock()
    daemon.project = "/tmp/test"
    daemon.log = mock.Mock()

    monkeypatch.setattr(
        "koruide.daemon.handlers_drive.resolve_drive_target",
        lambda ide, _, project=None, _log=None: ("vscode", "vscode", "explicit"),
    )
    monkeypatch.setattr(
        "koruide.daemon.handlers_drive.detect_running_ides",
        lambda: [],
    )
    monkeypatch.setattr(
        "koruide.daemon.handlers_drive.pick_target",
        lambda ides, prefer=None: None,
    )

    target_id, profile_id, target, preview = _resolve_keyboard_drive_selection(
        daemon=daemon,
        ide_arg="vscode",
        ide_pref="vscode",
        text="hello world",
    )

    assert target_id == "vscode"
    assert profile_id == "vscode"
    assert preview == "hello world"


def test_deliver_chat_via_plugin_socket_audits_request_not_success(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    daemon = mock.Mock()
    daemon.project = "/tmp/test"
    daemon._command_catalog_store = mock.Mock()
    daemon._command_telemetry = mock.Mock()
    daemon._recent_dsl = []
    daemon._send.return_value = True

    plugin = mock.Mock()
    plugin.ide = "cursor"
    plugin.version = "0.2.1"
    plugin.command_catalog = None

    monkeypatch.setattr("koruide.daemon.handlers_drive.command_picker_enabled", lambda: False)
    monkeypatch.setattr("koruide.daemon.handlers_drive.emit_phase", mock.Mock())
    monkeypatch.setattr("koruide.daemon.handlers_drive.record_integration_action", mock.Mock())

    _deliver_chat_via_plugin_socket(
        daemon,
        plugin,
        "hello",
        True,
        "corr-1",
        strategy_hint=None,
    )

    daemon.audit.record.assert_called_once_with(
        "drive_requested",
        ide="cursor",
        backend="plugin",
        chars=5,
        submit=True,
        status="awaiting_ack",
        corr="corr-1",
    )


def test_backward_compat_reexports_from_handlers() -> None:
    from koruide.daemon import handlers
    from koruide.daemon.handlers_drive import (
        _drive_via_keyboard,
        _drive_via_plugin,
        handle_drive as hd,
    )

    assert handlers.handle_drive is hd
    assert handlers._drive_via_plugin is _drive_via_plugin
    assert handlers._drive_via_keyboard is _drive_via_keyboard
    assert handlers._prefer_keyboard_drive is _prefer_keyboard_drive


def test_pending_corr_owner_alive_for_current_pid() -> None:
    import os

    corr = f"cli-drive-{os.getpid()}-deadbeef"
    assert _pending_corr_owner_alive(corr) is True


def test_pending_corr_owner_alive_for_missing_pid() -> None:
    corr = "cli-drive-999999999-deadbeef"
    assert _pending_corr_owner_alive(corr) is False


def test_active_pending_cleared_when_corr_owner_exited() -> None:
    plugin = mock.Mock()
    plugin.awaiting_plugin = (
        mock.Mock(),
        "cli-drive-999999999-deadbeef",
        True,
        "cursor",
        "text",
        False,
    )
    daemon = mock.Mock()

    pending = _active_pending_plugin_drive(daemon, plugin)

    assert pending is None
    assert plugin.awaiting_plugin is None
    daemon.log.assert_called_once()
