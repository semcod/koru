"""Unit tests for koruide.daemon.handlers_plugin_event module (R6)."""
from __future__ import annotations

from unittest import mock

import pytest

from koruide.daemon.handlers_plugin_event import (
    _PluginEventHandoff,
    _append_event,
    _check_handoff_cooldown,
    _event_path,
    _execute_handoff,
    _forward_handoff_to_plugin,
    _handle_plugin_event_basic,
    _plugin_event_should_handoff,
    _ack_plugin_event_without_handoff,
    handle_plugin_event,
)
from koruide.protocol import Message


def test_event_path() -> None:
    """Test _event_path returns correct path."""
    path = _event_path()
    assert path.name == "koru-autopilot-events.ndjson"


def test_plugin_event_should_handoff_true() -> None:
    """Test _plugin_event_should_handoff returns True for session.ended with handoff."""
    daemon = mock.Mock()
    daemon.handoff = mock.Mock()
    
    msg = Message(type="session.ended", id="e-1", data={})
    assert _plugin_event_should_handoff(daemon, msg) is True


def test_plugin_event_should_handoff_false_no_handoff() -> None:
    """Test _plugin_event_should_handoff returns False when handoff is None."""
    daemon = mock.Mock()
    daemon.handoff = None
    
    msg = Message(type="session.ended", id="e-1", data={})
    assert _plugin_event_should_handoff(daemon, msg) is False


def test_plugin_event_should_handoff_false_wrong_type() -> None:
    """Test _plugin_event_should_handoff returns False for non-session.ended."""
    daemon = mock.Mock()
    daemon.handoff = mock.Mock()
    
    msg = Message(type="message.sent", id="e-1", data={})
    assert _plugin_event_should_handoff(daemon, msg) is False


def test_ack_plugin_event_without_handoff_sends_ack() -> None:
    """Test _ack_plugin_event_without_handoff sends ack."""
    daemon = mock.Mock()
    client = mock.Mock()
    client.ide = "vscode"
    
    msg = Message(type="session.started", id="e-1", data={})
    ack_info = {"event": "session.started"}
    
    _ack_plugin_event_without_handoff(daemon, client, msg, ack_info)
    
    daemon._send.assert_called_once()
    call_args = daemon._send.call_args[0]
    assert call_args[0] == client
    assert b'"type":"ack"' in call_args[1]


def test_handle_plugin_event_basic_no_handoff() -> None:
    """Test _handle_plugin_event_basic returns None when no handoff needed."""
    daemon = mock.Mock()
    daemon.handoff = None
    client = mock.Mock()
    client.ide = "vscode"
    client.awaiting_plugin = None
    
    msg = Message(type="message.sent", id="e-1", data={"chat": "default"})
    
    result = _handle_plugin_event_basic(daemon, client, msg)
    
    assert result is None
    daemon.log.assert_called_once()
    daemon.audit.record.assert_called_once()


def test_handle_plugin_event_basic_with_handoff() -> None:
    """Test _handle_plugin_event_basic returns handoff info when handoff needed."""
    daemon = mock.Mock()
    daemon.handoff = mock.Mock()
    client = mock.Mock()
    client.ide = "vscode"
    
    msg = Message(type="session.ended", id="e-1", data={"chat": "default", "reason": "done"})
    
    result = _handle_plugin_event_basic(daemon, client, msg)
    
    assert result is not None
    assert isinstance(result, _PluginEventHandoff)
    assert result.chat == "default"
    assert result.reason == "done"


def test_check_handoff_cooldown_passed() -> None:
    """Test _check_handoff_cooldown returns True when cooldown passed."""
    daemon = mock.Mock()
    daemon._last_chat_send_at = 0
    daemon.handoff_cooldown = 5
    
    ack_info = {}
    result = _check_handoff_cooldown(daemon, ack_info)
    
    assert result is True
    assert "handoff" not in ack_info


def test_check_handoff_cooldown_blocked() -> None:
    """Test _check_handoff_cooldown returns False during cooldown."""
    import time
    daemon = mock.Mock()
    daemon._last_chat_send_at = time.monotonic()
    daemon.handoff_cooldown = 60
    
    ack_info = {}
    result = _check_handoff_cooldown(daemon, ack_info)
    
    assert result is False
    assert ack_info["handoff"] == "skipped"
    assert "cooldown" in ack_info["reason"]


def test_execute_handoff_success() -> None:
    """Test _execute_handoff returns text on success."""
    daemon = mock.Mock()
    daemon.handoff = mock.Mock(return_value="handoff text")
    client = mock.Mock()
    client.ide = "vscode"
    
    msg = Message(type="session.ended", id="e-1", data={})
    ack_info = {}
    
    result = _execute_handoff(daemon, client, msg, "default", "done", ack_info)
    
    assert result == "handoff text"
    daemon.handoff.assert_called_once_with({"chat": "default", "reason": "done", "ide": "vscode"})


