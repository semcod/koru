from __future__ import annotations

import signal
from pathlib import Path

from koru.autonomy.operator.operator_processes import (
    ExistingManagedProcess,
    _terminate_existing_processes,
)


def _proc(pid: int = 424242) -> ExistingManagedProcess:
    return ExistingManagedProcess(
        pid=pid,
        kind="autonomous",
        command="koru autonomous up --project /tmp/x",
        cwd=Path("/tmp/x"),
    )


def test_terminate_tolerates_sigterm_permission_error(monkeypatch) -> None:
    calls: list[tuple[int, int]] = []

    def fake_kill(pid: int, sig: int) -> None:
        calls.append((pid, sig))
        raise PermissionError(1, "Operation not permitted")

    monkeypatch.setattr("os.kill", fake_kill)

    _terminate_existing_processes([_proc()], stdio_format="nl")

    assert calls == [(424242, signal.SIGTERM)]


def test_terminate_tolerates_probe_permission_error(monkeypatch) -> None:
    calls: list[tuple[int, int]] = []
    ticks = iter([0.0, 0.1] + [100.0] * 64)

    def fake_kill(pid: int, sig: int) -> None:
        calls.append((pid, sig))
        if sig == 0:
            raise PermissionError(1, "Operation not permitted")
        if sig == signal.SIGKILL:
            raise PermissionError(1, "Operation not permitted")

    monkeypatch.setattr("os.kill", fake_kill)
    monkeypatch.setattr("time.monotonic", lambda: next(ticks))

    _terminate_existing_processes([_proc()], stdio_format="nl")

    assert (424242, signal.SIGTERM) in calls
    assert (424242, 0) in calls
    assert (424242, signal.SIGKILL) in calls


def test_terminate_returns_once_process_is_gone(monkeypatch) -> None:
    calls: list[tuple[int, int]] = []

    def fake_kill(pid: int, sig: int) -> None:
        calls.append((pid, sig))
        if sig == 0:
            raise ProcessLookupError

    monkeypatch.setattr("os.kill", fake_kill)

    _terminate_existing_processes([_proc()], stdio_format="nl")

    assert calls == [(424242, signal.SIGTERM), (424242, 0)]
    assert not any(sig == signal.SIGKILL for _, sig in calls)


def test_terminate_missing_pid_is_skipped(monkeypatch) -> None:
    def fake_kill(pid: int, sig: int) -> None:
        raise ProcessLookupError

    monkeypatch.setattr("os.kill", fake_kill)

    _terminate_existing_processes([_proc()], stdio_format="nl")
