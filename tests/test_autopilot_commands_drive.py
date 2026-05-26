"""Unit tests for koru.autopilot.commands.drive module (R5b)."""
from __future__ import annotations

import argparse
from pathlib import Path
from unittest import mock

import pytest

from koru.autopilot.commands.drive import (
    _drive_command_argv,
    action_drive,
)


def test_drive_command_argv_basic() -> None:
    """Test _drive_command_argv builds correct argv."""
    args = argparse.Namespace(
        ide="vscode",
        submit=True,
        require_plugin=False,
        direct=False,
        prompt=None,
    )
    argv = _drive_command_argv(args, "hello world")
    assert argv == ["koru", "autopilot", "drive", "--ide", "vscode", "hello world"]


def test_drive_command_argv_no_submit() -> None:
    """Test _drive_command_argv with --no-submit."""
    args = argparse.Namespace(
        ide="windsurf",
        submit=False,
        require_plugin=False,
        direct=False,
        prompt=None,
    )
    argv = _drive_command_argv(args, "test")
    assert "--no-submit" in argv


def test_drive_command_argv_require_plugin() -> None:
    """Test _drive_command_argv with --require-plugin."""
    args = argparse.Namespace(
        ide="cursor",
        submit=True,
        require_plugin=True,
        direct=False,
        prompt=None,
    )
    argv = _drive_command_argv(args, "test")
    assert "--require-plugin" in argv


def test_drive_command_argv_direct() -> None:
    """Test _drive_command_argv with --direct."""
    args = argparse.Namespace(
        ide="auto",
        submit=True,
        require_plugin=False,
        direct=True,
        prompt=None,
    )
    argv = _drive_command_argv(args, "test")
    assert "--direct" in argv


def test_drive_command_argv_with_prompt() -> None:
    """Test _drive_command_argv with --prompt."""
    args = argparse.Namespace(
        ide="vscode",
        submit=True,
        require_plugin=False,
        direct=False,
        prompt="hello world",
    )
    argv = _drive_command_argv(args, "hello world")
    assert "--prompt" in argv
    assert "hello world" in argv


def test_drive_command_argv_with_prompt_file() -> None:
    """Test _drive_command_argv with replay-safe --prompt-file."""
    args = argparse.Namespace(
        ide="vscodium",
        submit=True,
        require_plugin=True,
        direct=False,
        prompt=None,
        prompt_file=Path("/tmp/drive.prompt"),
    )
    argv = _drive_command_argv(args, "hello world")
    assert argv == [
        "koru",
        "autopilot",
        "drive",
        "--ide",
        "vscodium",
        "--require-plugin",
        "--prompt-file",
        "/tmp/drive.prompt",
    ]


def test_action_drive_missing_text() -> None:
    """Test action_drive returns 2 when text is missing."""
    args = argparse.Namespace(
        prompt=None,
        prompt_file=None,
        text=[],
        ide="auto",
        submit=True,
        dry_run=False,
        require_plugin=False,
        direct=False,
        project=None,
    )
    
    with mock.patch("sys.stderr") as mock_stderr:
        result = action_drive(args, client_fn=mock.Mock(), daemon_start_hint_fn=mock.Mock(), run_direct_drive_fn=mock.Mock(), should_fallback_fn=mock.Mock())
    
    assert result == 2


def test_action_drive_direct_mode() -> None:
    """Test action_drive uses direct mode when --direct flag is set."""
    args = argparse.Namespace(
        prompt="test text",
        prompt_file=None,
        text=[],
        ide="vscode",
        submit=True,
        dry_run=False,
        require_plugin=False,
        direct=True,
        project=None,
    )
    
    mock_run_direct = mock.Mock(return_value=(0, {"ok": True}))
    
    with mock.patch("koru.autopilot.commands.drive.shell_command"):
        result = action_drive(
            args,
            client_fn=mock.Mock(),
            daemon_start_hint_fn=mock.Mock(),
            run_direct_drive_fn=mock_run_direct,
            should_fallback_fn=mock.Mock(),
        )
    
    assert result == 0
    mock_run_direct.assert_called_once_with(args, "test text", emit_payload=True)


def test_action_drive_daemon_not_running() -> None:
    """Test action_drive returns 2 when daemon is not running."""
    args = argparse.Namespace(
        prompt="test",
        text=[],
        ide="auto",
        submit=True,
        dry_run=False,
        require_plugin=False,
        direct=False,
        project=None,
    )
    
    mock_client = mock.Mock()
    mock_client.is_running.return_value = False
    mock_client_fn = mock.Mock(return_value=mock_client)
    mock_hint_fn = mock.Mock(return_value="Start daemon with 'koru autopilot daemon'")
    
    with mock.patch("sys.stderr"):
        with mock.patch("koru.autopilot.commands.drive.shell_command"):
            result = action_drive(
                args,
                client_fn=mock_client_fn,
                daemon_start_hint_fn=mock_hint_fn,
                run_direct_drive_fn=mock.Mock(),
                should_fallback_fn=mock.Mock(),
            )
    
    assert result == 2


def test_action_drive_dry_run() -> None:
    """Test action_drive prints dry-run message and exits."""
    args = argparse.Namespace(
        prompt="hello world",
        text=[],
        ide="vscode",
        submit=True,
        dry_run=True,
        require_plugin=False,
        direct=False,
        project=None,
    )
    
    mock_client = mock.Mock()
    mock_client.is_running.return_value = True
    
    with mock.patch("builtins.print") as mock_print:
        with mock.patch("koru.autopilot.commands.drive.shell_command"):
            result = action_drive(
                args,
                client_fn=mock.Mock(return_value=mock_client),
                daemon_start_hint_fn=mock.Mock(),
                run_direct_drive_fn=mock.Mock(),
                should_fallback_fn=mock.Mock(),
            )
    
    assert result == 0
    mock_print.assert_called_once()
    assert "dry-run" in str(mock_print.call_args)


