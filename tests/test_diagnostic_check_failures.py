"""Diagnostic failures must reach durable intake without stopping other checks."""

import math
import subprocess
import sys

import pytest
from planfile import Planfile

from koru.autonomy.operator import operator_diagnostics as diagnostics


def _run_loop(project, command, messages):
    state = project / "diagnostic-markers"

    def run(project, check_id, command, **kwargs):
        return diagnostics.run_command_check(
            project=project,
            check_id=check_id,
            command=command,
            stdio_info=lambda message, **kw: messages.append(message),
            **kwargs,
        )

    return diagnostics.run_idle_check_loop(
        checks=[
            ("broken", "controlled failure", command),
            (
                "healthy",
                "following healthy check",
                [
                    sys.executable,
                    "-c",
                    'from pathlib import Path;Path("healthy.ran").touch()',
                ],
            ),
        ],
        stdio_info=lambda message, **kw: messages.append(message),
        is_topology_enabled=lambda *a, **kw: True,
        run_command=run,
        clear_marker=diagnostics.clear_diagnostic_marker,
        create_ticket=lambda **kw: diagnostics.create_diagnostic_ticket(
            stdio_info=lambda message, **unused: messages.append(message),
            **kw,
        ),
        make_result=lambda status, failed: {"status": status, "failed": failed},
        stdio_format="human",
        project=project,
        cycle=1,
        queue_status="idle",
        diagnostic_tickets=True,
        diagnostic_ticket_queue="fixture",
        diagnostic_ticket_priority="high",
        diagnostic_state_dir=state,
        topology_integration=False,
    )


@pytest.mark.parametrize("failure", ["missing", "permission", "timeout"])
def test_failed_check_is_ticketed_and_next_check_runs(tmp_path, monkeypatch, failure):
    monkeypatch.setattr("koru.activity_log.activity", lambda *a, **kw: None)
    monkeypatch.setenv("KORU_PLANFILE_SYNC", "off")
    monkeypatch.setattr(diagnostics, "IDLE_CHECK_TIMEOUT_SECONDS", 0.5, raising=False)
    pf = Planfile(str(tmp_path))
    command = [str(tmp_path / "missing-executable")]
    if failure == "permission":
        script = tmp_path / "non-executable"
        script.write_text("#!/bin/sh\nexit 0\n")
        script.chmod(0o600)
        command = [str(script)]
    elif failure == "timeout":
        command = [sys.executable, "-c", "import time;time.sleep(2)"]
    messages = []
    for _ in range(2):
        assert _run_loop(tmp_path, command, messages) == {
            "status": "failed",
            "failed": ["broken"],
        }
        assert (tmp_path / "healthy.ran").is_file()
    tickets = pf.list_tickets(sprint="all")
    assert len(tickets) == 1
    assert tickets[0].status.value == "open"
    assert (tmp_path / "diagnostic-markers/broken.failed").read_text() == tickets[0].id


@pytest.mark.parametrize("exit_code, expected", [(0, True), (3, False)])
def test_success_and_nonzero_checks_use_finite_runtime_budget(tmp_path, monkeypatch, exit_code, expected):
    actual = subprocess.run
    observed = []

    def observe(*args, **kwargs):
        observed.append(kwargs.get("timeout"))
        return actual(*args, **kwargs)

    monkeypatch.setattr(diagnostics.subprocess, "run", observe)
    result = diagnostics.run_command_check(
        stdio_info=lambda *a, **kw: None,
        project=tmp_path,
        check_id="controlled",
        command=[sys.executable, "-c", f"raise SystemExit({exit_code})"],
    )
    assert result is expected
    assert len(observed) == 1 and observed[0] is not None
    assert math.isfinite(observed[0]) and 0 < observed[0] <= 600


@pytest.mark.parametrize(
    "exception",
    [
        OSError("fixture-sensitive-provider-detail"),
        subprocess.TimeoutExpired("fixture-sensitive-provider-detail", 0.5),
    ],
)
def test_launch_and_timeout_diagnostics_do_not_print_exception_details(tmp_path, monkeypatch, exception):
    def fail(*args, **kwargs):
        raise exception

    monkeypatch.setattr(diagnostics.subprocess, "run", fail)
    messages = []
    assert (
        diagnostics.run_command_check(
            stdio_info=lambda message, **kw: messages.append(message),
            project=tmp_path,
            check_id="controlled",
            command=["fixture-check"],
        )
        is False
    )
    assert "fixture-sensitive-provider-detail" not in "\n".join(messages)
    assert any(type(exception).__name__ in message for message in messages)
