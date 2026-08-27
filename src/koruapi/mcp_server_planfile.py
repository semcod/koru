"""MCP tool handlers and schemas for planfile tickets, jobs, and quality gates."""

from __future__ import annotations

import json
import subprocess
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from koru.quality_gate_commands import sumr_scan_command, vallm_batch_command
from koru.queue.koru_queue_argv import build_koru_queue_argv
from koru.redup_integration import redup_check_command

try:
    import psutil

    _PSUTIL_AVAILABLE = True
except ImportError:
    _PSUTIL_AVAILABLE = False

DEFAULT_GATES = ["regix", "redup"]
RUN_TICKET_TIMEOUT_SECONDS = 300
JOB_STORE_FILE = ".planfile/.koru/jobs.json"
PATCH_BUDGET_LINES = 80
OVERSIZED_FILE_COUNT = 5
OVERSIZED_PROMPT_CHARS = 2000
_PROJECT_ROOT_KEYS = ("project_root", "project", "project_dir", "cwd")


def resolve_mcp_project_root(arguments: dict[str, Any]) -> Path:
    """Resolve project path from MCP args; accept common aliases.

    Agents often pass ``project`` / ``project_dir`` / ``cwd`` instead of
    ``project_root``. Prefer an explicit alias over a silent KeyError.
    """
    for key in _PROJECT_ROOT_KEYS:
        raw = arguments.get(key)
        if isinstance(raw, str) and raw.strip():
            return Path(raw).expanduser().resolve()
    raise KeyError(
        "Missing project path: pass project_root (or alias project / "
        "project_dir / cwd) as an absolute path on disk."
    )


def _project_root_schema_props(description: str) -> dict[str, Any]:
    return {
        "project_root": {
            "type": "string",
            "description": description,
        },
        "project": {
            "type": "string",
            "description": "Alias for project_root (absolute path).",
        },
    }


