"""Tests for :mod:`koru.autonomy.env` (autoloop / autonomous env parity)."""

from __future__ import annotations

import os
from types import SimpleNamespace

import pytest

from koru.autonomy import env as autonomy_env


def test_auto_loop_env_defaults_cover_core_autoloop_flags() -> None:
    d = autonomy_env.AUTOLOOP_ENV_DEFAULTS
    for key in (
        "ENABLE_SCAN",
        "TICKET_SOURCES",
        "ENABLE_AUTOPILOT_DRIVE",
        "AUTOPILOT_ENSURE_DAEMON",
        "TOPOLOGY_INTEGRATION",
        "AUTOPILOT_SKIP_DRIVE_IDLE_STREAK",
        "SCAN_AFTER_IDLE_QUEUE",
        "SCAN_AFTER_IDLE_MIN_INTERVAL_SECONDS",
        "ENABLE_IDLE_DIAGNOSTICS",
        "REGIX_DIAGNOSTIC_CMD",
        "REDUP_DIAGNOSTIC_CMD",
        "TESTQL_DIAGNOSTIC_CMD",
    ):
        assert key in d


def test_env_truthy_matrix(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("KORU_TEST_TRUTHY", "YES")
    assert autonomy_env.env_truthy("KORU_TEST_TRUTHY", False) is True
    monkeypatch.setenv("KORU_TEST_TRUTHY", "0")
    assert autonomy_env.env_truthy("KORU_TEST_TRUTHY", True) is False
    monkeypatch.delenv("KORU_TEST_TRUTHY", raising=False)
    assert autonomy_env.env_truthy("KORU_TEST_TRUTHY", True) is True


def test_apply_autoloop_env_to_args_custom_environ() -> None:
    args = SimpleNamespace(
        ticket_sources="queue",
        idle_diagnostics="off",
        diagnostic_tickets=False,
        diagnostic_ticket_queue="default",
        diagnostic_ticket_priority="high",
        diagnostic_state_dir=".planfile/.koru/autoloop-diag",
        strict_diagnostics=False,
        autopilot_action="drive",
        autopilot_on_idle_only=False,
        autopilot_skip_on_diagnostics_fail=True,
        autopilot_skip_statuses="waiting_input",
        autopilot_skip_drive_idle_streak=0,
        backoff_on_stagnation=True,
        scan_skip_if_clean=False,
        scan_after_idle_queue=False,
        scan_after_idle_min_interval=0.0,
        topology_integration=True,
        wup_watch=None,
        wup_mode="testql",
        wup_deps="deps.json",
        wup_scenarios_dir="testql-scenarios",
        wup_testql_bin="testql",
        wup_track_dir=".wup/tracks",
        wup_diagnostic_tickets=True,
        wup_ticket_queue="default",
    )
    fake_env = {
        **os.environ,
        "TICKET_SOURCES": "scan",
        "AUTOPILOT_ACTION": "HANDOFF",
        "AUTOPILOT_SKIP_DRIVE_IDLE_STREAK": "2",
        "SCAN_AFTER_IDLE_QUEUE": "true",
        "SCAN_AFTER_IDLE_MIN_INTERVAL_SECONDS": "90",
    }
    autonomy_env.apply_autoloop_env_to_args(args, environ=fake_env)
    assert args.ticket_sources == "scan"
    assert args.autopilot_action == "handoff"
    assert args.autopilot_skip_drive_idle_streak == 2
    assert args.scan_after_idle_queue is True
    assert args.scan_after_idle_min_interval == 90.0
