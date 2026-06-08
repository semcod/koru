"""Live runtime insights for the local dashboard.

This supplements static/runtime-context data with signals about what is
actually active on the host right now: running IDEs, current tool usage,
and top processes by CPU / memory.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

from koru.autonomous_process_guard import (
    find_existing_autonomous_processes,
    find_existing_wup_processes,
)
from koru.tillm_bridge import shell_agent_process_patterns
from koruide.ide import detect_running_ides

_PS_COLUMNS = ("pid", "pcpu", "pmem", "rss", "etime", "comm", "args")

_CORE_TOOL_PATTERNS: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    ("koru", "Koru", ("koru", "python -m koru.cli", "koru autonomous", "koru auto")),
    ("wup", "WUP", ("wup watch", "koru-wup-testql", "wup")),
    ("planfile", "Planfile", ("planfile",)),
    ("pytest", "Pytest", ("pytest",)),
    ("playwright", "Playwright", ("playwright", "chrome-headless-shell", "chromium")),
    ("docker", "Docker", ("docker compose", "dockerd", "containerd")),
    ("antigravity", "Antigravity", ("antigravity",)),
    ("cursor", "Cursor", ("cursor",)),
    ("windsurf", "Windsurf", ("windsurf",)),
    ("vscodium", "VSCodium", ("codium", "vscodium", "code-oss")),
    ("vscode", "VS Code", ("code", "vscode")),
    ("jetbrains", "JetBrains", ("pycharm", "idea", "jetbrains")),
)


def _tool_patterns() -> tuple[tuple[str, str, tuple[str, ...]], ...]:
    return (*shell_agent_process_patterns(), *_CORE_TOOL_PATTERNS)


def _run_ps() -> list[dict[str, Any]]:
    """Return a normalized process table from ``ps`` (Linux/macOS)."""
    cmd = ["ps", "-eo", "pid=,pcpu=,pmem=,rss=,etime=,comm=,args="]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=False, timeout=5)
    except (OSError, subprocess.SubprocessError):
        return []
    if result.returncode != 0:
        return []

    rows: list[dict[str, Any]] = []
    for raw in (result.stdout or "").splitlines():
        line = raw.strip()
        if not line:
            continue
        parts = line.split(None, 5)
        if len(parts) < 6:
            continue
        pid_s, pcpu_s, pmem_s, rss_s, etime, comm, *rest = parts
        args = rest[0] if rest else comm
        try:
            pid = int(pid_s)
            pcpu = float(pcpu_s)
            pmem = float(pmem_s)
            rss_kb = int(rss_s)
        except ValueError:
            continue
        rows.append(
            {
                "pid": pid,
                "pcpu": pcpu,
                "pmem": pmem,
                "rss_kb": rss_kb,
                "rss_mb": round(rss_kb / 1024.0, 1),
                "etime": etime,
                "comm": comm,
                "args": args,
            }
        )
    return rows


def _looks_project_related(args: str, project: Path) -> bool:
    project_str = str(project.resolve())
    return project_str in args


def _classify_process(proc: dict[str, Any], project: Path) -> str:
    args = str(proc.get("args", "")).lower()
    comm = str(proc.get("comm", "")).lower()
    haystack = f"{comm} {args}"
    for tool_id, _label, patterns in _tool_patterns():
        if any(pattern in haystack for pattern in patterns):
            return tool_id
    if _looks_project_related(args, project):
        return "project"
    return "other"


def _active_tools(
    processes: list[dict[str, Any]], project: Path, *, limit: int = 10
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for proc in processes:
        tool_id = _classify_process(proc, project)
        if tool_id in {"other", "project"}:
            continue
        label = next((label for tid, label, _ in _tool_patterns() if tid == tool_id), tool_id)
        out.append(
            {
                "id": tool_id,
                "label": label,
                "pid": proc["pid"],
                "cpu": proc["pcpu"],
                "rss_mb": proc["rss_mb"],
                "etime": proc["etime"],
                "comm": proc["comm"],
            }
        )
    out.sort(key=lambda row: (-float(row["cpu"]), -float(row["rss_mb"]), int(row["pid"])))
    unique: list[dict[str, Any]] = []
    seen: set[tuple[str, int]] = set()
    for row in out:
        key = (str(row["id"]), int(row["pid"]))
        if key in seen:
            continue
        seen.add(key)
        unique.append(row)
        if len(unique) >= limit:
            break
    return unique


def _top_processes(
    processes: list[dict[str, Any]], project: Path, *, limit: int = 8
) -> list[dict[str, Any]]:
    ranked = sorted(
        processes,
        key=lambda row: (-float(row["pcpu"]), -float(row["rss_mb"]), int(row["pid"])),
    )
    out: list[dict[str, Any]] = []
    for proc in ranked[:limit]:
        out.append(
            {
                "pid": proc["pid"],
                "name": proc["comm"],
                "cpu": proc["pcpu"],
                "mem_pct": proc["pmem"],
                "rss_mb": proc["rss_mb"],
                "etime": proc["etime"],
                "category": _classify_process(proc, project),
                "project_related": _looks_project_related(str(proc.get("args", "")), project),
            }
        )
    return out


def collect_runtime_insights(project: Path) -> dict[str, Any]:
    """Collect live host/process insights for dashboard rendering."""
    processes = _run_ps()
    ides = [ide.to_dict() for ide in detect_running_ides()]
    autonomous = [
        {"pid": proc.pid, "cwd": str(proc.cwd), "command": proc.command}
        for proc in find_existing_autonomous_processes(project)
    ]
    wup = [
        {"pid": proc.pid, "cwd": str(proc.cwd), "command": proc.command}
        for proc in find_existing_wup_processes(project)
    ]
    active_tools = _active_tools(processes, project)
    top = _top_processes(processes, project)
    return {
        "summary": {
            "running_ides": len(ides),
            "active_tools": len(active_tools),
            "top_processes": len(top),
            "autonomous_processes": len(autonomous),
            "wup_processes": len(wup),
        },
        "running_ides": ides,
        "active_tools": active_tools,
        "top_processes": top,
        "project_processes": {
            "autonomous": autonomous,
            "wup": wup,
        },
    }


__all__ = ["collect_runtime_insights"]
