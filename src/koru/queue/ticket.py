"""Ticket parsing and command building for the planfile queue."""


import json
import os
import shlex
import shutil
import sys
from collections.abc import Callable, Sequence
from importlib.util import find_spec
from pathlib import Path
from typing import Any

from koru.queue.types import CommandResult


def parse_next_ticket(stdout: str) -> dict | None:
    """Pick the first runnable ticket from planfile output.

    Accepts both a single-object payload (legacy ``ticket next``) and
    an array (``ticket list --format json``). Returns ``None`` when the
    queue is idle.
    """
    stripped = stdout.strip()
    if not stripped or "No runnable ticket found" in stripped:
        return None
    try:
        payload = json.loads(stripped)
    except json.JSONDecodeError:
        payload = json.loads(stripped, strict=False)
    if isinstance(payload, dict):
        return payload
    if isinstance(payload, list):
        # planfile ticket list returns oldest-first; sort by priority
        # then treat the first entry whose status is open / ready / todo as runnable.
        runnable_states = {None, "open", "ready", "todo"}
        priority_order = {"critical": 0, "high": 1, "normal": 2, "low": 3}

        # Filter runnable tickets first
        runnable_tickets = [
            entry
            for entry in payload
            if isinstance(entry, dict) and entry.get("status") in runnable_states
        ]

        if not runnable_tickets:
            return None

        # Sort by priority (critical first), then by creation date as tiebreaker
        runnable_tickets.sort(
            key=lambda t: (
                priority_order.get(t.get("priority", "normal"), 2),
                t.get("created_at", ""),
            ),
        )

        return runnable_tickets[0]
    return None


def ticket_command(ticket: dict) -> str | None:
    """Extract the command/script from a ticket."""
    inputs = ticket.get("inputs") or {}
    executor = ticket.get("executor") or {}
    return inputs.get("script") or executor.get("handler")


def ticket_llm_request(ticket: dict) -> dict[str, Any] | None:
    """Translate an executor.kind=llm ticket into an LLM HTTP call spec.

    Returns None when the ticket lacks the minimum signal (a prompt to
    send), so the caller can fall back to ``planfile ticket block``
    with a ``--reason`` describing the missing input.
    """
    inputs = ticket.get("inputs") or {}
    executor = ticket.get("executor") or {}
    prompt = inputs.get("prompt") or ticket.get("description") or ticket.get("name")
    if not prompt:
        return None
    return {
        "endpoint": inputs.get("llm_endpoint") or executor.get("handler"),
        "model": inputs.get("llm_model"),
        "prompt": str(prompt),
        "system_prompt": inputs.get("system_prompt"),
        "max_tokens": inputs.get("llm_max_tokens"),
        "temperature": inputs.get("llm_temperature", 0.0),
        "response_schema": inputs.get("response_schema"),
        "timeout_seconds": inputs.get("llm_timeout_seconds") or 60.0,
    }


def ticket_api_request(ticket: dict) -> dict[str, Any] | None:
    """Translate an executor.kind=api ticket into an HTTP call spec."""
    inputs = ticket.get("inputs") or {}
    executor = ticket.get("executor") or {}
    endpoint = inputs.get("api_endpoint") or executor.get("handler")
    if not endpoint:
        return None

    return {
        "endpoint": endpoint,
        "method": inputs.get("api_method") or "GET",
        "headers": inputs.get("api_headers") or {},
        "body": inputs.get("api_body"),
        "timeout_seconds": inputs.get("api_timeout_seconds") or 30.0,
    }


def _has_planfile_cli_module() -> bool:
    try:
        return find_spec("planfile.cli") is not None
    except ModuleNotFoundError:
        return False


def _local_planfile_executable(project: Path) -> Path | None:
    """Return a nearby Planfile CLI before falling back to an unrelated active venv."""
    project = project.resolve()
    candidates = (
        project.parent / "planfile" / ".venv" / "bin" / "planfile",
        project.parent / "planfile" / "venv" / "bin" / "planfile",
        project / ".venv" / "bin" / "planfile",
        project / "venv" / "bin" / "planfile",
    )
    for candidate in candidates:
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return candidate
    return None


def planfile_command(
    project: Path,
    args: Sequence[str],
    runner: Callable[[Sequence[str], Path], CommandResult],
) -> CommandResult:
    """Execute a planfile CLI command."""
    configured = os.getenv("KORU_PLANFILE_CMD")
    if configured:
        base_command = shlex.split(configured)
    elif local_planfile := _local_planfile_executable(project):
        base_command = [str(local_planfile)]
    elif _has_planfile_cli_module():
        base_command = [sys.executable, "-m", "planfile.cli"]
    elif shutil.which("planfile"):
        base_command = ["planfile"]
    else:
        base_command = ["planfile"]
    return runner([*base_command, *args], project)


def result_json(result: CommandResult) -> str:
    """Convert a CommandResult to JSON for logging."""
    payload: dict[str, Any] = {
        "exit_code": result.returncode,
        "stdout": result.stdout[-4000:],
        "stderr": result.stderr[-4000:],
    }
    if hasattr(result, "status_code"):
        payload["status_code"] = result.status_code  # type: ignore[attr-defined]
    if hasattr(result, "model"):
        payload["llm_model"] = result.model  # type: ignore[attr-defined]
    if hasattr(result, "usage"):
        payload["llm_usage"] = result.usage  # type: ignore[attr-defined]
    return json.dumps(payload)