def test_execute_handoff_empty_text() -> None:
    """Test _execute_handoff returns None when handoff returns empty."""
    daemon = mock.Mock()
    daemon.handoff = mock.Mock(return_value="")
    client = mock.Mock()
    client.ide = "vscode"
    
    msg = Message(type="session.ended", id="e-1", data={})
    ack_info = {}
    
    result = _execute_handoff(daemon, client, msg, "default", "done", ack_info)
    
    assert result is None
    assert ack_info["handoff"] == "skipped"
    daemon._send.assert_called_once()


def test_execute_handoff_exception() -> None:
    """Test _execute_handoff handles exception."""
    daemon = mock.Mock()
    daemon.handoff = mock.Mock(side_effect=Exception("handoff error"))
    client = mock.Mock()
    client.ide = "vscode"
    
    msg = Message(type="session.ended", id="e-1", data={})
    ack_info = {}
    
    result = _execute_handoff(daemon, client, msg, "default", "done", ack_info)
    
    assert result is None
    assert ack_info["handoff"] == "error"
    daemon._send.assert_called_once()


def test_forward_handoff_to_plugin() -> None:
    """Test _forward_handoff_to_plugin sends text to plugin."""
    daemon = mock.Mock()
    daemon._last_chat_send_at = 0
    client = mock.Mock()
    client.ide = "vscode"
    
    msg = Message(type="session.ended", id="e-1", data={})
    ack_info = {}
    
    _forward_handoff_to_plugin(daemon, client, msg, "test text", "default", "done", ack_info)
    
    assert daemon._send.call_count == 2  # forwarded + ack
    assert ack_info["handoff"] == "sent"
    assert ack_info["chars"] == 9
    daemon.audit.record.assert_called_once_with("handoff", ide="vscode", chat="default", reason="done", chars=9, ok=True)


def test_handle_plugin_event_session_started() -> None:
    """Test handle_plugin_event calls start_new_log_session for session.started."""
    with mock.patch("koruide.daemon.handlers_plugin_event.start_new_log_session") as mock_start:
        daemon = mock.Mock()
        daemon.handoff = None
        client = mock.Mock()
        client.ide = "vscode"
        
        msg = Message(type="session.started", id="e-1", data={"session_id": "s-123", "session_name": "test"})
        
        handle_plugin_event(daemon, client, msg)
        
        mock_start.assert_called_once_with(session_id="s-123", name="test")


def test_handle_plugin_event_no_handoff() -> None:
    """Test handle_plugin_event handles non-handoff event."""
    daemon = mock.Mock()
    daemon.handoff = None
    client = mock.Mock()
    client.ide = "vscode"
    client.awaiting_plugin = None
    
    msg = Message(type="message.sent", id="e-1", data={"chat": "default"})
    
    handle_plugin_event(daemon, client, msg)
    
    daemon._send.assert_called_once()  # ack sent


def test_handle_plugin_event_with_handoff(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test handle_plugin_event orchestrates full handoff."""
    monkeypatch.setattr(
        "koruide.daemon.handlers_plugin_event._check_handoff_cooldown",
        mock.Mock(return_value=True),
    )
    monkeypatch.setattr(
        "koruide.daemon.handlers_plugin_event._execute_handoff",
        mock.Mock(return_value="handoff text"),
    )
    mock_forward = mock.Mock()
    monkeypatch.setattr(
        "koruide.daemon.handlers_plugin_event._forward_handoff_to_plugin",
        mock_forward,
    )
    
    daemon = mock.Mock()
    daemon.handoff = mock.Mock()
    daemon._last_chat_send_at = 0
    daemon.handoff_cooldown = 5
    client = mock.Mock()
    client.ide = "vscode"
    
    msg = Message(type="session.ended", id="e-1", data={"chat": "default", "reason": "done"})
    
    handle_plugin_event(daemon, client, msg)
    
    mock_forward.assert_called_once()


# ---------------------------------------------------------------------------
# Backward compatibility tests
# ---------------------------------------------------------------------------

def test_backward_compat_reexports_from_handlers() -> None:
    """Test that plugin_event functions are re-exported from handlers module."""
    from koruide.daemon import handlers
    
    assert handlers.handle_plugin_event is handle_plugin_event
    assert handlers._event_path is _event_path
    assert handlers._append_event is _append_event
    assert handlers._handle_plugin_event_basic is _handle_plugin_event_basic