def build_tool_schemas(*, project_root_description: str) -> list[dict[str, Any]]:
    """Return tools/list schema entries for planfile MCP tools."""
    return [
        {
            "name": "koru_list_tickets",
            "description": (
                "List koru tickets for a given project (planfile queue). "
                "Returns ticket id, title, status, priority, executor kind, and associated files. "
                "When the filtered list is empty, also returns queue_status, counts, and "
                "suggested_actions (scan, waiting_input, split large work)."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    **_project_root_schema_props(project_root_description),
                    "queue_name": {
                        "type": "string",
                        "description": "Optional queue name if multiple queues exist.",
                    },
                    "status": {
                        "type": "string",
                        "enum": [
                            "open",
                            "in_progress",
                            "waiting_input",
                            "done",
                            "all",
                        ],
                        "default": "open",
                        "description": (
                            "Filter tickets by status. Use waiting_input to see "
                            "human-blocked tickets when the open queue looks empty."
                        ),
                    },
                },
                "required": ["project_root"],
            },
        },
        {
            "name": "koru_run_ticket",
            "description": (
                "Run koru autopilot/planfile pipeline for a single ticket. "
                "Executes a closed-loop: scan -> plan -> apply changes -> run tests -> quality gates."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    **_project_root_schema_props(project_root_description),
                    "ticket_id": {
                        "type": "string",
                        "description": "Ticket ID from koru queue.",
                    },
                    "queue_name": {
                        "type": "string",
                        "description": "Optional planfile execution queue (koru --queue-name).",
                    },
                    "actor": {
                        "type": "string",
                        "description": "Optional actor for ticket claim metadata (koru --actor).",
                    },
                    "mode": {
                        "type": "string",
                        "enum": ["dry", "apply"],
                        "default": "apply",
                        "description": "Dry-run only or apply changes to the working tree.",
                    },
                    "max_steps": {
                        "type": "integer",
                        "minimum": 1,
                        "description": "Optional safety limit on number of steps/iterations.",
                    },
                    "oom_kill_threshold_mb": {
                        "type": "integer",
                        "minimum": 100,
                        "description": (
                            "Memory limit in MB before killing subprocess (default: 4096). "
                            "Set to 0 to disable."
                        ),
                    },
                    "oom_monitor_interval_seconds": {
                        "type": "integer",
                        "minimum": 1,
                        "description": "Polling interval for memory stats in seconds (default: 5).",
                    },
                    "oom_action": {
                        "type": "string",
                        "enum": ["kill", "warn", "continue"],
                        "default": "kill",
                        "description": (
                            "Action when OOM is detected: kill subprocess, warn only, or continue."
                        ),
                    },
                },
                "required": ["project_root", "ticket_id"],
            },
        },
        {
            "name": "koru_job_status",
            "description": "Check status of a long-running koru job.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "job_id": {
                        "type": "string",
                        "description": "Job ID returned by koru_run_ticket.",
                    },
                },
                "required": ["job_id"],
            },
        },
        {
            "name": "koru_run_quality_gates",
            "description": (
                "Run koru quality gates (regix, redup, vallm, sumr, etc.) for a project. "
                "Returns per-gate pass/fail status and issue details."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    **_project_root_schema_props(project_root_description),
                    "gates": {
                        "type": "array",
                        "items": {
                            "type": "string",
                            "enum": ["regix", "redup", "vallm", "sumr", "testql", "security"],
                        },
                        "description": "Subset of gates to run; if omitted, run all configured.",
                    },
                    "fail_fast": {
                        "type": "boolean",
                        "default": True,
                        "description": "Stop on first failing gate when true.",
                    },
                    "oom_kill_threshold_mb": {
                        "type": "integer",
                        "minimum": 100,
                        "description": (
                            "Memory limit in MB before killing subprocess (default: 2048). "
                            "Set to 0 to disable."
                        ),
                    },
                    "oom_monitor_interval_seconds": {
                        "type": "integer",
                        "minimum": 1,
                        "description": "Polling interval for memory stats in seconds (default: 5).",
                    },
                    "oom_action": {
                        "type": "string",
                        "enum": ["kill", "warn", "continue"],
                        "default": "kill",
                        "description": (
                            "Action when OOM is detected: kill subprocess, warn only, or continue."
                        ),
                    },
                },
                "required": ["project_root"],
            },
        },
        {
            "name": "koru_propose_edits",
            "description": (
                "Propose code edits for a given ticket as file edits (no direct writes). "
                "Returns edit operations that the IDE can apply locally. "
                "Includes workflow_hints when the ticket looks oversized for the ≤80-line patch budget."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    **_project_root_schema_props(project_root_description),
                    "ticket_id": {
                        "type": "string",
                        "description": "Ticket ID from koru queue for which to propose edits.",
                    },
                    "files_scope": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional whitelist of files to modify (relative paths).",
                    },
                    "max_edits": {
                        "type": "integer",
                        "minimum": 1,
                        "description": "Optional safety cap on number of edits.",
                    },
                },
                "required": ["project_root", "ticket_id"],
            },
        },
    ]


def _get_job_store_path(project: Path | None = None) -> Path:
    if project is None:
        project = Path.cwd()
    return project / JOB_STORE_FILE


