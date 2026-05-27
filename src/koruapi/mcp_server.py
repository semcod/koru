"""koru MCP server — expose koru tools to IDE agents via Model Context Protocol.

Implements a stdio-based MCP server that wraps existing koru modules
(context, queue, scan, gate, autonomous) as MCP tools. Compatible with
Windsurf, Cursor, VS Code, and any IDE supporting MCP stdio transport.

Tools:
    koru_list_tickets    — list open tickets from planfile queue
    koru_run_ticket      — run autopilot pipeline for a single ticket
    koru_job_status      — check status of a long-running job
    koru_run_quality_gates — run quality gates (regix, redup, vallm, etc.)
    koru_propose_edits   — propose file edits for a ticket (read-only)

Start via CLI::

    koru mcp-serve                         # stdio (default)
    koru mcp-serve --project /path/to/repo # explicit project root

The server communicates over stdin/stdout using JSON-RPC 2.0 per the
MCP specification. No external HTTP port is opened.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import traceback
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from koru.queue.koru_queue_argv import build_koru_queue_argv
from koru.redup_integration import redup_check_command

try:
    import psutil

    _PSUTIL_AVAILABLE = True
except ImportError:
    _PSUTIL_AVAILABLE = False

# ---------------------------------------------------------------------------
# Lazy imports — avoid pulling heavy modules until a tool is actually called.
# This keeps startup fast for the stdio handshake.
# ---------------------------------------------------------------------------

_PROTOCOL_VERSION = "2024-11-05"
_SERVER_NAME = "koru"
_SERVER_VERSION = "0.2.1"
_PROJECT_ROOT_DESCRIPTION = "Absolute path to project root on disk."
_DEFAULT_GATES = ["regix", "redup"]
_RUN_TICKET_TIMEOUT_SECONDS = 300

# Job store file path (relative to project root)
_JOB_STORE_FILE = ".planfile/.koru/jobs.json"


def _get_job_store_path(project: Path | None = None) -> Path:
    """Get the job store file path for a project."""
    if project is None:
        # Default to current directory if no project specified
        project = Path.cwd()
    return project / _JOB_STORE_FILE


def _load_jobs(project: Path | None = None) -> dict[str, dict[str, Any]]:
    """Load jobs from the JSON file."""
    job_store_path = _get_job_store_path(project)
    if not job_store_path.exists():
        return {}
    try:
        with job_store_path.open(encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


# In-memory job store for long-running operations
_jobs: dict[str, dict[str, Any]] = _load_jobs()


def _save_jobs(jobs: dict[str, dict[str, Any]], project: Path | None = None) -> None:
    """Save jobs to the JSON file."""
    job_store_path = _get_job_store_path(project)
    job_store_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(job_store_path, "w", encoding="utf-8") as f:
            json.dump(jobs, f, indent=2, default=str)
    except OSError:
        pass  # Silently fail if we can't write (e.g., read-only filesystem)


def _get_process_memory_mb(pid: int) -> float:
    """Get process memory usage in MB."""
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
    """Monitor subprocess for OOM conditions.

    Returns (should_kill, logs) tuple.
    """
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
                elif action == "warn":
                    logs.append("Warning: OOM detected but continuing (action=warn)")
                # action == "continue": do nothing
            time.sleep(interval_seconds)
    except Exception as exc:
        logs.append(f"OOM monitoring error: {exc}")
    return False, logs


# ---------------------------------------------------------------------------
# Tool definitions (MCP tools/list response)
# ---------------------------------------------------------------------------

TOOLS: list[dict[str, Any]] = [
    {
        "name": "koru_list_tickets",
        "description": (
            "List open koru tickets for a given project (planfile queue). "
            "Returns ticket id, title, status, priority, executor kind, and associated files."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "project_root": {
                    "type": "string",
                    "description": _PROJECT_ROOT_DESCRIPTION,
                },
                "queue_name": {
                    "type": "string",
                    "description": "Optional queue name if multiple queues exist.",
                },
                "status": {
                    "type": "string",
                    "enum": ["open", "in_progress", "done", "all"],
                    "default": "open",
                    "description": "Filter tickets by status.",
                },
            },
            "required": ["project_root"],
        },
    },
    {
        "name": "koru_run_ticket",
        "description": (
            "Run koru autopilot/planfile pipeline for a single ticket. "
            "Executes a closed-loop: scan → plan → apply changes → run tests → quality gates."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "project_root": {
                    "type": "string",
                    "description": _PROJECT_ROOT_DESCRIPTION,
                },
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
                "project_root": {
                    "type": "string",
                    "description": _PROJECT_ROOT_DESCRIPTION,
                },
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
            "Returns edit operations that the IDE can apply locally."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "project_root": {
                    "type": "string",
                    "description": _PROJECT_ROOT_DESCRIPTION,
                },
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
    {
        "name": "koru_ide_command_catalog",
        "description": (
            "Return the normalized IDE command/action catalog for LLM planning. "
            "The catalog is candidate-only; Koru verifies live commands before execution."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "ide": {
                    "type": "string",
                    "description": "IDE id or all.",
                    "default": "all",
                },
                "for_llm": {
                    "type": "boolean",
                    "default": True,
                    "description": "Return compact LLM-oriented catalog.",
                },
            },
        },
    },
    {
        "name": "koru_ide_command_scenario_schema",
        "description": "Return JSON Schema for Koru IDE command scenarios.",
        "inputSchema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "koru_strategy_prompt",
        "description": (
            "Return the LLM strategy briefing (catalog + scenario schema + policy) "
            "as a ready-to-paste prompt for IDE control planning."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "ide": {
                    "type": "string",
                    "description": "IDE id or 'all'.",
                    "default": "all",
                },
                "for_llm": {
                    "type": "boolean",
                    "default": True,
                    "description": "Compact category-only catalog (recommended).",
                },
                "include_text": {
                    "type": "boolean",
                    "default": True,
                    "description": "Include rendered Markdown 'text' field.",
                },
            },
        },
    },
    {
        "name": "koru_validate_ide_command_scenario",
        "description": (
            "Validate an LLM-authored IDE command scenario against Koru's command catalog "
            "and risk policy."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "scenario": {
                    "type": "object",
                    "description": "Scenario object matching koru.ide_command_scenario.v1.",
                    "additionalProperties": True,
                },
            },
            "required": ["scenario"],
        },
    },
    {
        "name": "koru_ide_commands",
        "description": (
            "Return the runtime IDE command catalog and per-command telemetry "
            "for a connected Koru autopilot plugin (focus/paste/submit candidates)."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "project_root": {
                    "type": "string",
                    "description": _PROJECT_ROOT_DESCRIPTION,
                },
                "ide": {
                    "type": "string",
                    "description": "IDE id (cursor, vscode, windsurf, vscodium, antigravity).",
                },
                "capability": {
                    "type": "string",
                    "description": "Optional capability filter (focus_open, paste, submit, ...).",
                },
            },
            "required": ["project_root"],
        },
    },
    {
        "name": "koru_ide_drive",
        "description": (
            "Send a prompt to the IDE chat via the koruide daemon drive/chat.send path."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "project_root": {
                    "type": "string",
                    "description": _PROJECT_ROOT_DESCRIPTION,
                },
                "text": {"type": "string", "description": "Prompt text to paste into IDE chat."},
                "ide": {
                    "type": "string",
                    "description": "Target IDE (default: auto).",
                },
                "submit": {
                    "type": "boolean",
                    "default": True,
                    "description": "Whether to submit after paste.",
                },
                "strategy_hint": {
                    "type": "string",
                    "description": "Optional picker hint (e.g. llm).",
                },
            },
            "required": ["project_root", "text"],
        },
    },
    {
        "name": "koru_ide_dsl_recent",
        "description": "Return recent Koru Drive DSL trace lines from the autopilot daemon.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "project_root": {
                    "type": "string",
                    "description": _PROJECT_ROOT_DESCRIPTION,
                },
                "limit": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 50,
                    "default": 20,
                    "description": "Maximum number of DSL lines to return.",
                },
            },
            "required": ["project_root"],
        },
    },
]


# ---------------------------------------------------------------------------
# Tool implementations
# ---------------------------------------------------------------------------


def _get_python_cmd() -> str:
    """Return the Python command available in the environment."""
    from koru.utils.subprocess_runner import get_python_cmd

    return get_python_cmd()


def _run_planfile_cli(project: Path, *args: str) -> subprocess.CompletedProcess[str]:
    """Call ``planfile`` CLI as a subprocess, returning stdout."""
    python = _get_python_cmd()
    cmd = [python, "-m", "planfile"] + list(args) + ["--project", str(project)]
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=30,
        cwd=str(project),
    )


def _parse_tickets_json(stdout: str) -> list[dict[str, Any]]:
    """Parse planfile ticket list JSON output."""
    stripped = stdout.strip()
    if not stripped or "No runnable ticket" in stripped:
        return []
    try:
        data = json.loads(stripped)
    except json.JSONDecodeError:
        return []
    if isinstance(data, list):
        return [t for t in data if isinstance(t, dict)]
    if isinstance(data, dict):
        return [data]
    return []


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
    if status_filter == "done":
        return [t for t in all_tickets if t.get("status") == "done"]
    return open_tickets


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
    project = Path(arguments["project_root"]).resolve()
    queue_name = arguments.get("queue_name")
    status_filter = arguments.get("status", "open")

    from koru.context import build_context

    try:
        ctx = build_context(project=project, queue_name=queue_name)
    except Exception as exc:
        return {"tickets": [], "error": str(exc)}

    tickets = _tickets_for_status_filter(ctx, str(status_filter))
    return {"tickets": [_serialize_mcp_ticket(t) for t in tickets]}


def tool_ide_command_catalog(arguments: dict[str, Any]) -> dict[str, Any]:
    from koruide.command_catalog import build_ide_command_catalog, command_catalog_for_llm

    ide_raw = arguments.get("ide", "all")
    ide = None if ide_raw in (None, "", "all") else str(ide_raw)
    for_llm = bool(arguments.get("for_llm", True))
    catalog = command_catalog_for_llm(ide) if for_llm else build_ide_command_catalog(ide)
    return {"catalog": catalog}


def tool_ide_command_scenario_schema(_arguments: dict[str, Any]) -> dict[str, Any]:
    from koruide.command_scenario import ide_command_scenario_schema

    return {"schema": ide_command_scenario_schema()}


def tool_strategy_prompt(arguments: dict[str, Any]) -> dict[str, Any]:
    """Return Koru's LLM-ready IDE strategy prompt."""
    from koruide.strategy_prompt import build_strategy_prompt

    ide_raw = arguments.get("ide", "all")
    ide = None if ide_raw in (None, "", "all") else str(ide_raw)
    for_llm = bool(arguments.get("for_llm", True))
    include_text = bool(arguments.get("include_text", True))
    try:
        payload = build_strategy_prompt(ide, for_llm=for_llm, include_text=include_text)
    except ValueError as exc:
        return {"ok": False, "error": str(exc)}
    return {"ok": True, "prompt": payload}


