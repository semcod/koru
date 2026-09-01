"""Shared quality-gate runner used by MCP and ``koru ci``."""

from __future__ import annotations

import subprocess
import threading
import time
from pathlib import Path
from typing import Any

from koru.quality_gate_commands import sumr_scan_command, vallm_batch_command
from koru.redup_integration import redup_check_command

try:
    import psutil

    _PSUTIL_AVAILABLE = True
except ImportError:
    _PSUTIL_AVAILABLE = False

DEFAULT_GATES = ("regix", "redup")
GATE_TIMEOUT_SECONDS = 120
TESTQL_PATTERN = "*.testql.toon.yaml"


def has_testql_scenarios(project: Path, pattern: str = TESTQL_PATTERN) -> bool:
    """Return True when the project tree contains at least one TestQL scenario file."""
    try:
        return any(project.rglob(pattern))
    except OSError:
        return False


def gate_commands(project: Path) -> dict[str, list[str]]:
    return {
        "regix": ["regix", "gates", "--workdir", str(project)],
        "redup": redup_check_command(project),
        "vallm": vallm_batch_command(project),
        "sumr": sumr_scan_command(project),
        "testql": [
            "testql",
            "suite",
            "--path",
            str(project),
            "--pattern",
            "*.testql.toon.yaml",
            "--output",
            "console",
        ],
        "security": ["bandit", "-r", str(project), "-f", "json"],
    }


def _detect_enabled_gates(project: Path, known_gates: list[str]) -> list[str]:
    try:
        from koru.topology import load_topology

        topo = load_topology(project)
        detected: list[str] = []
        for gate_name in known_gates:
            comp = topo.get("components", {}).get(gate_name, {})
            if comp.get("enabled", False) and comp.get("available", False):
                detected.append(gate_name)
        return detected
    except Exception:
        return []


def resolve_gates(
    project: Path,
    requested: list[str] | None,
    commands: dict[str, list[str]],
) -> list[str]:
    if requested:
        return requested
    detected = _detect_enabled_gates(project, list(commands.keys()))
    if detected:
        return detected
    return list(DEFAULT_GATES)


def _monitor_subprocess_oom(
    proc: subprocess.Popen[str],
    threshold_mb: int,
    interval_seconds: float | int,
    action: str,
) -> tuple[bool, list[str]]:
    logs: list[str] = []
    killed = False
    while proc.poll() is None:
        try:
            rss_mb = psutil.Process(proc.pid).memory_info().rss / (1024 * 1024)
        except (psutil.Error, ProcessLookupError):
            break
        if rss_mb > threshold_mb:
            logs.append(f"OOM monitor: RSS {rss_mb:.0f}MB > {threshold_mb}MB")
            if action == "kill":
                proc.kill()
                killed = True
            break
        time.sleep(interval_seconds)
    return killed, logs


def _launch_oom_monitor(
    proc: subprocess.Popen[str],
    threshold_mb: int,
    interval_seconds: float | int,
    action: str,
) -> list[Any]:
    state: list[Any] = [False, []]
    if threshold_mb > 0 and _PSUTIL_AVAILABLE:

        def _monitor() -> None:
            state[0], state[1] = _monitor_subprocess_oom(
                proc,
                threshold_mb,
                interval_seconds,
                action,
            )

        threading.Thread(target=_monitor, daemon=True).start()
    return state


def run_single_gate(
    project: Path,
    gate_name: str,
    cmd: list[str],
    *,
    oom_threshold_mb: int = 2048,
    oom_interval_seconds: int = 5,
    oom_action: str = "kill",
    timeout_seconds: int = GATE_TIMEOUT_SECONDS,
) -> tuple[str, dict[str, Any]]:
    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=str(project),
        )
        oom_state = _launch_oom_monitor(proc, oom_threshold_mb, oom_interval_seconds, oom_action)
        try:
            stdout, stderr = proc.communicate(timeout=timeout_seconds)
        except subprocess.TimeoutExpired:
            proc.kill()
            stdout, stderr = proc.communicate()
            return "timeout", {
                "gate": gate_name,
                "status": "timeout",
                "issues": [f"timed out after {timeout_seconds}s"],
            }

        if oom_state[0]:
            issues = list(oom_state[1])
            issues.extend((stdout or "").strip().split("\n")[-5:])
            issues.extend((stderr or "").strip().split("\n")[-5:])
            return "killed", {"gate": gate_name, "status": "killed", "issues": issues}

        if proc.returncode == 0:
            return "passed", {"gate": gate_name, "status": "passed", "issues": []}
        issues = ((stdout or "").strip().split("\n") + (stderr or "").strip().split("\n"))[-10:]
        return "failed", {"gate": gate_name, "status": "failed", "issues": issues}
    except FileNotFoundError:
        return "not_installed", {
            "gate": gate_name,
            "status": "not_installed",
            "issues": [],
            "message": f"{cmd[0]} not found in PATH",
        }
    except Exception as exc:
        return "error", {"gate": gate_name, "status": "error", "issues": [str(exc)]}


def run_quality_gates(
    project: Path,
    *,
    gates: list[str] | None = None,
    fail_fast: bool = True,
    oom_kill_threshold_mb: int = 2048,
    oom_monitor_interval_seconds: int = 5,
    oom_action: str = "kill",
) -> dict[str, Any]:
    """Run configured quality gates and return MCP-compatible payload."""
    commands = gate_commands(project)
    selected = resolve_gates(project, gates, commands)
    results: list[dict[str, Any]] = []
    overall = "passed"
    for gate_name in selected:
        cmd = commands.get(gate_name)
        if cmd is None:
            results.append(
                {
                    "gate": gate_name,
                    "status": "skipped",
                    "issues": [],
                    "message": f"Unknown gate: {gate_name}",
                }
            )
            continue
        if gate_name == "testql" and not has_testql_scenarios(project):
            results.append(
                {
                    "gate": gate_name,
                    "status": "skipped",
                    "issues": [],
                    "message": f"No {TESTQL_PATTERN} scenarios under project root",
                }
            )
            continue
        status, payload = run_single_gate(
            project,
            gate_name,
            cmd,
            oom_threshold_mb=oom_kill_threshold_mb,
            oom_interval_seconds=oom_monitor_interval_seconds,
            oom_action=oom_action,
        )
        results.append(payload)
        if status in {"failed", "timeout", "killed"}:
            overall = "failed"
            if fail_fast:
                break
    return {"overall_status": overall, "results": results}
