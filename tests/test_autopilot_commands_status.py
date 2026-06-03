"""Unit tests for koru.autopilot.commands.status module (R5b)."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from unittest import mock

import pytest

from koru.autopilot.commands.status import (
    _print_status_json,
    _print_status_explain_summary,
    action_status,
)


def test_print_status_json(capsys: pytest.CaptureFixture) -> None:
    """Test _print_status_json prints formatted JSON."""
    info = {"plugins": [], "running": True, "version": "1.0"}
    _print_status_json(info)
    
    captured = capsys.readouterr()
    assert '"plugins": []' in captured.out
    assert '"running": true' in captured.out
    assert '"version": "1.0"' in captured.out


def test_print_status_explain_summary(capsys: pytest.CaptureFixture) -> None:
    """Human status summary should explain the active daemon lane in stderr."""
    _print_status_explain_summary(
        {
            "daemon": {
                "pid": 123,
                "version": "0.1.287",
                "git_sha": "abc123",
                "python_executable": "/venv/bin/python",
            },
            "plugins": [{"ide": "vscodium"}],
        },
        Path("/tmp/koru-autopilot-vscodium.sock"),
    )

    captured = capsys.readouterr()
    assert "--- runtime ---" in captured.err
    assert "pid=123" in captured.err
    assert "plugins: 1 (vscodium)" in captured.err


def test_action_status_daemon_not_running() -> None:
    """Test action_status returns 1 when daemon is not running."""
    args = argparse.Namespace(
        explain=False,
        project=Path.cwd(),
    )
    
    mock_client = mock.Mock()
    mock_client.is_running.return_value = False
    mock_client.socket_path = Path("/tmp/test.sock")
    
    mock_client_fn = mock.Mock(return_value=mock_client)
    mock_hint_fn = mock.Mock(return_value="Start daemon with 'koru autopilot daemon'")
    
    with mock.patch("builtins.print") as mock_print:
        result = action_status(
            args,
            client_fn=mock_client_fn,
            daemon_start_hint_fn=mock_hint_fn,
            normalize_ide_fn=mock.Mock(),
            resolve_target_ide_fn=mock.Mock(),
        )
    
    assert result == 1
    assert mock_print.call_count == 2  # daemon not running + hint


def test_action_status_daemon_not_running_explain(capsys: pytest.CaptureFixture) -> None:
    """Explain mode should tell operators why status is empty after Ctrl+C."""
    args = argparse.Namespace(
        explain=True,
        project=Path.cwd(),
    )

    mock_client = mock.Mock()
    mock_client.is_running.return_value = False
    mock_client.socket_path = Path("/tmp/test.sock")

    result = action_status(
        args,
        client_fn=mock.Mock(return_value=mock_client),
        daemon_start_hint_fn=mock.Mock(return_value="start it"),
        normalize_ide_fn=mock.Mock(),
        resolve_target_ide_fn=mock.Mock(),
    )

    captured = capsys.readouterr()
    assert result == 1
    assert "daemon is NOT running" in captured.out
    assert "expected after Ctrl+C" in captured.err


def test_action_status_success() -> None:
    """Test action_status returns 0 on success."""
    args = argparse.Namespace(
        explain=False,
        project=Path.cwd(),
    )
    
    mock_client = mock.Mock()
    mock_client.is_running.return_value = True
    mock_client.status.return_value = {"plugins": ["vscode"], "running": True}
    
    with mock.patch("builtins.print") as mock_print:
        result = action_status(
            args,
            client_fn=mock.Mock(return_value=mock_client),
            daemon_start_hint_fn=mock.Mock(),
            normalize_ide_fn=mock.Mock(),
            resolve_target_ide_fn=mock.Mock(),
        )
    
    assert result == 0
    mock_print.assert_called_once()
    assert "vscode" in str(mock_print.call_args)


def test_action_status_exception() -> None:
    """Test action_status handles exceptions."""
    args = argparse.Namespace(
        explain=False,
        project=Path.cwd(),
    )
    
    mock_client = mock.Mock()
    mock_client.is_running.return_value = True
    mock_client.status.side_effect = OSError("Connection failed")
    
    with mock.patch("sys.stderr"):
        result = action_status(
            args,
            client_fn=mock.Mock(return_value=mock_client),
            daemon_start_hint_fn=mock.Mock(),
            normalize_ide_fn=mock.Mock(),
            resolve_target_ide_fn=mock.Mock(),
        )
    
    assert result == 1


def test_action_status_explain_with_empty_plugins(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test action_status with --explain flag when no plugins connected."""
    args = argparse.Namespace(
        explain=True,
        project=Path.cwd(),
    )
    
    mock_client = mock.Mock()
    mock_client.is_running.return_value = True
    mock_client.status.return_value = {"plugins": [], "running": True}
    mock_client.socket_path = Path("/tmp/test.sock")
    
    mock_evaluate = mock.Mock(return_value={"status": "disconnected"})
    mock_format = mock.Mock(return_value="Bridge analysis text")
    monkeypatch.setattr(
        "koru.ide_adapters.bridge.evaluate_bridge",
        mock_evaluate,
    )
    monkeypatch.setattr(
        "koru.ide_adapters.bridge.format_bridge_text",
        mock_format,
    )
    
    with mock.patch("builtins.print"):
        with mock.patch("sys.stderr"):
            result = action_status(
                args,
                client_fn=mock.Mock(return_value=mock_client),
                daemon_start_hint_fn=mock.Mock(),
                normalize_ide_fn=mock.Mock(return_value="vscode"),
                resolve_target_ide_fn=mock.Mock(return_value="vscode"),
            )
    
    assert result == 0


