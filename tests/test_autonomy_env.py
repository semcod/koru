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


def _autoloop_args() -> SimpleNamespace:
    return SimpleNamespace(
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
        operator_pipeline=False,
        operator_tickets=False,
        operator_ticket_queue="default",
        operator_ticket_priority="high",
    )


def test_apply_autoloop_env_to_args_custom_environ() -> None:
    args = _autoloop_args()
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


def test_apply_autoloop_env_to_args_invalid_values_fall_back(
    capsys: pytest.CaptureFixture[str],
) -> None:
    args = _autoloop_args()
    fake_env = {
        **os.environ,
        "TICKET_SOURCES": "bogus",
        "AUTOPILOT_ACTION": "sideways",
        "WUP_MODE": "nope",
        "AUTOPILOT_SKIP_DRIVE_IDLE_STREAK": "not-a-number",
        "SCAN_AFTER_IDLE_MIN_INTERVAL_SECONDS": "-5",
        "AUTOPILOT_SKIP_STATUSES": "   ",
    }
    autonomy_env.apply_autoloop_env_to_args(args, environ=fake_env)
    assert args.ticket_sources == "queue"
    assert args.autopilot_action == "drive"
    assert args.wup_mode == "testql"
    assert args.autopilot_skip_drive_idle_streak == 0
    assert args.scan_after_idle_min_interval == 0.0
    assert args.autopilot_skip_statuses == "waiting_input"
    assert "unknown TICKET_SOURCES" in capsys.readouterr().err


def test_apply_autoloop_env_to_args_operator_fields_are_optional() -> None:
    args = _autoloop_args()
    del args.operator_pipeline, args.operator_tickets
    del args.operator_ticket_queue, args.operator_ticket_priority
    fake_env = {
        **os.environ,
        "KORU_OPERATOR_PIPELINE": "true",
        "OPERATOR_TICKET_QUEUE": "ops",
    }
    autonomy_env.apply_autoloop_env_to_args(args, environ=fake_env)
    assert not hasattr(args, "operator_pipeline")
    assert not hasattr(args, "operator_ticket_queue")


def test_apply_autoloop_env_to_args_blank_env_keeps_cli_values() -> None:
    args = _autoloop_args()
    fake_env = {
        **os.environ,
        "AUTOPILOT_SKIP_STATUSES": "",
        "DIAGNOSTIC_TICKET_QUEUE": "  ",
    }
    autonomy_env.apply_autoloop_env_to_args(args, environ=fake_env)
    assert args.autopilot_skip_statuses == "waiting_input"
    assert args.diagnostic_ticket_queue == "default"
    assert args.wup_watch is None


def test_apply_autoloop_env_to_args_wup_watch_truth_set() -> None:
    args = _autoloop_args()
    autonomy_env.apply_autoloop_env_to_args(args, environ={**os.environ, "WUP_WATCH": "YES"})
    assert args.wup_watch is True
    args = _autoloop_args()
    autonomy_env.apply_autoloop_env_to_args(args, environ={**os.environ, "WUP_WATCH": "0"})
    assert args.wup_watch is False
