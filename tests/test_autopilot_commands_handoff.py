"""Unit tests for koru.autopilot.commands.handoff module (R5b)."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from unittest import mock

import pytest

from koru.autopilot.commands.handoff import _build_brief, action_handoff


def test_build_brief_success() -> None:
    """Test _build_brief builds context and renders markdown."""
    mock_build_context = mock.Mock(return_value={"project": "test"})
    mock_render = mock.Mock(return_value="# Brief\n\nTest content.")

    result = _build_brief(
        Path("/test/project"),
        build_context_fn=mock_build_context,
        render_markdown_handoff_fn=mock_render,
    )

    assert result == "# Brief\n\nTest content."
    mock_build_context.assert_called_once_with(project=Path("/test/project"))
    mock_render.assert_called_once_with({"project": "test"})


def test_action_handoff_dry_run() -> None:
    """Test action_handoff with --dry-run prints brief and exits."""
    args = argparse.Namespace(
        project=Path("/test"),
        dry_run=True,
        submit=False,
        ide=None,
        require_plugin=False,
    )

    mock_client_fn = mock.Mock()
    mock_build_context = mock.Mock(return_value={})
    mock_render = mock.Mock(return_value="# Test Brief")

    result = action_handoff(
        args,
        client_fn=mock_client_fn,
        build_context_fn=mock_build_context,
        render_markdown_handoff_fn=mock_render,
    )

    assert result == 0
    mock_client_fn.assert_not_called()  # No client needed for dry-run


def test_action_handoff_empty_brief() -> None:
    """Test action_handoff fails with empty brief."""
    args = argparse.Namespace(
        project=Path("/test"),
        dry_run=False,
        submit=False,
        ide=None,
        require_plugin=False,
    )

    mock_build_context = mock.Mock(return_value={})
    mock_render = mock.Mock(return_value="   ")  # Empty/whitespace brief

    result = action_handoff(
        args,
        client_fn=mock.Mock(),
        build_context_fn=mock_build_context,
        render_markdown_handoff_fn=mock_render,
    )

    assert result == 1


def test_action_handoff_daemon_not_running() -> None:
    """Test action_handoff returns 2 when daemon not running."""
    args = argparse.Namespace(
        project=Path("/test"),
        dry_run=False,
        submit=True,
        ide="cursor",
        require_plugin=True,
    )

    mock_client = mock.Mock()
    mock_client.is_running.return_value = False
    mock_client_fn = mock.Mock(return_value=mock_client)
    mock_build_context = mock.Mock(return_value={})
    mock_render = mock.Mock(return_value="# Brief content")

    result = action_handoff(
        args,
        client_fn=mock_client_fn,
        build_context_fn=mock_build_context,
        render_markdown_handoff_fn=mock_render,
    )

    assert result == 2
    mock_client.is_running.assert_called_once()


def test_action_handoff_success() -> None:
    """Test successful handoff with daemon drive."""
    args = argparse.Namespace(
        project=Path("/test"),
        dry_run=False,
        submit=True,
        ide="cursor",
        require_plugin=True,
    )

    mock_client = mock.Mock()
    mock_client.is_running.return_value = True
    mock_client.drive.return_value = {
        "ok": True,
        "delivered": True,
        "backend": "plugin",
    }
    mock_client_fn = mock.Mock(return_value=mock_client)
    mock_build_context = mock.Mock(return_value={})
    mock_render = mock.Mock(return_value="# Brief content")

    result = action_handoff(
        args,
        client_fn=mock_client_fn,
        build_context_fn=mock_build_context,
        render_markdown_handoff_fn=mock_render,
    )

    assert result == 0
    mock_client.drive.assert_called_once_with(
        "# Brief content",
        submit=True,
        ide="cursor",
        require_plugin=True,
    )


def test_action_handoff_drive_failure() -> None:
    """Test action_handoff handles drive failure."""
    args = argparse.Namespace(
        project=Path("/test"),
        dry_run=False,
        submit=False,
        ide=None,
        require_plugin=False,
    )

    mock_client = mock.Mock()
    mock_client.is_running.return_value = True
    mock_client.drive.side_effect = RuntimeError("Connection failed")
    mock_client_fn = mock.Mock(return_value=mock_client)
    mock_build_context = mock.Mock(return_value={})
    mock_render = mock.Mock(return_value="# Brief")

    result = action_handoff(
        args,
        client_fn=mock_client_fn,
        build_context_fn=mock_build_context,
        render_markdown_handoff_fn=mock_render,
    )

    assert result == 1


def test_action_handoff_drive_returns_not_ok() -> None:
    """Test action_handoff returns 1 when drive reply not ok."""
    args = argparse.Namespace(
        project=Path("/test"),
        dry_run=False,
        submit=False,
        ide=None,
        require_plugin=False,
    )

    mock_client = mock.Mock()
    mock_client.is_running.return_value = True
    mock_client.drive.return_value = {"ok": False, "error": "Plugin not found"}
    mock_client_fn = mock.Mock(return_value=mock_client)
    mock_build_context = mock.Mock(return_value={})
    mock_render = mock.Mock(return_value="# Brief")

    result = action_handoff(
        args,
        client_fn=mock_client_fn,
        build_context_fn=mock_build_context,
        render_markdown_handoff_fn=mock_render,
    )

    assert result == 1


def test_action_handoff_summary_output(capsys) -> None:
    """Test action_handoff prints JSON summary."""
    args = argparse.Namespace(
        project=Path("/test"),
        dry_run=False,
        submit=True,
        ide="vscode",
        require_plugin=False,
    )

    mock_client = mock.Mock()
    mock_client.is_running.return_value = True
    mock_client.drive.return_value = {
        "ok": True,
        "delivered": True,
        "backend": "plugin",
    }
    mock_client_fn = mock.Mock(return_value=mock_client)
    mock_build_context = mock.Mock(return_value={})
    mock_render = mock.Mock(return_value="# Test Brief Content")

    action_handoff(
        args,
        client_fn=mock_client_fn,
        build_context_fn=mock_build_context,
        render_markdown_handoff_fn=mock_render,
    )

    captured = capsys.readouterr()
    # Verify JSON output
    assert captured.out.strip()
    try:
        summary = json.loads(captured.out)
        assert summary["ok"] is True
        assert summary["chars"] == len("# Test Brief Content")
        assert summary["ide"] == "vscode"
        assert summary["submit"] is True
        assert summary["backend"] == "plugin"
    except json.JSONDecodeError:
        pytest.fail("Output should be valid JSON")


def test_action_handoff_context_exception() -> None:
    """Test action_handoff handles context build exceptions."""
    args = argparse.Namespace(
        project=Path("/test"),
        dry_run=False,
        submit=False,
        ide=None,
        require_plugin=False,
    )

    mock_build_context = mock.Mock(side_effect=Exception("Context build failed"))
    mock_render = mock.Mock()

    result = action_handoff(
        args,
        client_fn=mock.Mock(),
        build_context_fn=mock_build_context,
        render_markdown_handoff_fn=mock_render,
    )

    assert result == 1


def test_action_handoff_emits_jsonl_contract(capsys) -> None:
    args = argparse.Namespace(
        project=Path("/test"),
        dry_run=False,
        submit=True,
        ide="cursor",
        require_plugin=False,
        log_format="jsonl",
    )

    mock_client = mock.Mock()
    mock_client.is_running.return_value = True
    mock_client.drive.return_value = {"ok": True, "delivered": True, "backend": "plugin"}

    rc = action_handoff(
        args,
        client_fn=mock.Mock(return_value=mock_client),
        build_context_fn=mock.Mock(return_value={}),
        render_markdown_handoff_fn=mock.Mock(return_value="# Brief"),
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
    """Test that handoff functions are re-exported from cli_command module."""
    from koru.autopilot import cli_command

    assert hasattr(cli_command, "_handoff_action_impl")
    assert hasattr(cli_command, "_action_handoff")
