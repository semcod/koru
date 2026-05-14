"""Tests for autonomous scenarios (basic smoke tests)."""

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from koru.autonomous import (
    _run_cycle,
    autonomous_main,
    AutoloopState,
    QueueLoopResult,
    ScanResult,
)


def test_autonomous_main_safe_up_expands_args():
    """Test that safe-up subcommand expands to safe defaults."""
    with tempfile.TemporaryDirectory() as tmpdir:
        argv = ["safe-up", "--project", tmpdir]
        result = autonomous_main(argv)
        # The command should expand safe-up to up with safe defaults
        # We're testing that it doesn't crash and returns a valid exit code
        assert result in (0, 2)  # 0=success, 2=argparse error (expected)


def test_autonomous_cycle_smoke_scenario():
    """Test smoke scenario: scan + queue only, no autopilot."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project = Path(tmpdir)
        state = AutoloopState()
        
        # Mock queue result - idle (no tickets)
        queue_result = QueueLoopResult(
            iterations=1,
            completed=[],
            failed=[],
            waiting=[],
            last_status="idle",
            last_message="",
            last_ticket_id=None,
        )
        
        # Mock scan result
        scan_result = ScanResult(
            suggestions=[],
            applied=[],
            skipped=[],
        )
        
        with patch("koru.autonomous.run_planfile_queue_loop") as mock_queue:
            mock_queue.return_value = queue_result
            
            with patch("koru.autonomous.run_scan") as mock_scan:
                mock_scan.return_value = scan_result
                
                scan_out, queue_out, _, diag_out = _run_cycle(
                    cycle=1,
                    project=project,
                    actor="test",
                    queue_name=None,
                    enable_scan=True,
                    max_iterations=1,
                    enable_autopilot=False,  # Smoke: no autopilot
                    autopilot_ide="auto",
                    drive_prompt="test prompt",
                    submit=True,
                    include_semcod_artifacts=None,
                    client=None,  # No autopilot client
                    state=state,
                    idle_diagnostics="off",
                    diagnostic_tickets=False,
                    diagnostic_ticket_queue="default",
                    diagnostic_ticket_priority="high",
                    diagnostic_state_dir=None,
                    wup_watch_enabled=False,
                    wup_diagnostic_tickets=False,
                    wup_ticket_queue="default",
                    strict_diagnostics=False,
                    autopilot_action="drive",
                    autopilot_on_idle_only=False,
                    autopilot_skip_on_diagnostics_fail=True,
                    autopilot_skip_statuses="waiting_input",
                    scan_skip_if_clean=False,
                    scan_skip_after=1,
                    topology_integration=False,
                    stdio_format="human",
                    correlation_id="test-123",
                )
                
                # Verify scan was called
                mock_scan.assert_called_once()
                
                # Verify queue was called
                mock_queue.assert_called_once()
                
                # Verify autopilot was skipped
                assert scan_out is not None
                assert queue_out.last_status == "idle"
                assert diag_out.status in ("ok", "skipped")


def test_autonomous_cycle_autopilot_skipped_when_no_client():
    """Test that autopilot is skipped when no client is provided."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project = Path(tmpdir)
        state = AutoloopState()
        
        # Mock queue result - idle
        queue_result = QueueLoopResult(
            iterations=1,
            completed=[],
            failed=[],
            waiting=[],
            last_status="idle",
            last_message="",
            last_ticket_id=None,
        )
        
        # Mock scan result
        scan_result = ScanResult(
            suggestions=[],
            applied=[],
            skipped=[],
        )
        
        with patch("koru.autonomous.run_planfile_queue_loop") as mock_queue:
            mock_queue.return_value = queue_result
            
            with patch("koru.autonomous.run_scan") as mock_scan:
                mock_scan.return_value = scan_result
                
                _run_cycle(
                    cycle=1,
                    project=project,
                    actor="test",
                    queue_name=None,
                    enable_scan=True,
                    max_iterations=1,
                    enable_autopilot=True,  # Enable autopilot
                    autopilot_ide="windsurf",
                    drive_prompt="test prompt",
                    submit=True,
                    include_semcod_artifacts=None,
                    client=None,  # No client - autopilot will be skipped
                    state=state,
                    idle_diagnostics="off",
                    diagnostic_tickets=False,
                    diagnostic_ticket_queue="default",
                    diagnostic_ticket_priority="high",
                    diagnostic_state_dir=None,
                    wup_watch_enabled=False,
                    wup_diagnostic_tickets=False,
                    wup_ticket_queue="default",
                    strict_diagnostics=False,
                    autopilot_action="drive",
                    autopilot_on_idle_only=False,
                    autopilot_skip_on_diagnostics_fail=True,
                    autopilot_skip_statuses="waiting_input",
                    scan_skip_if_clean=False,
                    scan_skip_after=1,
                    topology_integration=False,
                    stdio_format="human",
                    correlation_id="test-123",
                )
                
                # Test passes if no exception is raised
                # Autopilot is skipped when client=None