def test_action_drive_prompt_file_preserves_prompt_bytes(tmp_path: Path) -> None:
    """Replay-safe --prompt-file preserves whitespace in the stored prompt."""
    prompt_path = tmp_path / "drive.prompt"
    prompt_path.write_text("hello replay\n", encoding="utf-8")
    args = argparse.Namespace(
        prompt=None,
        prompt_file=prompt_path,
        text=[],
        ide="vscodium",
        submit=True,
        dry_run=False,
        require_plugin=True,
        direct=False,
        project=None,
    )
    mock_client = mock.Mock()
    mock_client.is_running.return_value = True
    mock_client.drive.return_value = {"ok": True}

    with mock.patch("builtins.print"):
        with mock.patch("koru.autopilot.commands.drive.shell_command"):
            result = action_drive(
                args,
                client_fn=mock.Mock(return_value=mock_client),
                daemon_start_hint_fn=mock.Mock(),
                run_direct_drive_fn=mock.Mock(),
                should_fallback_fn=mock.Mock(return_value=False),
            )

    assert result == 0
    mock_client.drive.assert_called_once_with(
        "hello replay\n",
        submit=True,
        ide="vscodium",
        require_plugin=True,
    )


def test_action_drive_success() -> None:
    """Test action_drive returns 0 on successful drive."""
    args = argparse.Namespace(
        prompt="test",
        text=[],
        ide="vscode",
        submit=True,
        dry_run=False,
        require_plugin=False,
        direct=False,
        project=None,
    )
    
    mock_client = mock.Mock()
    mock_client.is_running.return_value = True
    mock_client.drive.return_value = {"ok": True, "message": "sent"}
    
    mock_should_fallback = mock.Mock(return_value=False)
    
    with mock.patch("builtins.print"):
        with mock.patch("koru.autopilot.commands.drive.shell_command"):
            result = action_drive(
                args,
                client_fn=mock.Mock(return_value=mock_client),
                daemon_start_hint_fn=mock.Mock(),
                run_direct_drive_fn=mock.Mock(),
                should_fallback_fn=mock_should_fallback,
            )
    
    assert result == 0
    mock_client.drive.assert_called_once_with("test", submit=True, ide="vscode", require_plugin=False)


def test_action_drive_failure_reply() -> None:
    """Test action_drive returns 1 when reply is not ok."""
    args = argparse.Namespace(
        prompt="test",
        text=[],
        ide="vscode",
        submit=True,
        dry_run=False,
        require_plugin=False,
        direct=False,
        project=None,
    )
    
    mock_client = mock.Mock()
    mock_client.is_running.return_value = True
    mock_client.drive.return_value = {"ok": False, "message": "error"}
    
    mock_should_fallback = mock.Mock(return_value=False)
    
    with mock.patch("builtins.print"):
        with mock.patch("koru.autopilot.commands.drive.shell_command"):
            result = action_drive(
                args,
                client_fn=mock.Mock(return_value=mock_client),
                daemon_start_hint_fn=mock.Mock(),
                run_direct_drive_fn=mock.Mock(),
                should_fallback_fn=mock_should_fallback,
            )
    
    assert result == 1


def test_action_drive_with_fallback() -> None:
    """Test action_drive falls back to direct drive when fallback condition is met."""
    args = argparse.Namespace(
        prompt="test",
        text=[],
        ide="vscode",
        submit=True,
        dry_run=False,
        require_plugin=False,
        direct=False,
        project=None,
    )
    
    mock_client = mock.Mock()
    mock_client.is_running.return_value = True
    mock_client.drive.return_value = {"ok": False, "opened": False, "message": "failed"}
    
    mock_should_fallback = mock.Mock(return_value=True)
    mock_run_direct = mock.Mock(return_value=(0, {"ok": True, "chars": 4}))
    
    with mock.patch("builtins.print"):
        with mock.patch("sys.stderr"):
            with mock.patch("koru.autopilot.commands.drive.shell_command"):
                result = action_drive(
                    args,
                    client_fn=mock.Mock(return_value=mock_client),
                    daemon_start_hint_fn=mock.Mock(),
                    run_direct_drive_fn=mock_run_direct,
                    should_fallback_fn=mock_should_fallback,
                )
    
    assert result == 0
    mock_run_direct.assert_called_once()


def test_action_drive_exception() -> None:
    """Test action_drive handles exceptions from client.drive()."""
    args = argparse.Namespace(
        prompt="test",
        text=[],
        ide="vscode",
        submit=True,
        dry_run=False,
        require_plugin=False,
        direct=False,
        project=None,
    )
    
    mock_client = mock.Mock()
    mock_client.is_running.return_value = True
    mock_client.drive.side_effect = OSError("Connection failed")
    
    with mock.patch("sys.stderr"):
        with mock.patch("koru.autopilot.commands.drive.shell_command"):
            result = action_drive(
                args,
                client_fn=mock.Mock(return_value=mock_client),
                daemon_start_hint_fn=mock.Mock(),
                run_direct_drive_fn=mock.Mock(),
                should_fallback_fn=mock.Mock(),
            )
    
    assert result == 1


# ---------------------------------------------------------------------------
# Backward compatibility tests
# ---------------------------------------------------------------------------

def test_backward_compat_reexports_from_cli_command() -> None:
    """Test that drive functions are re-exported from cli_command module."""
    from koru.autopilot import cli_command
    
    assert hasattr(cli_command, "_drive_command_argv")
    assert hasattr(cli_command, "_drive_action_impl")
