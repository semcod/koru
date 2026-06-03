"""Unit tests for koru.autopilot.commands.shutdown module (R5b)."""
from __future__ import annotations

import argparse
import json
from unittest import mock

from koru.autopilot.commands.shutdown import action_shutdown


def test_action_shutdown_success() -> None:
    """Test action_shutdown delegates to daemon_shutdown_fn."""
    args = argparse.Namespace()
    
    mock_client_fn = mock.Mock()
    mock_shutdown_fn = mock.Mock(return_value=0)
    
    result = action_shutdown(
        args,
        client_fn=mock_client_fn,
        daemon_shutdown_fn=mock_shutdown_fn,
    )
    
    assert result == 0
    mock_shutdown_fn.assert_called_once_with(args, client_fn=mock_client_fn)


def test_action_shutdown_error() -> None:
    """Test action_shutdown returns error code from daemon_shutdown_fn."""
    args = argparse.Namespace()
    
    mock_shutdown_fn = mock.Mock(return_value=1)
    
    result = action_shutdown(
        args,
        client_fn=mock.Mock(),
        daemon_shutdown_fn=mock_shutdown_fn,
    )
    
    assert result == 1


def test_action_shutdown_propagates_exception() -> None:
    """Test action_shutdown propagates exceptions from daemon_shutdown_fn."""
    args = argparse.Namespace()
    
    mock_shutdown_fn = mock.Mock(side_effect=OSError("Shutdown failed"))
    
    try:
        action_shutdown(
            args,
            client_fn=mock.Mock(),
            daemon_shutdown_fn=mock_shutdown_fn,
        )
        assert False, "Should have raised OSError"
    except OSError as e:
        assert str(e) == "Shutdown failed"


def test_action_shutdown_emits_jsonl_contract(capsys) -> None:
    args = argparse.Namespace(log_format="jsonl")

    rc = action_shutdown(
        args,
        client_fn=mock.Mock(),
        daemon_shutdown_fn=mock.Mock(return_value=0),
    )

    assert rc == 0
    err_lines = [line for line in capsys.readouterr().err.splitlines() if line.strip().startswith("{")]
    assert err_lines
    payload = json.loads(err_lines[0])
    assert set(["ts", "corr", "component", "level", "action", "result"]).issubset(payload)


# ---------------------------------------------------------------------------
# Backward compatibility tests
# ---------------------------------------------------------------------------

def test_backward_compat_reexports_from_cli_command() -> None:
    """Test that shutdown functions are re-exported from cli_command module."""
    from koru.autopilot import cli_command
    
    assert hasattr(cli_command, "_shutdown_action_impl")
    assert hasattr(cli_command, "_action_shutdown")
