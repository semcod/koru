"""Unit tests for koruide.daemon.handlers_hello module (R6)."""
from __future__ import annotations

from unittest import mock

import pytest

from koruide.daemon.handlers_hello import (
    _configure_plugin_client,
    _extract_hello_metadata,
    _handle_plugin_version_check,
    _log_plugin_hello_accepted,
    _log_rejected_plugin_connection,
    handle_hello,
)
from koruide.protocol import Message


def test_extract_hello_metadata_complete() -> None:
    """Test _extract_hello_metadata with all fields."""
    msg = Message(
        type="hello",
        id="h-1",
        data={
            "ide": "vscode",
            "version": "1.0.0",
            "buildSha": "build123",
            "protocolVersion": 2,
            "capabilities": ["chat", "commands"],
            "workspaceName": "koru",
            "workspaceFolders": ["/repo/koru"],
        },
    )
    ide, version, build_sha, protocol, caps, workspace_name, workspace_folders = _extract_hello_metadata(msg)
    assert ide == "vscode"
    assert version == "1.0.0"
    assert build_sha == "build123"
    assert protocol == 2
    assert caps == ["chat", "commands"]
    assert workspace_name == "koru"
    assert workspace_folders == ["/repo/koru"]


def test_extract_hello_metadata_minimal() -> None:
    """Test _extract_hello_metadata with minimal data."""
    msg = Message(type="hello", id="h-1", data={"ide": "cursor"})
    ide, version, build_sha, protocol, caps, workspace_name, workspace_folders = _extract_hello_metadata(msg)
    assert ide == "cursor"
    assert version is None
    assert build_sha is None
    assert protocol is None
    assert caps == []
    assert workspace_name is None
    assert workspace_folders == []


def test_extract_hello_metadata_no_ide() -> None:
    """Test _extract_hello_metadata without ide field."""
    msg = Message(type="hello", id="h-1", data={})
    ide, _version, _build_sha, _protocol, _caps, _workspace_name, _workspace_folders = _extract_hello_metadata(msg)
    assert ide is None


def test_configure_plugin_client() -> None:
    """Test _configure_plugin_client sets all attributes."""
    daemon = mock.Mock()
    client = mock.Mock()
    client.role = "unknown"
    
    _configure_plugin_client(
        daemon,
        client,
        ide="vscode",
        plugin_version="1.0.0",
        build_sha="build123",
        protocol_version=2,
        capabilities=["chat"],
        workspace_name="koru",
        workspace_folders=["/repo/koru"],
    )
    
    assert client.role == "plugin"
    assert client.ide == "vscode"
    assert client.version == "1.0.0"
    assert client.build_sha == "build123"
    assert client.protocol_version == 2
    assert client.capabilities == ["chat"]
    assert client.workspace_name == "koru"
    assert client.workspace_folders == ["/repo/koru"]
    daemon._plugin_router.drop_stale_plugins.assert_called_once_with(client, "vscode")


def test_log_plugin_hello_accepted() -> None:
    """Test _log_plugin_hello_accepted logs correctly."""
    daemon = mock.Mock()
    version_info = {"expected_plugin_version": "1.0.0", "plugin_version_policy": "strict"}
    
    _log_plugin_hello_accepted(
        daemon,
        ide="vscode",
        plugin_version="1.0.0",
        build_sha="build123",
        protocol_version=2,
        capabilities=["chat", "commands"],
        version_info=version_info,
        matching_cmds=["cmd1", "cmd2"],
        workspace_name="koru",
        workspace_folders=["/repo/koru"],
    )
    
    daemon.log.assert_called_once()
    log_msg = daemon.log.call_args[0][0]
    assert "plugin hello accepted" in log_msg
    assert "vscode" in log_msg
    assert "2" in log_msg  # protocol


def test_log_rejected_plugin_connection_rate_limiting() -> None:
    """Test _log_rejected_plugin_connection implements rate limiting."""
    daemon = mock.Mock()
    daemon._plugin_rejection_log_state = {}
    daemon._plugin_rejections = []
    
    # First call should log
    _log_rejected_plugin_connection(
        daemon,
        ide="vscode",
        plugin_version="0.9.0",
        expected_plugin_version="1.0.0",
        message="version mismatch",
    )
    # Should log at least once (main rejection message + potentially details)
    assert daemon.log.call_count >= 1
    
    # Second immediate call should be suppressed (within rate limit window)
    daemon.log.reset_mock()
    _log_rejected_plugin_connection(
        daemon,
        ide="vscode",
        plugin_version="0.9.0",
        expected_plugin_version="1.0.0",
        message="version mismatch",
    )
    # Should be suppressed due to rate limiting
    assert daemon.log.call_count == 0


def test_handle_hello_rejects_missing_ide() -> None:
    """Test handle_hello rejects hello without ide."""
    daemon = mock.Mock()
    client = mock.Mock()
    
    msg = Message(type="hello", id="h-1", data={})
    handle_hello(daemon, client, msg)
    
    daemon._send.assert_called_once()
    call_args = daemon._send.call_args[0]
    assert call_args[0] == client
    assert "hello requires" in call_args[1].decode().lower()


def test_handle_hello_accepts_valid_plugin(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test handle_hello accepts valid plugin connection."""
    daemon = mock.Mock()
    client = mock.Mock()
    client.role = "unknown"
    
    msg = Message(
        type="hello",
        id="h-1",
        data={
            "ide": "vscode",
            "version": "1.0.0",
            "protocolVersion": 1,
            "capabilities": [],
        },
    )
    
    # Mock version check to pass
    monkeypatch.setattr(
        "koruide.daemon.handlers_hello._handle_plugin_version_check",
        lambda *args, **kwargs: True,
    )
    
    handle_hello(daemon, client, msg)
    
    # Should send ack
    daemon._send.assert_called_once()
    call_args = daemon._send.call_args[0]
    assert call_args[0] == client
    assert '"role":"plugin"' in call_args[1].decode()
    
    # Should record audit
    daemon.audit.record.assert_called_once()
    assert daemon.audit.record.call_args[1]["ide"] == "vscode"


# ---------------------------------------------------------------------------
# Backward compatibility tests
# ---------------------------------------------------------------------------

def test_backward_compat_reexports_from_handlers() -> None:
    """Test that hello functions are re-exported from handlers module."""
    from koruide.daemon import handlers
    
    assert handlers.handle_hello is handle_hello
    assert handlers._extract_hello_metadata is _extract_hello_metadata
    assert handlers._configure_plugin_client is _configure_plugin_client
    assert handlers._log_rejected_plugin_connection is _log_rejected_plugin_connection