def tool_ide_commands(arguments: dict[str, Any]) -> dict[str, Any]:
    """Expose stored runtime command catalog + telemetry for IDE LLM introspection."""
    from koruide.command_catalog import build_ide_command_catalog
    from koruide.command_catalog_store import CommandCatalogStore
    from koruide.command_telemetry import CommandTelemetry

    project = Path(arguments["project_root"]).resolve()
    ide = arguments.get("ide")
    capability = arguments.get("capability")
    store = CommandCatalogStore(project)
    telemetry = CommandTelemetry(project)
    static = build_ide_command_catalog(ide if isinstance(ide, str) else None)
    if isinstance(ide, str):
        entry = store.get(ide)
        rows = telemetry.rows_for(
            ide,
            capability=capability if isinstance(capability, str) else None,
        )
        return {
            "ide": ide,
            "capability": capability,
            "static_catalog": static,
            "runtime_catalog": {ide: entry} if entry else {},
            "telemetry": rows,
        }
    return {
        "static_catalog": static,
        "runtime_catalog": {ide_id: store.get(ide_id) for ide_id in store.all_ides()},
        "telemetry_ides": store.all_ides(),
    }


def tool_ide_drive(arguments: dict[str, Any]) -> dict[str, Any]:
    """Drive IDE chat through koruide daemon."""
    from koruide.client import AutopilotClient
    from koruide.socket import default_socket_path

    text = str(arguments.get("text", ""))
    if not text.strip():
        return {"ok": False, "error": "text is required"}
    ide = str(arguments.get("ide", "auto"))
    submit = bool(arguments.get("submit", True))
    strategy_hint = arguments.get("strategy_hint")
    client = AutopilotClient(socket_path=default_socket_path(), timeout=45.0)
    if not client.is_running():
        return {"ok": False, "error": "koruide daemon is not running"}
    reply = client.drive(
        text,
        submit=submit,
        ide=ide,
        require_plugin=False,
        strategy_hint=strategy_hint if isinstance(strategy_hint, str) else None,
    )
    return {"ok": bool(reply.get("ok", True)), "reply": reply}


