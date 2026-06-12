"""Unit tests for koru.autopilot.commands.drive module (R5b)."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import pytest

from koru.autopilot.commands.drive import (
    DriveRepairReaction,
    _diagnose_bridge_after_drive_failure,
    _drive_command_argv,
    action_drive,
)
from koru.bounded_contexts.repairs.events import (
    REPAIR_ATTEMPT_RECORDED,
    REPAIR_DIAGNOSTIC_RECORDED,
)
from koru.cqrs import runtime_for_project


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
    
    with mock.patch("sys.stderr"):
        result = action_drive(
            args,
            client_fn=mock.Mock(),
            daemon_start_hint_fn=mock.Mock(),
            run_direct_drive_fn=mock.Mock(),
            should_fallback_fn=mock.Mock(),
        )
    
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
    mock_client.drive.assert_called_once_with(
        "test",
        submit=True,
        ide="vscode",
        require_plugin=False,
    )


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


def test_action_drive_reacts_to_bridge_diagnostic_with_direct_fallback() -> None:
    """A failed daemon reply can trigger diagnostic-driven direct fallback."""
    args = argparse.Namespace(
        prompt="test",
        text=[],
        ide="vscodium",
        submit=True,
        dry_run=False,
        require_plugin=False,
        direct=False,
        project=None,
    )
    mock_client = mock.Mock()
    mock_client.is_running.return_value = True
    mock_client.socket_path = Path("/tmp/koru-autopilot-vscodium.sock")
    mock_client.drive.return_value = {
        "ok": False,
        "message": "plugin bridge not ready",
        "backend": None,
    }
    mock_run_direct = mock.Mock(return_value=(0, {"ok": True, "backend": "direct"}))
    observed: dict[str, object] = {}

    def repair_reaction(got_args, got_client, reply):  # noqa: ANN001, ANN202
        observed["args"] = got_args
        observed["client"] = got_client
        observed["reply"] = reply
        return DriveRepairReaction(
            fallback_to_direct=True,
            reason="bridge diagnostic: vscodium.plugin.not_connected",
        )

    with mock.patch("builtins.print"):
        with mock.patch("sys.stderr"):
            with mock.patch("koru.autopilot.commands.drive.shell_command"):
                result = action_drive(
                    args,
                    client_fn=mock.Mock(return_value=mock_client),
                    daemon_start_hint_fn=mock.Mock(),
                    run_direct_drive_fn=mock_run_direct,
                    should_fallback_fn=mock.Mock(return_value=False),
                    repair_reaction_fn=repair_reaction,
                )

    assert result == 0
    assert observed["args"] is args
    assert observed["client"] is mock_client
    assert observed["reply"] == mock_client.drive.return_value
    mock_run_direct.assert_called_once()


def test_drive_failure_diagnostic_records_history_and_selects_direct_fallback(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from koru.ide_adapters import bridge as bridge_mod

    args = argparse.Namespace(
        ide="vscodium",
        require_plugin=False,
        project=tmp_path,
        socket=None,
    )
    client = argparse.Namespace(socket_path=tmp_path / "koru-autopilot-vscodium.sock")
    reply = {
        "ok": False,
        "message": "plugin bridge not ready",
        "backend": None,
        "opened": False,
        "submitted": False,
    }
    status = SimpleNamespace(
        ide="vscodium",
        socket_path=str(client.socket_path),
        project=str(tmp_path),
        daemon_running=True,
        plugins_connected=True,
        plugins_compatible=False,
        ready=False,
        fixes_applied=[],
        hypotheses=[
            SimpleNamespace(
                id="vscodium.plugin.build_mismatch",
                confidence=0.95,
                evidence="old-build != new-build",
                remediation=SimpleNamespace(
                    summary="Developer: Reload Window",
                    kind="manual",
                    command=None,
                ),
            )
        ],
    )
    monkeypatch.setattr(bridge_mod, "evaluate_bridge", lambda **_kwargs: status)

    reaction = _diagnose_bridge_after_drive_failure(args, client, reply)

    assert reaction is not None
    assert reaction.fallback_to_direct is True
    assert "vscodium.plugin.build_mismatch" in reaction.reason
    events = runtime_for_project(tmp_path).store.all_events(context="repairs")
    assert [event.event_type for event in events] == [
        REPAIR_DIAGNOSTIC_RECORDED,
        REPAIR_ATTEMPT_RECORDED,
    ]
    assert events[0].payload["status"]["drive_reply"]["message"] == "plugin bridge not ready"
    assert events[1].payload["actions"] == ["drive reaction: switch to local direct injection"]


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


def test_action_drive_emits_jsonl_contract(capsys: pytest.CaptureFixture) -> None:
    args = argparse.Namespace(
        prompt="test",
        text=[],
        ide="vscode",
        submit=True,
        dry_run=False,
        require_plugin=False,
        direct=False,
        project=None,
        log_format="jsonl",
    )

    mock_client = mock.Mock()
    mock_client.is_running.return_value = True
    mock_client.drive.return_value = {"ok": True, "backend": "plugin"}

    with mock.patch("koru.autopilot.commands.drive.shell_command"):
        result = action_drive(
            args,
            client_fn=mock.Mock(return_value=mock_client),
            daemon_start_hint_fn=mock.Mock(),
            run_direct_drive_fn=mock.Mock(),
            should_fallback_fn=mock.Mock(return_value=False),
        )

    assert result == 0
    err_lines = [
        line for line in capsys.readouterr().err.splitlines() if line.strip().startswith("{")
    ]
    assert err_lines
    payload = json.loads(err_lines[0])
    assert set(["ts", "corr", "component", "level", "action", "result"]).issubset(payload)


def test_action_drive_refuses_direct_when_daemon_blocks_semantic() -> None:
    """Bridge repair must not run os_injector when daemon refused blind keyboard."""
    args = argparse.Namespace(
        prompt="probe test",
        text=[],
        ide="jetbrains",
        submit=True,
        dry_run=False,
        require_plugin=False,
        direct=False,
        project=None,
    )
    semantic_reply = {
        "ok": False,
        "backend": "semantic_required",
        "message": (
            "refusing blind keyboard/OS-injector fallback on Wayland for JetBrains "
            "after vdisplay/imgl did not confirm the target"
        ),
        "opened": None,
        "submitted": None,
    }
    mock_client = mock.Mock()
    mock_client.is_running.return_value = True
    mock_client.socket_path = Path("/tmp/koru-autopilot-jetbrains.sock")
    mock_client.drive.return_value = semantic_reply
    mock_run_direct = mock.Mock(return_value=(0, {"ok": True, "backend": "os_injector"}))

    def repair_reaction(_args, _client, _reply):  # noqa: ANN001, ANN202
        return DriveRepairReaction(
            fallback_to_direct=True,
            reason="bridge diagnostic: ide.keyboard_lane",
        )

    with mock.patch("builtins.print") as mock_print:
        with mock.patch("sys.stderr"):
            with mock.patch("koru.autopilot.commands.drive.shell_command"):
                result = action_drive(
                    args,
                    client_fn=mock.Mock(return_value=mock_client),
                    daemon_start_hint_fn=mock.Mock(),
                    run_direct_drive_fn=mock_run_direct,
                    should_fallback_fn=mock.Mock(return_value=False),
                    repair_reaction_fn=repair_reaction,
                )

    assert result == 1
    mock_run_direct.assert_not_called()
    printed = " ".join(str(call.args[0]) for call in mock_print.call_args_list)
    assert "semantic_required" in printed or "refusing blind keyboard" in printed


# ---------------------------------------------------------------------------
# Backward compatibility tests
# ---------------------------------------------------------------------------

def test_backward_compat_reexports_from_cli_command() -> None:
    """Test that drive functions are re-exported from cli_command module."""
    from koru.autopilot import cli_command
    
    assert hasattr(cli_command, "_drive_command_argv")
    assert hasattr(cli_command, "_drive_action_impl")
