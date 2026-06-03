"""Probe autopilot daemon/plugin health via koru subprocess."""

from __future__ import annotations

import json
import os
import subprocess
from datetime import UTC, datetime
from typing import Callable, Sequence

from coru.supervisor.models import LaneHealth, LaneRecord


def _iso_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _lane_environ(record: LaneRecord) -> dict[str, str]:
    env = dict(os.environ)
    env["KORU_AUTOPILOT_IDE"] = record.ide
    env["KORU_AUTOPILOT_INSTANCE"] = record.instance
    env["KORU_AUTOPILOT_SOCKET"] = record.socket_path
    if record.editor_cli:
        env["CORU_EDITOR_CLI"] = record.editor_cli
    return env


def _status_command(record: LaneRecord, koru_argv: Sequence[str] | None) -> list[str]:
    argv = list(koru_argv or ("koru",))
    return [*argv, "autopilot", "status", "--ide", record.ide]


def _run_status_probe(
    record: LaneRecord,
    *,
    koru_argv: Sequence[str] | None,
    run: Callable[..., subprocess.CompletedProcess[str]],
    timeout: float,
) -> subprocess.CompletedProcess[str] | LaneHealth:
    cmd = _status_command(record, koru_argv)
    try:
        return run(
            cmd,
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout,
            env=_lane_environ(record),
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return LaneHealth(
            daemon_running=False,
            plugin_connected=False,
            issues=[str(exc)],
            checked_at=_iso_now(),
        )


def _failure_health(proc: subprocess.CompletedProcess[str]) -> LaneHealth:
    detail = (proc.stderr or proc.stdout or "").strip().splitlines()
    issue = detail[-1] if detail else f"status rc={proc.returncode}"
    return LaneHealth(
        daemon_running=False,
        plugin_connected=False,
        issues=[issue[:240]],
        checked_at=_iso_now(),
    )


def _select_plugin(info: dict[str, object], ide: str) -> tuple[list[dict[str, object]], dict[str, object] | None, bool]:
    plugins = info.get("plugins") if isinstance(info.get("plugins"), list) else []
    plugin_rows = [row for row in plugins if isinstance(row, dict)]
    matching = [row for row in plugin_rows if str(row.get("ide") or "") == ide]
    chosen = matching[0] if matching else (plugin_rows[0] if plugin_rows else None)
    return plugin_rows, chosen, bool(matching or plugin_rows)


def _success_health(info: dict[str, object], record: LaneRecord) -> LaneHealth:
    plugin_rows, chosen, plugin_connected = _select_plugin(info, record.ide)
    daemon = info.get("daemon") if isinstance(info.get("daemon"), dict) else {}
    issues: list[str] = []
    if not plugin_connected:
        issues.append("no connected plugin")

    return LaneHealth(
        daemon_running=True,
        plugin_connected=plugin_connected,
        plugin_count=len(plugin_rows),
        daemon_version=str(daemon.get("version") or info.get("daemon_version") or "") or None,
        plugin_version=str(chosen.get("version") or "") if chosen else None,
        plugin_build=str(chosen.get("build") or chosen.get("git_sha") or "") if chosen else None,
        expected_build=str(info.get("expected_plugin_build") or "") or None,
        issues=issues,
        checked_at=_iso_now(),
    )


def probe_lane_health(
    record: LaneRecord,
    *,
    koru_argv: Sequence[str] | None = None,
    run: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
    timeout: float = 8.0,
) -> LaneHealth:
    status_result = _run_status_probe(
        record,
        koru_argv=koru_argv,
        run=run,
        timeout=timeout,
    )
    if isinstance(status_result, LaneHealth):
        return status_result
    proc = status_result

    if proc.returncode != 0:
        return _failure_health(proc)

    try:
        info = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return LaneHealth(
            daemon_running=True,
            plugin_connected=False,
            issues=["status stdout was not JSON"],
            checked_at=_iso_now(),
        )

    if not isinstance(info, dict):
        return LaneHealth(
            daemon_running=True,
            plugin_connected=False,
            issues=["status stdout JSON root was not an object"],
            checked_at=_iso_now(),
        )

    return _success_health(info, record)