def tool_ide_dsl_recent(arguments: dict[str, Any]) -> dict[str, Any]:
    """Read persisted recent Drive DSL lines."""
    project = Path(arguments["project_root"]).resolve()
    limit = int(arguments.get("limit", 20))
    path = project / ".planfile" / ".koru" / "dsl_recent.json"
    if not path.is_file():
        return {"lines": [], "source": str(path), "count": 0}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {"lines": [], "error": str(exc), "source": str(path), "count": 0}
    lines = data.get("lines") if isinstance(data, dict) else []
    if not isinstance(lines, list):
        lines = []
    trimmed = [line for line in lines if isinstance(line, str)][-limit:]
    return {"lines": trimmed, "source": str(path), "count": len(trimmed)}


def tool_validate_ide_command_scenario(arguments: dict[str, Any]) -> dict[str, Any]:
    from koruide.command_scenario import validate_ide_command_scenario

    scenario = arguments.get("scenario")
    if not isinstance(scenario, dict):
        return {
            "ok": False,
            "validation": {
                "ok": False,
                "errors": ["scenario must be an object"],
                "warnings": [],
                "normalized": {},
            },
        }
    validation = validate_ide_command_scenario(scenario)
    return {"ok": validation.ok, "validation": validation.to_dict()}


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
    """Start OOM monitor thread. Returns mutable [killed_bool, logs_list] state."""
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
    )


