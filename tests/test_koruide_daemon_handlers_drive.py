"""Unit tests for koruide.daemon.handlers_drive module (R6)."""
from __future__ import annotations

from typing import Any
from unittest import mock

import pytest

from koruide.daemon.handlers_drive import (
    _drive_via_keyboard,
    _drive_via_keyboard_backend,
    _drive_via_os_injector_backend,
    _drive_via_plugin,
    _prefer_keyboard_drive,
    _resolve_keyboard_drive_selection,
    _try_os_injector_drive,
    handle_drive,
)


def test_prefer_keyboard_drive_with_env_var(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test _prefer_keyboard_drive returns True when env var is set."""
    monkeypatch.setenv("KORU_AUTOPILOT_PREFER_KEYBOARD", "1")
    assert _prefer_keyboard_drive() is True


def test_prefer_keyboard_drive_without_env_var(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test _prefer_keyboard_drive returns False when no env var is set."""
    monkeypatch.delenv("KORU_AUTOPILOT_PREFER_KEYBOARD", raising=False)
    monkeypatch.delenv("KORU_AUTOPILOT_VISIBLE_TYPING", raising=False)
    assert _prefer_keyboard_drive() is False


def test_prefer_keyboard_drive_with_visible_typing(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test _prefer_keyboard_drive returns True when visible typing is enabled."""
    monkeypatch.setenv("KORU_AUTOPILOT_VISIBLE_TYPING", "true")
    assert _prefer_keyboard_drive() is True


def test_handle_drive_rejects_missing_text() -> None:
    """Test handle_drive sends error when text is missing."""
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
    """Test handle_drive routes via plugin when plugin is available."""
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


def test_handle_drive_blocks_when_plugin_required_but_not_found(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test handle_drive blocks when require_plugin is True but no plugin."""
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
    """Test _resolve_keyboard_drive_selection returns correct values."""
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


def test_try_os_injector_drive_returns_none_when_no_profile(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test _try_os_injector_drive returns None when no OS injector profile."""
    daemon = mock.Mock()
    daemon.project = "/tmp/test"
    daemon.log = mock.Mock()
    
    monkeypatch.setattr(
        "koruide.os_injector.try_drive_with_profile",
        lambda **kwargs: None,
    )
    
    result = _try_os_injector_drive(daemon, "vscode", "hello", True)
    assert result is None


def test_try_os_injector_drive_raises_on_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test _try_os_injector_drive raises InjectorError on failure."""
    daemon = mock.Mock()
    daemon.project = "/tmp/test"
    daemon.log = mock.Mock()
    
    from koruide import os_injector as oi_module
    
    def raise_error(**kwargs):
        raise oi_module.OsInjectorError("test error")
    
    monkeypatch.setattr(
        "koruide.os_injector.try_drive_with_profile",
        raise_error,
    )
    
    with pytest.raises(Exception):  # InjectorError will be raised
        _try_os_injector_drive(daemon, "vscode", "hello", True)


def test_drive_via_os_injector_backend_success() -> None:
    """Test _drive_via_os_injector_backend returns True on success."""
    daemon = mock.Mock()
    daemon._try_os_injector_drive.return_value = {
        "backend": "os_injector",
        "submitted": True,
        "chat_x": 100,
        "chat_y": 200,
        "input_method": "paste",
    }
    daemon.project = "/tmp/test"
    
    client = mock.Mock()
    msg = mock.Mock()
    msg.id = "test-123"
    
    target = mock.Mock()
    target.to_dict.return_value = {"id": "vscode"}
    
    result = _drive_via_os_injector_backend(
        daemon=daemon,
        client=client,
        msg=msg,
        target_id="vscode",
        profile_id="vscode",
        text="hello",
        submit=True,
        preview="hello",
        target=target,
    )
    
    assert result is True
    daemon._send.assert_called_once()
    daemon.audit.record.assert_called_once()


def test_drive_via_os_injector_backend_failure() -> None:
    """Test _drive_via_os_injector_backend returns False on failure."""
    daemon = mock.Mock()
    from koruide.injector import InjectorError
    daemon._try_os_injector_drive.side_effect = InjectorError("test error")
    
    client = mock.Mock()
    msg = mock.Mock()
    
    result = _drive_via_os_injector_backend(
        daemon=daemon,
        client=client,
        msg=msg,
        target_id="vscode",
        profile_id="vscode",
        text="hello",
        submit=True,
        preview="hello",
        target=None,
    )
    
    assert result is False


def test_drive_via_keyboard_backend_success() -> None:
    """Test _drive_via_keyboard_backend sends ack on success."""
    daemon = mock.Mock()
    daemon.injector.select_backend.return_value = "wtype"
    daemon.injector.type_text.return_value = mock.Mock(backend="wtype", submitted=True)
    
    client = mock.Mock()
    msg = mock.Mock()
    msg.id = "test-123"
    
    target = mock.Mock()
    target.to_dict.return_value = {"id": "vscode"}
    
    _drive_via_keyboard_backend(
        daemon=daemon,
        client=client,
        msg=msg,
        target_id="vscode",
        text="hello",
        submit=True,
        preview="hello",
        target=target,
    )
    
    daemon._send.assert_called_once()
    daemon.audit.record.assert_called_once()


def test_drive_via_keyboard_backend_failure() -> None:
    """Test _drive_via_keyboard_backend sends error on failure."""
    daemon = mock.Mock()
    daemon.injector.select_backend.return_value = "wtype"
    from koruide.injector import InjectorError
    daemon.injector.type_text.side_effect = InjectorError("test error")
    
    client = mock.Mock()
    msg = mock.Mock()
    msg.id = "test-123"
    
    _drive_via_keyboard_backend(
        daemon=daemon,
        client=client,
        msg=msg,
        target_id="vscode",
        text="hello",
        submit=True,
        preview="hello",
        target=None,
    )
    
    daemon._send.assert_called_once()
    call_args = daemon._send.call_args[0]
    assert call_args[0] == client
    assert "error" in call_args[1].decode().lower()


# ---------------------------------------------------------------------------
# Backward compatibility tests
# ---------------------------------------------------------------------------

def test_backward_compat_reexports_from_handlers() -> None:
    """Test that drive functions are re-exported from handlers module."""
    from koruide.daemon import handlers
    
    assert handlers.handle_drive is handle_drive
    assert handlers._drive_via_plugin is _drive_via_plugin
    assert handlers._drive_via_keyboard is _drive_via_keyboard
    assert handlers._prefer_keyboard_drive is _prefer_keyboard_drive
