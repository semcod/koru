"""Unit tests for koru.autopilot.commands.manage module (R5b)."""
from __future__ import annotations

import argparse
import json
from unittest import mock

import pytest

from koru.autopilot.commands.manage import action_manage


def test_action_manage_collect_report() -> None:
    """Test action_manage collects and displays report."""
    args = argparse.Namespace(
        ide="cursor",
        socket="/tmp/test.sock",
        fix=False,
        dry_run=False,
        output_format="text",
    )

    mock_report = mock.Mock()
    mock_report.ok = True
    mock_report.to_dict.return_value = {"ok": True, "issues": []}

    mock_collect = mock.Mock(return_value=mock_report)
    mock_format = mock.Mock(return_value="Report: OK")
    mock_repair = mock.Mock()

    result = action_manage(
        args,
        collect_report_fn=mock_collect,
        format_report_fn=mock_format,
        repair_fn=mock_repair,
    )

    assert result == 0
    mock_collect.assert_called_once_with(ide="cursor", socket_path="/tmp/test.sock")
    mock_format.assert_called_once_with(mock_report)
    mock_repair.assert_not_called()


def test_action_manage_repair_mode() -> None:
    """Test action_manage in repair mode (--fix)."""
    args = argparse.Namespace(
        ide="vscode",
        socket="/tmp/test.sock",
        fix=True,
        dry_run=True,
        output_format="text",
    )

    mock_report = mock.Mock()
    mock_report.ok = True
    mock_report.to_dict.return_value = {"ok": True, "fixed": []}

    mock_collect = mock.Mock()
    mock_format = mock.Mock(return_value="Repair: OK")
    mock_repair = mock.Mock(return_value=mock_report)

    result = action_manage(
        args,
        collect_report_fn=mock_collect,
        format_report_fn=mock_format,
        repair_fn=mock_repair,
    )

    assert result == 0
    mock_repair.assert_called_once_with(
        ide="vscode", socket_path="/tmp/test.sock", dry_run=True
    )
    mock_collect.assert_not_called()


def test_action_manage_json_output(capsys) -> None:
    """Test action_manage outputs JSON when requested."""
    args = argparse.Namespace(
        ide="auto",
        socket=None,
        fix=False,
        dry_run=False,
        output_format="json",
    )

    mock_report = mock.Mock()
    mock_report.ok = True
    mock_report.to_dict.return_value = {"ok": True, "ide": "cursor"}

    mock_collect = mock.Mock(return_value=mock_report)
    mock_format = mock.Mock()
    mock_repair = mock.Mock()

    result = action_manage(
        args,
        collect_report_fn=mock_collect,
        format_report_fn=mock_format,
        repair_fn=mock_repair,
    )

    assert result == 0
    captured = capsys.readouterr()
    assert json.loads(captured.out) == {"ok": True, "ide": "cursor"}
    mock_format.assert_not_called()


def test_action_manage_failure_returns_1() -> None:
    """Test action_manage returns 1 when report has ok=False."""
    args = argparse.Namespace(
        ide="cursor",
        socket=None,
        fix=False,
        dry_run=False,
        output_format="text",
    )

    mock_report = mock.Mock()
    mock_report.ok = False
    mock_report.to_dict.return_value = {"ok": False, "issues": ["error"]}

    mock_collect = mock.Mock(return_value=mock_report)
    mock_format = mock.Mock(return_value="Report: FAIL")
    mock_repair = mock.Mock()

    result = action_manage(
        args,
        collect_report_fn=mock_collect,
        format_report_fn=mock_format,
        repair_fn=mock_repair,
    )

    assert result == 1


# ---------------------------------------------------------------------------
# Backward compatibility tests
# ---------------------------------------------------------------------------

def test_backward_compat_reexports_from_cli_command() -> None:
    """Test that manage functions are re-exported from cli_command module."""
    from koru.autopilot import cli_command

    assert hasattr(cli_command, "_manage_action_impl")
    assert hasattr(cli_command, "_action_manage")
