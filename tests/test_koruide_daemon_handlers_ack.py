"""Unit tests for koruide.daemon.handlers_ack module (R6)."""
from __future__ import annotations

from unittest import mock

import pytest

from koruide.daemon.handlers_ack import (
    _annotated_plugin_ack_info,
    _plugin_ack_needs_os_fallback,
    _record_plugin_ack_integration,
    _relay_message_sent_ack,
    _relay_os_fallback_ack,
    _relay_plugin_ack_os_fallback,
    _send_plugin_ack_reply,
    _strict_plugin_ack_ok,
    handle_ack,
)
from koruide.protocol import Message


def test_plugin_ack_needs_os_fallback_check(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test _plugin_ack_needs_os_fallback delegates to DriveOrchestrator."""
    mock_should_try = mock.Mock(return_value=True)
    monkeypatch.setattr(
        "koruide.daemon.handlers_ack.DriveOrchestrator.should_try_os_fallback",
        mock_should_try,
    )
    
    result = _plugin_ack_needs_os_fallback(
        plugin_ok=False,
        info={"delivered": True},
        submit_requested=True,
        plugin_ide="vscode",
        require_plugin=False,
    )
    
    assert result is True
    mock_should_try.assert_called_once_with(
        plugin_ok=False,
        info={"delivered": True},
        submit_requested=True,
        plugin_ide="vscode",
        require_plugin=False,
    )


def test_strict_plugin_ack_ok_when_not_strict(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test _strict_plugin_ack_ok returns original ok when strict check not triggered."""
    mock_should_fail = mock.Mock(return_value=False)
    monkeypatch.setattr(
        "koruide.daemon.handlers_ack.DriveOrchestrator.should_fail_strict_plugin_ack",
        mock_should_fail,
    )
    
    info = {"delivered": True}
    result = _strict_plugin_ack_ok(
        info,
        plugin_ok=True,
        submit_requested=True,
        plugin_ide="vscode",
    )
    
    assert result is True
    assert "message" not in info


def test_strict_plugin_ack_ok_when_strict_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test _strict_plugin_ack_ok sets failure message when strict check fails."""
    mock_should_fail = mock.Mock(return_value=True)
    monkeypatch.setattr(
        "koruide.daemon.handlers_ack.DriveOrchestrator.should_fail_strict_plugin_ack",
        mock_should_fail,
    )
    
    info = {"delivered": True}
    result = _strict_plugin_ack_ok(
        info,
        plugin_ok=True,
        submit_requested=True,
        plugin_ide="vscode",
    )
    
    assert result is False
    assert "message" in info
    assert "strict plugin verification failed" in info["message"]


def test_annotated_plugin_ack_info_builds_metadata(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test _annotated_plugin_ack_info builds info with version metadata."""
    mock_annotate = mock.Mock(return_value={"delivered": True, "annotated": True})
    monkeypatch.setattr(
        "koruide.daemon.handlers_ack.DriveOrchestrator.annotate_plugin_ack",
        mock_annotate,
    )
    mock_version_info = mock.Mock(return_value={"version": "1.0.0"})
    monkeypatch.setattr(
        "koruide.daemon.handlers_ack.DriveOrchestrator.plugin_version_info",
        mock_version_info,
    )
    
    client = mock.Mock()
    client.version = "1.0.0"
    client.build_sha = "build123"
    client.protocol_version = 2
    client.capabilities = ["chat"]
    
    msg = Message(type="ack", id="ack-1", data={"ok": True, "delivered": True})
    
    result = _annotated_plugin_ack_info(
        client,
        msg,
        plugin_ok=True,
        submit_requested=True,
        plugin_ide="vscode",
    )
    
    assert "version" in result
    mock_annotate.assert_called_once()
    mock_version_info.assert_called_once_with(
        plugin_ide="vscode",
        connected_version="1.0.0",
        connected_build_sha="build123",
        protocol_version=2,
        capabilities=["chat"],
    )


def test_relay_message_sent_ack_no_pending() -> None:
    """Test _relay_message_sent_ack returns False when no pending drive."""
    daemon = mock.Mock()
    client = mock.Mock()
    client.awaiting_plugin = None
    
    msg = Message(type="plugin.event", id="e-1", data={"event": "message.sent"})
    result = _relay_message_sent_ack(daemon, client, msg)
    
    assert result is False


def test_relay_message_sent_ack_strict_waits(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test _relay_message_sent_ack returns False when strict ack required."""
    monkeypatch.setattr(
        "koruide.daemon.handlers_ack.DriveOrchestrator.strict_plugin_ack_required",
        mock.Mock(return_value=True),
    )
    
    daemon = mock.Mock()
    client = mock.Mock()
    client.awaiting_plugin = (
        mock.Mock(),  # cli_client
        "corr-1",     # corr
        True,         # submit_requested
        "vscode",     # plugin_ide
        "text",       # original_text
        False,        # require_plugin
    )
    
    msg = Message(type="plugin.event", id="e-1", data={"event": "message.sent"})
    result = _relay_message_sent_ack(daemon, client, msg)
    
    assert result is False
    daemon.log.assert_called_once()
    assert "waiting for full plugin ack" in daemon.log.call_args[0][0]


def test_relay_message_sent_ack_strict_accepts_deferred_vscodium(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "koruide.daemon.handlers_ack.DriveOrchestrator.strict_plugin_ack_required",
        mock.Mock(return_value=True),
    )
    monkeypatch.setattr(
        "koruide.daemon.handlers_ack.DriveOrchestrator.build_message_sent_info",
        mock.Mock(return_value={"verification": "event_only", "event": "message.sent"}),
    )
    monkeypatch.setattr(
        "koruide.daemon.handlers_ack.DriveOrchestrator.drive_intent_evidence",
        mock.Mock(return_value={"intent_status": "fulfilled"}),
    )
    monkeypatch.setattr(
        "koruide.daemon.handlers_ack.DriveOrchestrator.plugin_version_info",
        mock.Mock(return_value={}),
    )
    monkeypatch.setattr(
        "koruide.daemon.handlers._cli_client_still_connected",
        mock.Mock(return_value=True),
    )

    daemon = mock.Mock()
    client = mock.Mock()
    client.awaiting_plugin = (
        mock.Mock(),
        "corr-1",
        True,
        "vscodium",
        "text",
        True,
    )
    client.awaiting_plugin_info = {"verification": "submit_unverified", "ide": "vscodium"}
    client.awaiting_plugin_timer = mock.Mock()
    client.version = "0.2.7"
    client.build_sha = "build123"
    client.protocol_version = 2
    client.capabilities = ["chat.events"]
    daemon._send.return_value = True

    msg = Message(type="message.sent", id="e-1", data={"chat": "default"})
    result = _relay_message_sent_ack(daemon, client, msg)

    assert result is True
    assert client.awaiting_plugin is None
    assert client.awaiting_plugin_info is None
    assert client.awaiting_plugin_timer is None
    daemon._send.assert_called_once()
    assert any(
        "strict ack accepted late message.sent fallback for vscodium" in call.args[0]
        for call in daemon.log.call_args_list
    )


def test_relay_message_sent_ack_rejects_poisoned_deferred_vscodium(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "koruide.daemon.handlers_ack.DriveOrchestrator.strict_plugin_ack_required",
        mock.Mock(return_value=True),
    )

    daemon = mock.Mock()
    client = mock.Mock()
    client.awaiting_plugin = (
        mock.Mock(),
        "corr-1",
        True,
        "vscodium",
        "text",
        True,
    )
    client.awaiting_plugin_info = {
        "verification": "submit_unverified",
        "ide": "vscodium",
        "attempted_submit": "workbench.action.chat.submit",
        "operation_trace": [
            {
                "op": "submit_verify",
                "route": "sentinel-clipboard",
                "ok": True,
                "detail": {
                    "observedLength": -1,
                    "requireEmptyAfterSubmit": False,
                },
            }
        ],
    }

    msg = Message(type="message.sent", id="e-1", data={"chat": "default"})
    result = _relay_message_sent_ack(daemon, client, msg)

    assert result is False
    assert client.awaiting_plugin is not None
    daemon._send.assert_not_called()
    assert any(
        "late message.sent ignored for poisoned submit_unverified" in call.args[0]
        for call in daemon.log.call_args_list
    )


def test_relay_message_sent_ack_strict_accepts_deferred_cursor(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "koruide.daemon.handlers_ack.DriveOrchestrator.strict_plugin_ack_required",
        mock.Mock(return_value=True),
    )
    monkeypatch.setattr(
        "koruide.daemon.handlers_ack.DriveOrchestrator.build_message_sent_info",
        mock.Mock(return_value={"verification": "event_only", "event": "message.sent"}),
    )
    monkeypatch.setattr(
        "koruide.daemon.handlers_ack.DriveOrchestrator.drive_intent_evidence",
        mock.Mock(return_value={"intent_status": "fulfilled"}),
    )
    monkeypatch.setattr(
        "koruide.daemon.handlers_ack.DriveOrchestrator.plugin_version_info",
        mock.Mock(return_value={}),
    )
    monkeypatch.setattr(
        "koruide.daemon.handlers._cli_client_still_connected",
        mock.Mock(return_value=True),
    )

    daemon = mock.Mock()
    client = mock.Mock()
    client.awaiting_plugin = (
        mock.Mock(),
        "corr-1",
        True,
        "cursor",
        "text",
        True,
    )
    client.awaiting_plugin_info = {"verification": "submit_unverified", "ide": "cursor"}
    client.awaiting_plugin_timer = mock.Mock()
    client.version = "0.2.7"
    client.build_sha = "build123"
    client.protocol_version = 2
    client.capabilities = ["chat.events"]
    daemon._send.return_value = True

    msg = Message(type="message.sent", id="e-1", data={"chat": "default"})
    result = _relay_message_sent_ack(daemon, client, msg)

    assert result is True
    assert client.awaiting_plugin is None
    assert client.awaiting_plugin_info is None
    assert client.awaiting_plugin_timer is None
    daemon._send.assert_called_once()
    assert any(
        "strict ack accepted late message.sent fallback for cursor" in call.args[0]
        for call in daemon.log.call_args_list
    )


def test_handle_ack_no_pending() -> None:
    """Test handle_ack returns early when no pending drive."""
    daemon = mock.Mock()
    client = mock.Mock()
    client.awaiting_plugin = None
    
    msg = Message(type="ack", id="ack-1", data={"ok": True})
    handle_ack(daemon, client, msg)
    
    daemon._send.assert_not_called()


def test_handle_ack_mismatched_id() -> None:
    """Test handle_ack returns early when message id doesn't match pending."""
    daemon = mock.Mock()
    client = mock.Mock()
    client.awaiting_plugin = (
        mock.Mock(),  # cli_client
        "corr-1",     # corr
        True,         # submit_requested
        "vscode",     # plugin_ide
        "text",       # original_text
        False,        # require_plugin
    )
    
    msg = Message(type="ack", id="ack-1", data={"ok": True})  # id != corr
    handle_ack(daemon, client, msg)
    
    daemon._send.assert_not_called()


def test_record_plugin_ack_integration_success(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test _record_plugin_ack_integration records success correctly."""
    mock_record = mock.Mock()
    monkeypatch.setattr(
        "koruide.daemon.handlers_ack.record_integration_action",
        mock_record,
    )
    mock_emit_verify = mock.Mock()
    monkeypatch.setattr(
        "koruide.daemon.handlers_ack.emit_verify",
        mock_emit_verify,
    )
    
    daemon = mock.Mock()
    daemon.project = "/tmp/test"
    
    info = {"delivered": True, "submitted": True, "verification": "submit"}
    
    _record_plugin_ack_integration(
        daemon,
        corr="corr-1",
        target_ide="vscode",
        info=info,
        plugin_ok=True,
        summary="test summary",
        route_summary="route",
    )
    
    mock_record.assert_called_once()
    assert mock_record.call_args[1]["outcome"] == "ok"
    mock_emit_verify.assert_called_once()


def test_record_plugin_ack_integration_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test _record_plugin_ack_integration records failure correctly."""
    mock_record = mock.Mock()
    monkeypatch.setattr(
        "koruide.daemon.handlers_ack.record_integration_action",
        mock_record,
    )
    mock_emit_failure = mock.Mock()
    monkeypatch.setattr(
        "koruide.daemon.handlers_ack.emit_failure",
        mock_emit_failure,
    )
    
    daemon = mock.Mock()
    daemon.project = "/tmp/test"
    
    info = {"delivered": False, "reason": "timeout"}
    
    _record_plugin_ack_integration(
        daemon,
        corr="corr-1",
        target_ide="vscode",
        info=info,
        plugin_ok=False,
        summary="test summary",
        route_summary="",
    )
    
    mock_record.assert_called_once()
    assert mock_record.call_args[1]["outcome"] == "failed"
    mock_emit_failure.assert_called_once()


def test_send_plugin_ack_reply_persists_operator_replay_dsl(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    monkeypatch.setattr(
        "koruide.daemon.handlers_ack._record_plugin_ack_integration",
        mock.Mock(),
    )
    monkeypatch.setattr(
        "koruide.daemon.handlers._cli_client_still_connected",
        mock.Mock(return_value=True),
    )
    daemon = mock.Mock()
    daemon.project = tmp_path
    daemon._recent_dsl = []
    daemon._command_telemetry.record_from_ack = mock.Mock()
    daemon._send.return_value = True

    info = {
        "delivered": True,
        "verification": "submit_unverified",
        "attempted_submit": "workbench.action.chat.submit",
        "submit_failure_reason": "input still contains pasted text",
        "operation_trace": [{"op": "submit", "route": "vscodium", "ok": False}],
    }

    _send_plugin_ack_reply(
        daemon,
        mock.Mock(),
        "corr/replay",
        "vscodium",
        info=info,
        plugin_ok=False,
        original_text="hello from replay",
    )

    replay_path = tmp_path / ".planfile" / ".koru" / "replay" / "corr-replay.prompt"
    assert replay_path.read_text(encoding="utf-8") == "hello from replay"
    assert "--prompt-file" in info["replay_command"]
    assert info["drive_dsl_operator"][0].startswith(
        "#900 act=diagnose severity=error code=submit_not_verified",
    )
    assert any(line.startswith("#902 act=replay") for line in daemon._recent_dsl)
    assert (tmp_path / ".planfile" / ".koru" / "dsl_recent.json").exists()
    daemon.audit.record.assert_called_once_with(
        "drive",
        ide="vscodium",
        backend="plugin",
        chars=len("hello from replay"),
        submit=True,
        ok=False,
        verification="submit_unverified",
        delivered=True,
        submitted=None,
        corr="corr/replay",
    )


# ---------------------------------------------------------------------------
# Backward compatibility tests
# ---------------------------------------------------------------------------

def test_backward_compat_reexports_from_handlers() -> None:
    """Test that ack functions are re-exported from handlers module."""
    from koruide.daemon import handlers
    
    assert handlers.handle_ack is handle_ack
    assert handlers._annotated_plugin_ack_info is _annotated_plugin_ack_info
    assert handlers._strict_plugin_ack_ok is _strict_plugin_ack_ok
    assert handlers._record_plugin_ack_integration is _record_plugin_ack_integration