def test_action_status_explain_skipped_with_plugins(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test action_status skips explain output when plugins are connected."""
    args = argparse.Namespace(
        explain=True,
        project=Path.cwd(),
    )
    
    mock_client = mock.Mock()
    mock_client.is_running.return_value = True
    mock_client.status.return_value = {"plugins": [{"ide": "vscode"}], "running": True}
    
    mock_evaluate = mock.Mock()
    monkeypatch.setattr(
        "koru.ide_adapters.bridge.evaluate_bridge",
        mock_evaluate,
    )
    
    with mock.patch("builtins.print"):
        result = action_status(
            args,
            client_fn=mock.Mock(return_value=mock_client),
            daemon_start_hint_fn=mock.Mock(),
            normalize_ide_fn=mock.Mock(),
            resolve_target_ide_fn=mock.Mock(),
        )
    
    assert result == 0
    mock_evaluate.assert_not_called()


def test_action_status_emits_jsonl_contract(capsys: pytest.CaptureFixture) -> None:
    args = argparse.Namespace(
        explain=False,
        project=Path.cwd(),
        ide="cursor",
        log_format="jsonl",
    )

    mock_client = mock.Mock()
    mock_client.is_running.return_value = True
    mock_client.socket_path = Path("/tmp/test.sock")
    mock_client.status.return_value = {"plugins": [], "running": True}

    result = action_status(
        args,
        client_fn=mock.Mock(return_value=mock_client),
        daemon_start_hint_fn=mock.Mock(),
        normalize_ide_fn=mock.Mock(),
        resolve_target_ide_fn=mock.Mock(),
    )

    assert result == 0
    err_lines = [line for line in capsys.readouterr().err.splitlines() if line.strip().startswith("{")]
    assert err_lines
    payload = json.loads(err_lines[0])
    assert set(["ts", "corr", "component", "level", "action", "result"]).issubset(payload)


# ---------------------------------------------------------------------------
# Backward compatibility tests
# ---------------------------------------------------------------------------

def test_backward_compat_reexports_from_cli_command() -> None:
    """Test that status functions are re-exported from cli_command module."""
    from koru.autopilot import cli_command
    
    assert hasattr(cli_command, "_status_action_impl")
    assert hasattr(cli_command, "_action_status")
