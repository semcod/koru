"""Regression tests for ticket-456: ensure run.end footer is written on early exit and interruption."""

from __future__ import annotations

import json
from argparse import Namespace
from pathlib import Path
from unittest.mock import patch

import pytest

from koru.queue.local_manager import QueueManagerEarlyExit
from koru.queue_cli_helpers import (
    open_queue_run_log,
    run_queue_loop_mode,
    run_queue_single_mode,
)


def _make_args(tmp_path: Path, *, loop: bool = False, ticket: str | None = None) -> Namespace:
    return Namespace(
        project=tmp_path,
        actor="koru",
        queue_name=None,
        interactive=False,
        dry_run=False,
        no_log=False,
        loop=loop,
        ticket=ticket,
        concurrency=1,
        max_iterations=1,
    )


def _dummy_runners() -> dict:
    nop = lambda *a, **kw: None
    return {
        "planfile_runner": nop,
        "shell_runner": nop,
        "api_runner": nop,
        "llm_runner": nop,
        "prompt_runner": nop,
    }


def _read_events(run_log_path: Path) -> list[dict]:
    return [json.loads(line) for line in run_log_path.read_text(encoding="utf-8").splitlines() if line.strip()]


def test_single_mode_writes_run_end_on_early_exit(tmp_path: Path) -> None:
    args = _make_args(tmp_path, loop=False)
    run_log = open_queue_run_log(args)
    assert run_log is not None

    early = QueueManagerEarlyExit(
        exit_code=0,
        status="duplicate_worker",
        message="another worker is already active",
        details={},
    )
    with (
        patch("koru.queue_cli_helpers.queue_local_manager_session", return_value=None),
        patch("koru.queue_cli_helpers.queue_manager_start", return_value=early),
        patch("koru.queue_cli_helpers.emit_management_event"),
    ):
        rc = run_queue_single_mode(args, run_log, **_dummy_runners())

    assert rc == 0
    events = _read_events(run_log.path)
    assert [e["type"] for e in events] == ["run.start", "run.end"]
    assert events[-1]["last_status"] == "duplicate_worker"
    assert events[-1]["iterations"] == 0


def test_loop_mode_writes_run_end_on_early_exit_and_invalid_args(tmp_path: Path) -> None:
    # 1. --ticket combined with --loop
    bad_args = _make_args(tmp_path, loop=True, ticket="T-1")
    bad_log = open_queue_run_log(bad_args)
    assert bad_log is not None
    rc = run_queue_loop_mode(bad_args, bad_log, **_dummy_runners())
    assert rc == 2
    bad_events = _read_events(bad_log.path)
    assert [e["type"] for e in bad_events] == ["run.start", "run.end"]
    assert bad_events[-1]["last_status"] == "invalid_args"

    # 2. early_exit from queue_manager_start
    args = _make_args(tmp_path, loop=True)
    run_log = open_queue_run_log(args)
    assert run_log is not None
    early = QueueManagerEarlyExit(
        exit_code=0,
        status="paused",
        message="local manager paused queue",
        details={},
    )
    with (
        patch("koru.queue_cli_helpers.queue_local_manager_session", return_value=None),
        patch("koru.queue_cli_helpers.queue_manager_start", return_value=early),
        patch("koru.queue_cli_helpers.emit_management_event"),
    ):
        rc2 = run_queue_loop_mode(args, run_log, **_dummy_runners())

    assert rc2 == 0
    events = _read_events(run_log.path)
    assert [e["type"] for e in events] == ["run.start", "run.end"]
    assert events[-1]["last_status"] == "paused"


def test_single_mode_writes_run_end_on_interruption(tmp_path: Path) -> None:
    args = _make_args(tmp_path, loop=False)
    run_log = open_queue_run_log(args)
    assert run_log is not None

    with (
        patch("koru.queue_cli_helpers.queue_local_manager_session", return_value=None),
        patch("koru.queue_cli_helpers.queue_manager_start", return_value=None),
        patch("koru.queue_cli_helpers.run_next_planfile_task", side_effect=KeyboardInterrupt()),
    ):
        with pytest.raises(KeyboardInterrupt):
            run_queue_single_mode(args, run_log, **_dummy_runners())

    events = _read_events(run_log.path)
    assert [e["type"] for e in events] == ["run.start", "run.end"]
    assert events[-1]["last_status"] == "interrupted"
