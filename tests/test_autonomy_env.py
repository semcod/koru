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
        "TOPOLOGY_INTEGRATION",
        "ENABLE_IDLE_DIAGNOSTICS",
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
        backoff_on_stagnation=True,
        scan_skip_if_clean=False,
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
    fake_env = {**os.environ, "TICKET_SOURCES": "scan", "AUTOPILOT_ACTION": "HANDOFF"}
    autonomy_env.apply_autoloop_env_to_args(args, environ=fake_env)
    assert args.ticket_sources == "scan"
    assert args.autopilot_action == "handoff"
