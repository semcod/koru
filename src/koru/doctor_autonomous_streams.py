"""Autonomous service stream probes for ``koru doctor``."""

from __future__ import annotations

import os
from collections.abc import Callable
from pathlib import Path

from koru.doctor_constants import PASS, WARN


def short_command(command: str, *, limit: int = 96) -> str:
    normalized = " ".join(command.split())
    if len(normalized) <= limit:
        return normalized
    return normalized[: limit - 1] + "..."


def autopilot_stream_socket_paths(selected: Path) -> list[Path]:
    runtime = Path(os.environ.get("XDG_RUNTIME_DIR") or "/tmp")
    try:
        candidates = [
            path
            for path in runtime.glob("koru-autopilot*.sock")
            if path.exists()
        ]
    except OSError:
        candidates = []
    if selected.exists() and selected not in candidates:
        candidates.append(selected)
    return sorted(candidates, key=lambda path: str(path))


def autopilot_stream_socket_summary(paths: list[Path]) -> tuple[list[str], int, int]:
    from koru.autonomy.environment import probe_socket_health

    summaries: list[str] = []
    listening = 0
    stale = 0
    for path in paths:
        health = probe_socket_health(path, connect_timeout=0.15)
        if health.listening:
            listening += 1
            state = "listening"
        elif health.stale:
            stale += 1
            state = "stale"
        else:
            state = "present"
        summaries.append(f"{path.name}:{state}")
    return summaries, listening, stale


def process_stream_summary(
    processes: list[object],
    *,
    label: str,
    limit: int = 3,
) -> list[str]:
    rows = []
    for proc in processes[:limit]:
        pid = getattr(proc, "pid", "?")
        command = short_command(str(getattr(proc, "command", "")))
        rows.append(f"{label}[pid={pid} cmd={command!r}]")
    remaining = len(processes) - len(rows)
    if remaining > 0:
        rows.append(f"{label}[+{remaining} more]")
    return rows


def drop_non_service_autonomous_matches(processes: list[object]) -> list[object]:
    filtered = []
    for proc in processes:
        command = str(getattr(proc, "command", ""))
        lowered = command.lower()
        if "pytest" in lowered or " tests/" in lowered:
            continue
        filtered.append(proc)
    return filtered


def autonomous_stream_issue_codes(
    *,
    auto_count: int,
    wup_count: int,
    socket_count: int,
    listening_socket_count: int,
    stale_socket_count: int,
) -> list[str]:
    issues: list[str] = []
    if auto_count > 1:
        issues.append("multiple_autonomous_loops")
    if wup_count > 1:
        issues.append("multiple_wup_watchers")
    if auto_count == 0 and wup_count > 0:
        issues.append("orphan_wup_watcher")
    if listening_socket_count > 1:
        issues.append("multiple_autopilot_socket_listeners")
    if stale_socket_count > 0:
        issues.append("stale_autopilot_socket_stream")
    if socket_count > 1 and listening_socket_count == 0:
        issues.append("multiple_autopilot_socket_files")
    return issues


def check_autonomous_service_stream(
    project: Path,
    *,
    socket_summary: Callable[[], tuple[list[str], int, int]],
) -> tuple[str, str]:
    from koru.autonomous_processes import (
        _find_existing_autonomous_processes,
        _find_existing_wup_processes,
    )

    auto_loops = _find_existing_autonomous_processes(project)
    auto_loops = drop_non_service_autonomous_matches(auto_loops)
    wup_watchers = _find_existing_wup_processes(project)
    socket_summaries, listening_sockets, stale_sockets = socket_summary()
    issues = autonomous_stream_issue_codes(
        auto_count=len(auto_loops),
        wup_count=len(wup_watchers),
        socket_count=len(socket_summaries),
        listening_socket_count=listening_sockets,
        stale_socket_count=stale_sockets,
    )
    detail_bits = [
        f"autonomous_loops={len(auto_loops)}",
        f"wup_watchers={len(wup_watchers)}",
        f"autopilot_sockets={len(socket_summaries)}",
        f"listening_sockets={listening_sockets}",
    ]
    if socket_summaries:
        detail_bits.append(f"sockets={','.join(socket_summaries)}")
    detail_bits.extend(process_stream_summary(auto_loops, label="auto"))
    detail_bits.extend(process_stream_summary(wup_watchers, label="wup"))
    if issues:
        detail_bits.append(f"issues={','.join(issues)}")
        detail_bits.append("recovery=stop duplicate koru auto/WUP services or gc stale sockets")
        return WARN, "; ".join(detail_bits)
    detail_bits.append("stream=single_or_idle")
    return PASS, "; ".join(detail_bits)
