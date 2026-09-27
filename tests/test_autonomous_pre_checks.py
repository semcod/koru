"""Tests for autonomous pre-checks and NoLimits storage check integration."""

from __future__ import annotations

import argparse
from pathlib import Path
from unittest.mock import MagicMock, patch

from koru.autonomous import _run_autonomous_pre_checks, check_storage_limits


def test_check_storage_limits_ok(tmp_path: Path):
    usage_mock = MagicMock()
    usage_mock.free = 50 * (1024**3)
    usage_mock.total = 100 * (1024**3)

    messages: list[str] = []
    with patch("shutil.disk_usage", return_value=usage_mock):
        result = check_storage_limits(tmp_path, stdio_info=messages.append)

    assert result["status"] == "ok"
    assert result["limit_id"] == "LIM-STORAGE-001"
    assert result["free_gb"] == 50.0
    assert result["remediation"] is None
    assert len(messages) == 0


def test_check_storage_limits_low_storage_warning(tmp_path: Path):
    usage_mock = MagicMock()
    usage_mock.free = 2 * (1024**3)
    usage_mock.total = 100 * (1024**3)

    messages: list[str] = []
    with patch("shutil.disk_usage", return_value=usage_mock):
        result = check_storage_limits(tmp_path, stdio_info=messages.append)

    assert result["status"] == "warning"
    assert result["limit_id"] == "LIM-STORAGE-001"
    assert result["free_gb"] == 2.0
    assert "fixos cleanup" in result["remediation"]
    assert len(messages) == 1
    assert "LIM-STORAGE-001" in messages[0]
    assert "fixos" in messages[0]


def test_check_storage_limits_handles_exception(tmp_path: Path):
    with patch("shutil.disk_usage", side_effect=OSError("Disk failure")):
        result = check_storage_limits(tmp_path)

    assert result["status"] == "error"
    assert result["limit_id"] == "LIM-STORAGE-001"
    assert "Disk failure" in result["error"]


def test_run_autonomous_pre_checks_integrates_storage_check(tmp_path: Path):
    args = argparse.Namespace(emit_events=None)
    with (
        patch("koru.autonomous.check_storage_limits") as mock_storage,
        patch("koru.autonomous._run_mcp_provision", return_value=True),
        patch("koru.autonomous._setup_autopilot_plugin", return_value=True),
        patch("koru.autonomous._run_operator_pipeline"),
        patch("koru.autonomous._unblock_queue_if_needed"),
    ):
        mcp_ran, plugin_conn = _run_autonomous_pre_checks(
            args=args,
            project=tmp_path,
            startup_probe=MagicMock(),
            socket_path=tmp_path / "sock",
            autopilot_ide="vscode",
            client=MagicMock(),
            correlation_id="corr-123",
        )

    assert mcp_ran is True
    assert plugin_conn is True
    mock_storage.assert_called_once()