def _run_ticket_timeout_response(
    job_id: str,
    project: Path,
    ticket_id: str,
    mode: str,
) -> dict[str, Any]:
    timeout_logs = [f"Operation timed out after {_RUN_TICKET_TIMEOUT_SECONDS} seconds."]
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
    if is_success:
        response["note"] = (
            "Queue execution is best-effort; current koru queue mode runs next runnable ticket."
        )
    else:
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
    project = Path(arguments["project_root"]).resolve()
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
            stdout, stderr = proc.communicate(timeout=_RUN_TICKET_TIMEOUT_SECONDS)
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
        "vallm": ["vallm", str(project)],
        "sumr": ["sumr", str(project)],
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
    return list(commands.keys()) or list(_DEFAULT_GATES)


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
    project = Path(arguments["project_root"]).resolve()
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


def tool_propose_edits(arguments: dict[str, Any]) -> dict[str, Any]:
    """Generate proposed file edits for a ticket (read-only, no writes)."""
    project = Path(arguments["project_root"]).resolve()
    ticket_id = arguments["ticket_id"]
    files_scope = arguments.get("files_scope") or []
    max_edits = arguments.get("max_edits")

    # Build context for the ticket to understand what files are involved
    from koru.context import build_context

    try:
        ctx = build_context(project=project)
    except Exception as exc:
        return {"ticket_id": ticket_id, "edits": [], "error": str(exc)}

    # Find the target ticket
    all_tickets = ctx.get("all_tickets") or []
    ticket = _find_ticket(all_tickets, ticket_id)

    if ticket is None:
        return {
            "ticket_id": ticket_id,
            "edits": [],
            "error": f"Ticket {ticket_id} not found in queue.",
        }

    # Extract file list and description
    ticket_files = ticket.get("files") or []
    if files_scope:
        ticket_files = [f for f in ticket_files if f in files_scope]

    inputs = ticket.get("inputs") or {}
    prompt = inputs.get("prompt", "")
    description = ticket.get("name", "")

    # Return ticket context as proposed scope — the IDE agent generates
    # the actual edits using its own LLM with this context.
    edits_context = [_build_edit_context(project, file_path) for file_path in ticket_files]

    if max_edits and len(edits_context) > max_edits:
        edits_context = edits_context[:max_edits]

    return {
        "ticket_id": ticket_id,
        "title": description,
        "prompt": prompt,
        "files": ticket_files,
        "edits": edits_context,
        "executor_kind": (ticket.get("executor") or {}).get("kind", "unknown"),
    }


# ---------------------------------------------------------------------------
# Tool dispatch table
# ---------------------------------------------------------------------------

_TOOL_DISPATCH: dict[str, Any] = {
    "koru_list_tickets": tool_list_tickets,
    "koru_run_ticket": tool_run_ticket,
    "koru_job_status": tool_job_status,
    "koru_run_quality_gates": tool_run_quality_gates,
    "koru_propose_edits": tool_propose_edits,
    "koru_ide_command_catalog": tool_ide_command_catalog,
    "koru_ide_command_scenario_schema": tool_ide_command_scenario_schema,
    "koru_strategy_prompt": tool_strategy_prompt,
    "koru_validate_ide_command_scenario": tool_validate_ide_command_scenario,
    "koru_ide_commands": tool_ide_commands,
    "koru_ide_drive": tool_ide_drive,
    "koru_ide_dsl_recent": tool_ide_dsl_recent,
}


