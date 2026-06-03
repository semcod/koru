"""Start/stop autopilot daemons for registered lanes."""

from __future__ import annotations

import os
import subprocess
from typing import Callable, Sequence

from coru.supervisor.models import LaneRecord


def _lane_environ(record: LaneRecord) -> dict[str, str]:
    env = dict(os.environ)
    env["KORU_AUTOPILOT_IDE"] = record.ide
    env["KORU_AUTOPILOT_INSTANCE"] = record.instance
    env["KORU_AUTOPILOT_SOCKET"] = record.socket_path
    if record.editor_cli:
        env["CORU_EDITOR_CLI"] = record.editor_cli
    return env


def start_daemon(
    record: LaneRecord,
    *,
    koru_argv: Sequence[str] | None = None,
    run: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
    timeout: float = 15.0,
) -> tuple[bool, str]:
    argv = list(koru_argv or ("koru",))
    cmd = [*argv, "autopilot", "daemon", "--idempotent", "--no-handoff"]
    if record.project:
        cmd.extend(["--project", record.project])
    try:
        proc = run(
            cmd,
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout,
            env=_lane_environ(record),
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return False, str(exc)
    if proc.returncode == 0:
        return True, (proc.stdout or proc.stderr or "daemon started").strip()[:240]
    detail = (proc.stderr or proc.stdout or f"rc={proc.returncode}").strip()
    return False, detail[:240]


def stop_daemon(
    record: LaneRecord,
    *,
    koru_argv: Sequence[str] | None = None,
    run: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
    timeout: float = 15.0,
) -> tuple[bool, str]:
    argv = list(koru_argv or ("koru",))
    cmd = [*argv, "autopilot", "shutdown"]
    try:
        proc = run(
            cmd,
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout,
            env=_lane_environ(record),
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return False, str(exc)
    if proc.returncode == 0:
        return True, (proc.stdout or proc.stderr or "daemon stopped").strip()[:240]
    detail = (proc.stderr or proc.stdout or f"rc={proc.returncode}").strip()
    return False, detail[:240]
