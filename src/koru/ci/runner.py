"""Run the project policy CI command and Koru quality gates."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

from koru.ci.gates import run_quality_gates
from koru.policy import load_policy


def run_policy_ci_command(project: Path, *, timeout_seconds: int | None = None) -> tuple[int, str]:
    policy = load_policy(project)
    command = (policy.ci_command or "").strip()
    if not command:
        return 2, "No ci.command configured in .planfile/.koru/policy.yaml"
    timeout = timeout_seconds or policy.ci_timeout_seconds
    proc = subprocess.run(
        ["bash", "-lc", command],
        cwd=str(project),
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )
    output = (proc.stdout or "") + (proc.stderr or "")
    return proc.returncode, output


def run_local_ci(
    project: Path,
    *,
    include_gates: bool = True,
    gates: list[str] | None = None,
    fail_fast: bool = True,
) -> dict[str, Any]:
    """Run policy CI command, then optional Koru quality gates."""
    project = project.resolve()
    policy = load_policy(project)
    stages: list[dict[str, Any]] = []

    has_policy_command = bool(policy.ci_command and policy.ci_command.strip())
    if has_policy_command:
        try:
            code, output = run_policy_ci_command(project)
        except subprocess.TimeoutExpired:
            stages.append({"stage": "policy_ci", "status": "timeout", "exit_code": 124})
            return {"overall_status": "failed", "stages": stages}
        status = "passed" if code == 0 else "failed"
        stages.append({"stage": "policy_ci", "status": status, "exit_code": code, "output_tail": output[-4000:]})
        if code != 0:
            return {"overall_status": "failed", "stages": stages}
    elif not include_gates:
        stages.append({
            "stage": "policy_ci",
            "status": "skipped",
            "skipped": True,
            "reason": "no_ci_command",
        })

    if include_gates:
        gate_result = run_quality_gates(project, gates=gates, fail_fast=fail_fast)
        stages.append({"stage": "quality_gates", **gate_result})
        if gate_result.get("overall_status") != "passed":
            return {"overall_status": "failed", "stages": stages}
    else:
        stages.append({
            "stage": "quality_gates",
            "status": "skipped",
            "skipped": True,
            "reason": "skip_gates_requested",
        })

    active_stages = [s for s in stages if s.get("status") not in ("skipped", None)]
    if not active_stages:
        return {
            "overall_status": "not_verified",
            "stages": stages,
            "reason": "zero_checks_executed",
        }

    return {"overall_status": "passed", "stages": stages}