# ---------------------------------------------------------------------------
# JSON-RPC 2.0 / MCP stdio transport
# ---------------------------------------------------------------------------


def _jsonrpc_response(req_id: Any, result: Any) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": req_id, "result": result}


def _jsonrpc_error(req_id: Any, code: int, message: str, data: Any = None) -> dict[str, Any]:
    err: dict[str, Any] = {"code": code, "message": message}
    if data is not None:
        err["data"] = data
    return {"jsonrpc": "2.0", "id": req_id, "error": err}


def _handle_initialize(params: dict[str, Any]) -> dict[str, Any]:
    return {
        "protocolVersion": _PROTOCOL_VERSION,
        "capabilities": {
            "tools": {},
        },
        "serverInfo": {
            "name": _SERVER_NAME,
            "version": _SERVER_VERSION,
        },
    }


def _handle_tools_list(params: dict[str, Any]) -> dict[str, Any]:
    return {"tools": TOOLS}


def _handle_tools_call(params: dict[str, Any]) -> dict[str, Any]:
    tool_name = params.get("name", "")
    arguments = params.get("arguments") or {}

    handler = _TOOL_DISPATCH.get(tool_name)
    if handler is None:
        return {
            "content": [{"type": "text", "text": f"Unknown tool: {tool_name}"}],
            "isError": True,
        }

    try:
        result = handler(arguments)
        return {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps(result, indent=2, sort_keys=True, default=str),
                },
            ],
        }
    except Exception as exc:
        tb = traceback.format_exc()
        return {
            "content": [{"type": "text", "text": f"Error in {tool_name}: {exc}\n{tb}"}],
            "isError": True,
        }


_METHOD_HANDLERS: dict[str, Any] = {
    "initialize": _handle_initialize,
    "tools/list": _handle_tools_list,
    "tools/call": _handle_tools_call,
}

# Notifications we silently acknowledge (no response required)
_NOTIFICATION_METHODS = frozenset(
    {
        "notifications/initialized",
        "notifications/cancelled",
    }
)


def handle_message(msg: dict[str, Any]) -> dict[str, Any] | None:
    """Process one JSON-RPC message and return the response (or None for notifications)."""
    method = msg.get("method", "")
    req_id = msg.get("id")
    params = msg.get("params") or {}

    # Notifications have no id — never respond.
    if req_id is None or method in _NOTIFICATION_METHODS:
        return None

    handler = _METHOD_HANDLERS.get(method)
    if handler is None:
        return _jsonrpc_error(req_id, -32601, f"Method not found: {method}")

    try:
        result = handler(params)
        return _jsonrpc_response(req_id, result)
    except Exception as exc:
        return _jsonrpc_error(req_id, -32603, str(exc))


def run_stdio() -> int:
    """Main loop: read JSON-RPC from stdin, write responses to stdout."""
    _log("koru mcp-server: started (stdio)")

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError as exc:
            err = _jsonrpc_error(None, -32700, f"Parse error: {exc}")
            _write(err)
            continue

        response = handle_message(msg)
        if response is not None:
            _write(response)

    _log("koru mcp-server: stdin closed, exiting")
    return 0


def _write(payload: dict[str, Any]) -> None:
    """Write a JSON-RPC message to stdout."""
    raw = json.dumps(payload, separators=(",", ":"), default=str)
    sys.stdout.write(raw + "\n")
    sys.stdout.flush()


def _log(msg: str) -> None:
    """Write diagnostic messages to stderr (never stdout — that's for MCP)."""
    print(msg, file=sys.stderr)


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def mcp_serve_main(argv: list[str]) -> int:
    """Entry point for ``koru mcp-serve``."""
    import argparse

    parser = argparse.ArgumentParser(
        prog="koru mcp-serve",
        description="Start the koru MCP server (stdio transport for IDE integration).",
    )
    parser.add_argument(
        "--project",
        type=Path,
        default=Path.cwd(),
        help="Project root (default: cwd).",
    )
    parser.add_argument(
        "--version",
        action="store_true",
        help="Print version and exit.",
    )
    args = parser.parse_args(argv)

    if args.version:
        print(f"koru mcp-server {_SERVER_VERSION}")
        return 0

    # Set project root in env so tool handlers can find it as fallback
    os.environ.setdefault("KORU_PROJECT_ROOT", str(args.project.resolve()))

    return run_stdio()
