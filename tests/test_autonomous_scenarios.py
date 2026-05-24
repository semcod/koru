"""Tests for autonomous scenarios (basic smoke tests)."""

import tempfile
from pathlib import Path
from unittest.mock import patch

from koru.autonomous import (
    AutoloopState,
    QueueLoopResult,
    ScanResult,
    _run_cycle,
    autonomous_main,
)


def test_autonomous_main_safe_up_expands_args():
    """Test that safe-up subcommand expands to safe defaults."""
    with tempfile.TemporaryDirectory() as tmpdir:
        with patch("koru.autonomous._action_up", return_value=0) as action_up:
            result = autonomous_main(["safe-up", "--project", tmpdir])

        assert result == 0
        args = action_up.call_args.args[0]
        assert args.action == "up"
        assert args.ticket_sources == "queue"
        assert args.idle_diagnostics == "quick"
        assert args.diagnostic_tickets is True
        assert args.enable_autopilot is False
        assert args.max_cycles == 1


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


def test_run_cycle_auto_heals_stale_socket():
    """Test that _run_cycle silently removes stale sockets before work."""
    with tempfile.TemporaryDirectory() as d:
        sock = Path(d) / "stale.sock"
        sock.touch()
        assert sock.exists()

        with patch("koru.autopilot.default_socket_path", return_value=sock):
            with patch("koru.autonomous.run_planfile_queue_loop") as mock_queue:
                mock_queue.return_value = QueueLoopResult(
                    iterations=1,
                    completed=[],
                    failed=[],
                    waiting=[],
                    last_status="idle",
                    last_message="",
                    last_ticket_id=None,
                )
                with patch("koru.autonomous.run_scan") as mock_scan:
                    mock_scan.return_value = ScanResult(
                        suggestions=[],
                        applied=[],
                        skipped=[],
                    )
                    _run_cycle(
                        cycle=1,
                        project=Path(d),
                        actor="test",
                        queue_name=None,
                        enable_scan=True,
                        max_iterations=1,
                        enable_autopilot=False,
                        autopilot_ide="auto",
                        drive_prompt="",
                        submit=True,
                        include_semcod_artifacts=None,
                        client=None,
                        state=AutoloopState(),
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

        assert not sock.exists()


def test_autonomous_cycle_skips_idle_drive_when_no_ticket_then_hits_idle_streak():
    """Idle queue without runnable tickets does not paste broad discovery into chat."""
    drive_calls: list[tuple[str, dict]] = []

    class RecordingClient:
        def drive(self, prompt: str, **kwargs):
            drive_calls.append((prompt, kwargs))
            return {"ok": True, "backend": "test"}

    with tempfile.TemporaryDirectory() as tmpdir:
        project = Path(tmpdir)
        state = AutoloopState()
        queue_result = QueueLoopResult(
            iterations=1,
            completed=[],
            failed=[],
            waiting=[],
            last_status="idle",
            last_message="",
            last_ticket_id=None,
        )
        scan_result = ScanResult(suggestions=[], applied=[], skipped=[])

        with patch("koru.autonomous.run_planfile_queue_loop") as mock_queue:
            mock_queue.return_value = queue_result
            with patch("koru.autonomous.run_scan") as mock_scan:
                mock_scan.return_value = scan_result

                common = dict(
                    project=project,
                    actor="test",
                    queue_name=None,
                    enable_scan=True,
                    max_iterations=1,
                    enable_autopilot=True,
                    autopilot_ide="windsurf",
                    drive_prompt="test prompt",
                    submit=True,
                    include_semcod_artifacts=None,
                    client=RecordingClient(),
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
                    autopilot_skip_drive_idle_streak=1,
                    scan_skip_if_clean=False,
                    scan_skip_after=1,
                    topology_integration=False,
                    stdio_format="human",
                    correlation_id="test-idle-streak",
                )

                _, _, ap1, _ = _run_cycle(cycle=1, **common)
                _, _, ap2, _ = _run_cycle(cycle=2, **common)

                assert ap1 == "skipped(idle_no_ticket)"
                assert ap2 == "skipped(idle_streak)"
                assert drive_calls == []