def _load_jobs(project: Path | None = None) -> dict[str, dict[str, Any]]:
    job_store_path = _get_job_store_path(project)
    if not job_store_path.exists():
        return {}
    try:
        with job_store_path.open(encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


_jobs: dict[str, dict[str, Any]] = _load_jobs()


def _save_jobs(jobs: dict[str, dict[str, Any]], project: Path | None = None) -> None:
    job_store_path = _get_job_store_path(project)
    job_store_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(job_store_path, "w", encoding="utf-8") as f:
            json.dump(jobs, f, indent=2, default=str)
    except OSError:
        pass


def _get_process_memory_mb(pid: int) -> float:
    if not _PSUTIL_AVAILABLE:
        return 0.0
    try:
        process = psutil.Process(pid)
        return process.memory_info().rss / (1024 * 1024)
    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
        return 0.0


def _monitor_subprocess_oom(
    proc: subprocess.Popen[str],
    threshold_mb: int,
    interval_seconds: int,
    action: str,
) -> tuple[bool, list[str]]:
    logs: list[str] = []
    if threshold_mb == 0 or not _PSUTIL_AVAILABLE:
        return False, logs

    try:
        while proc.poll() is None:
            memory_mb = _get_process_memory_mb(proc.pid)
            if memory_mb > threshold_mb:
                msg = (
                    f"Process {proc.pid} exceeded OOM threshold: "
                    f"{memory_mb:.1f}MB > {threshold_mb}MB"
                )
                logs.append(msg)
                if action == "kill":
                    logs.append(f"Killing process {proc.pid} due to OOM")
                    proc.kill()
                    return True, logs
                if action == "warn":
                    logs.append("Warning: OOM detected but continuing (action=warn)")
            time.sleep(interval_seconds)
    except Exception as exc:
        logs.append(f"OOM monitoring error: {exc}")
    return False, logs


def _tickets_for_status_filter(
    ctx: dict[str, Any],
    status_filter: str,
) -> list[dict[str, Any]]:
    all_tickets = ctx.get("all_tickets") or []
    open_tickets = ctx.get("open_tickets") or []
    if status_filter == "all":
        return all_tickets
    if status_filter == "open":
        return open_tickets
    if status_filter == "in_progress":
        return [t for t in all_tickets if t.get("status") == "in_progress"]
    if status_filter == "waiting_input":
        return [t for t in all_tickets if t.get("status") == "waiting_input"]
    if status_filter == "done":
        return [t for t in all_tickets if t.get("status") == "done"]
    return open_tickets


def _ticket_status_counts(all_tickets: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {
        "open": 0,
        "in_progress": 0,
        "waiting_input": 0,
        "done": 0,
        "other": 0,
        "total": len(all_tickets),
    }
    for ticket in all_tickets:
        status = str(ticket.get("status") or "other")
        if status in counts:
            counts[status] += 1
        else:
            counts["other"] += 1
    return counts


def _idle_queue_suggested_actions(counts: dict[str, int]) -> list[str]:
    actions = [
        "koru scan --apply  # discover new work from repo signals",
        (
            f"Split large migrations into tickets with ≤{PATCH_BUDGET_LINES}-line patches "
            "(one commit per ticket)"
        ),
        "koru_run_quality_gates  # check regix/redup even when the queue is idle",
    ]
    if counts.get("waiting_input", 0) > 0:
        actions.insert(
            0,
            "koru_list_tickets status=waiting_input  # unblock human-gated tickets",
        )
    if counts.get("in_progress", 0) > 0:
        actions.insert(
            0,
            "koru_list_tickets status=in_progress  # resume or finish claimed work",
        )
    return actions


def _serialize_mcp_ticket(ticket: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": ticket.get("id", ""),
        "title": ticket.get("name", ""),
        "status": ticket.get("status", "open"),
        "queue": ticket.get("queue", "default"),
        "priority": ticket.get("priority", "normal"),
        "files": ticket.get("files") or [],
        "executor_kind": (ticket.get("executor") or {}).get("kind", "unknown"),
    }


def tool_list_tickets(arguments: dict[str, Any]) -> dict[str, Any]:
    """List open tickets from the planfile queue."""
    try:
        project = resolve_mcp_project_root(arguments)
    except KeyError as exc:
        return {"tickets": [], "error": str(exc)}
    queue_name = arguments.get("queue_name")
    status_filter = arguments.get("status", "open")

    from koru.context import build_context

    try:
        ctx = build_context(project=project, queue_name=queue_name)
    except Exception as exc:
        return {"tickets": [], "error": str(exc)}

    tickets = _tickets_for_status_filter(ctx, str(status_filter))
    payload: dict[str, Any] = {
        "tickets": [_serialize_mcp_ticket(t) for t in tickets],
        "status_filter": status_filter,
    }
    all_tickets = ctx.get("all_tickets") or []
    counts = _ticket_status_counts(all_tickets)
    payload["counts"] = counts
    if not tickets:
        payload["queue_status"] = "idle"
        payload["suggested_actions"] = _idle_queue_suggested_actions(counts)
    else:
        payload["queue_status"] = "active"
    return payload


def _create_job(ticket_id: str, mode: str, project: Path | None = None) -> str:
    job_id = f"JOB-{uuid.uuid4().hex[:8]}"
    _jobs[job_id] = {
        "status": "running",
        "ticket_id": ticket_id,
        "mode": mode,
        "started_at": datetime.now(UTC).isoformat(),
        "logs": [],
        "progress": 0.0,
        "current_step": "starting",
    }
    _save_jobs(_jobs, project)
    return job_id


def _update_job(job_id: str, project: Path | None = None, **fields: Any) -> None:
    _jobs[job_id].update(fields)
    _save_jobs(_jobs, project)


def _collect_process_logs(
    result: subprocess.CompletedProcess[str],
    *,
    limit: int = 20,
) -> list[str]:
    logs: list[str] = []
    if result.stdout:
        logs.extend(result.stdout.strip().split("\n"))
    if result.stderr:
        logs.extend(result.stderr.strip().split("\n"))
    return logs[-limit:]


def _launch_oom_monitor(
    proc: subprocess.Popen,
    threshold_mb: int,
    interval_seconds: float | int,
    action: str,
) -> list:
    import threading

    state: list = [False, []]
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


def _run_ticket_queue_args(project: Path, arguments: dict[str, Any]) -> list[str]:
    actor = arguments.get("actor")
    queue_name = arguments.get("queue_name")
    return build_koru_queue_argv(
        project,
        mode=arguments.get("mode", "apply"),
        max_steps=arguments.get("max_steps"),
        actor=actor if isinstance(actor, str) and actor.strip() else None,
        queue_name=queue_name if isinstance(queue_name, str) and queue_name.strip() else None,
        ticket_id=str(arguments["ticket_id"]),
    )


def _run_ticket_timeout_response(
    job_id: str,
    project: Path,
    ticket_id: str,
    mode: str,
) -> dict[str, Any]:
    timeout_logs = [f"Operation timed out after {RUN_TICKET_TIMEOUT_SECONDS} seconds."]
    _update_job(
        job_id,
        project,
        status="timeout",
        current_step="timeout",
        progress=1.0,
        logs=timeout_logs,
    )
    return {
        "status": "timeout",
        "ticket_id": ticket_id,
        "mode": mode,
        "job_id": job_id,
        "logs": timeout_logs,
    }


def _run_ticket_oom_response(
    *,
    job_id: str,
    project: Path,
    ticket_id: str,
    mode: str,
    cmd_args: list[str],
    stdout: str,
    stderr: str,
    oom_logs: list[str],
) -> dict[str, Any]:
    logs = oom_logs + _collect_process_logs(
        subprocess.CompletedProcess(
            args=cmd_args,
            returncode=-9,
            stdout=stdout,
            stderr=stderr,
        ),
    )
    _update_job(
        job_id,
        project,
        status="killed",
        current_step="oom_killed",
        progress=1.0,
        logs=logs,
    )
    return {
        "status": "killed",
        "ticket_id": ticket_id,
        "mode": mode,
        "job_id": job_id,
        "logs": logs,
        "reason": "oom",
    }


def _run_ticket_completed_response(
    *,
    job_id: str,
    project: Path,
    ticket_id: str,
    mode: str,
    cmd_args: list[str],
    returncode: int,
    stdout: str,
    stderr: str,
) -> dict[str, Any]:
    result = subprocess.CompletedProcess(
        args=cmd_args,
        returncode=returncode,
        stdout=stdout,
        stderr=stderr,
    )
    logs = _collect_process_logs(result)
    is_success = result.returncode == 0
    _update_job(
        job_id,
        project,
        progress=1.0,
        status="success" if is_success else "failed",
        current_step="completed" if is_success else "failed",
        logs=logs,
    )

    response: dict[str, Any] = {
        "status": "success" if is_success else "failed",
        "ticket_id": ticket_id,
        "mode": mode,
        "job_id": job_id,
        "logs": logs,
    }
    if not is_success:
        response["exit_code"] = result.returncode
    return response


def _run_ticket_error_response(
    job_id: str,
    project: Path,
    ticket_id: str,
    exc: Exception,
) -> dict[str, Any]:
    error_message = str(exc)
    _update_job(
        job_id,
        project,
        status="error",
        current_step="error",
        progress=1.0,
        logs=[error_message],
    )
    return {
        "status": "error",
        "ticket_id": ticket_id,
        "job_id": job_id,
        "error": error_message,
    }


def tool_run_ticket(arguments: dict[str, Any]) -> dict[str, Any]:
    """Run the koru pipeline for a single ticket."""
    try:
        project = resolve_mcp_project_root(arguments)
    except KeyError as exc:
        return {"status": "error", "error": str(exc)}
    ticket_id = arguments["ticket_id"]
    mode = arguments.get("mode", "apply")
    oom_threshold = arguments.get("oom_kill_threshold_mb", 4096)
    oom_interval = arguments.get("oom_monitor_interval_seconds", 5)
    oom_action = arguments.get("oom_action", "kill")

    job_id = _create_job(ticket_id, mode, project)
    cmd_args = _run_ticket_queue_args(project, arguments)
    _update_job(job_id, project, current_step="running_queue", progress=0.3)

    try:
        proc = subprocess.Popen(
            cmd_args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=str(project),
        )

        oom_state = _launch_oom_monitor(proc, oom_threshold, oom_interval, oom_action)

        try:
            stdout, stderr = proc.communicate(timeout=RUN_TICKET_TIMEOUT_SECONDS)
        except subprocess.TimeoutExpired:
            proc.kill()
            stdout, stderr = proc.communicate()
            return _run_ticket_timeout_response(job_id, project, ticket_id, mode)

        oom_killed, oom_logs = oom_state[0], oom_state[1]
        if oom_killed:
            return _run_ticket_oom_response(
                job_id,
                project=project,
                ticket_id=ticket_id,
                mode=mode,
                cmd_args=cmd_args,
                stdout=stdout,
                stderr=stderr,
                oom_logs=oom_logs,
            )

        return _run_ticket_completed_response(
            job_id=job_id,
            project=project,
            ticket_id=ticket_id,
            mode=mode,
            cmd_args=cmd_args,
            returncode=proc.returncode,
            stdout=stdout,
            stderr=stderr,
        )
    except Exception as exc:
        return _run_ticket_error_response(job_id, project, ticket_id, exc)


def tool_job_status(arguments: dict[str, Any]) -> dict[str, Any]:
    """Check status of a previously started job."""
    job_id = arguments["job_id"]
    job = _jobs.get(job_id)
    if job is None:
        return {"job_id": job_id, "status": "not_found", "error": f"Unknown job: {job_id}"}
    return {
        "job_id": job_id,
        "status": job["status"],
        "progress": job.get("progress", 0.0),
        "current_step": job.get("current_step", "unknown"),
        "logs_tail": (job.get("logs") or [])[-10:],
    }


def _gate_commands(project: Path) -> dict[str, list[str]]:
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


def _resolve_gates(
    project: Path,
    requested: list[str],
    commands: dict[str, list[str]],
) -> list[str]:
    if requested:
        return requested
    detected = _detect_enabled_gates(project, list(commands.keys()))
    if detected:
        return detected
    return list(commands.keys()) or list(DEFAULT_GATES)


def _run_single_gate(
    project: Path,
    gate_name: str,
    cmd: list[str],
    oom_threshold_mb: int = 2048,
    oom_interval_seconds: int = 5,
    oom_action: str = "kill",
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
            stdout, stderr = proc.communicate(timeout=120)
        except subprocess.TimeoutExpired:
            proc.kill()
            stdout, stderr = proc.communicate()
            return "timeout", {
                "gate": gate_name,
                "status": "timeout",
                "issues": ["Gate timed out after 120 seconds."],
            }

        oom_killed, oom_logs = oom_state[0], oom_state[1]
        if oom_killed:
            output_lines = (stdout or "").strip().split("\n")
            error_lines = (stderr or "").strip().split("\n")
            issues = oom_logs + (output_lines + error_lines)[-10:]
            return "killed", {
                "gate": gate_name,
                "status": "killed",
                "issues": issues,
                "reason": "oom",
            }

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


def tool_run_quality_gates(arguments: dict[str, Any]) -> dict[str, Any]:
    """Run quality gates for the project."""
    try:
        project = resolve_mcp_project_root(arguments)
    except KeyError as exc:
        return {"overall_status": "error", "results": [], "error": str(exc)}
    requested_gates = arguments.get("gates") or []
    fail_fast = arguments.get("fail_fast", True)
    oom_threshold = arguments.get("oom_kill_threshold_mb", 2048)
    oom_interval = arguments.get("oom_monitor_interval_seconds", 5)
    oom_action = arguments.get("oom_action", "kill")

    gate_commands = _gate_commands(project)
    gates = _resolve_gates(project, requested_gates, gate_commands)

    results: list[dict[str, Any]] = []
    overall = "passed"
    for gate_name in gates:
        cmd = gate_commands.get(gate_name)
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

        status, payload = _run_single_gate(
            project,
            gate_name,
            cmd,
            oom_threshold_mb=oom_threshold,
            oom_interval_seconds=oom_interval,
            oom_action=oom_action,
        )
        results.append(payload)

        if status in {"failed", "timeout", "killed"}:
            overall = "failed"
            if fail_fast:
                break

    return {"overall_status": overall, "results": results}


def _find_ticket(all_tickets: list[dict[str, Any]], ticket_id: str) -> dict[str, Any] | None:
    for ticket in all_tickets:
        if ticket.get("id") == ticket_id:
            return ticket
    return None


def _build_edit_context(project: Path, file_path: str) -> dict[str, Any]:
    full_path = project / file_path
    if not full_path.is_file():
        return {
            "file_path": file_path,
            "operation": "create_if_missing",
            "exists": False,
        }
    try:
        content = full_path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return {
            "file_path": file_path,
            "operation": "review",
            "exists": True,
            "read_error": True,
        }
    return {
        "file_path": file_path,
        "operation": "review",
        "line_count": len(content.split("\n")),
        "exists": True,
    }


def _ticket_workflow_hints(
    *,
    ticket_files: list[Any],
    prompt: str,
) -> dict[str, Any]:
    file_count = len(ticket_files)
    prompt_chars = len(prompt or "")
    oversized = file_count >= OVERSIZED_FILE_COUNT or prompt_chars >= OVERSIZED_PROMPT_CHARS
    hints: dict[str, Any] = {
        "patch_budget_lines": PATCH_BUDGET_LINES,
        "file_count": file_count,
        "prompt_chars": prompt_chars,
        "oversized": oversized,
    }
    if oversized:
        hints["guidance"] = (
            f"Ticket looks large for a single ≤{PATCH_BUDGET_LINES}-line patch. "
            "Split into smaller planfile tickets (one concern / few files each) "
            "before implementing; keep one commit per ticket."
        )
    return hints


def _resolve_propose_edits_ticket(
    project: Path, ticket_id: str
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    from koru.context import build_context

    try:
        ctx = build_context(project=project)
    except Exception as exc:
        return None, {"ticket_id": ticket_id, "edits": [], "error": str(exc)}

    all_tickets = ctx.get("all_tickets") or []
    ticket = _find_ticket(all_tickets, ticket_id)
    if ticket is None:
        return None, {
            "ticket_id": ticket_id,
            "edits": [],
            "error": f"Ticket {ticket_id} not found in queue.",
        }
    return ticket, None


def _scope_ticket_files(ticket_files: list[Any], files_scope: list[Any]) -> list[Any]:
    if not files_scope:
        return ticket_files
    return [f for f in ticket_files if f in files_scope]


def _collect_edit_contexts(
    project: Path, ticket_files: list[Any], max_edits: Any
) -> list[dict[str, Any]]:
    edits_context = [_build_edit_context(project, file_path) for file_path in ticket_files]
    if max_edits and len(edits_context) > max_edits:
        edits_context = edits_context[:max_edits]
    return edits_context


def tool_propose_edits(arguments: dict[str, Any]) -> dict[str, Any]:
    """Generate proposed file edits for a ticket (read-only, no writes)."""
    try:
        project = resolve_mcp_project_root(arguments)
    except KeyError as exc:
        return {"ticket_id": arguments.get("ticket_id"), "edits": [], "error": str(exc)}
    ticket_id = arguments["ticket_id"]
    files_scope = arguments.get("files_scope") or []
    max_edits = arguments.get("max_edits")

    ticket, error = _resolve_propose_edits_ticket(project, ticket_id)
    if error is not None:
        return error

    ticket_files = _scope_ticket_files(ticket.get("files") or [], files_scope)

    inputs = ticket.get("inputs") or {}
    prompt = inputs.get("prompt", "")
    description = ticket.get("name", "")

    edits_context = _collect_edit_contexts(project, ticket_files, max_edits)

    return {
        "ticket_id": ticket_id,
        "title": description,
        "prompt": prompt,
        "files": ticket_files,
        "edits": edits_context,
        "executor_kind": (ticket.get("executor") or {}).get("kind", "unknown"),
        "workflow_hints": _ticket_workflow_hints(
            ticket_files=ticket_files,
            prompt=str(prompt or ""),
        ),
    }


TOOL_DISPATCH: dict[str, Any] = {
    "koru_list_tickets": tool_list_tickets,
    "koru_run_ticket": tool_run_ticket,
    "koru_job_status": tool_job_status,
    "koru_run_quality_gates": tool_run_quality_gates,
    "koru_propose_edits": tool_propose_edits,
}
