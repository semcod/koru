"""Minimal planfile-backed queue runner for koru."""

from __future__ import annotations

import json
import os
import shlex
import subprocess
import sys
import urllib.error
import urllib.request
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from importlib.util import find_spec
from pathlib import Path
from typing import Any, Protocol


class CommandResult(Protocol):
    """Protocol for subprocess-like command results."""

    returncode: int
    stdout: str
    stderr: str


@dataclass(frozen=True)
class QueueRunResult:
    """Result of a single queue tick."""

    status: str
    ticket_id: str | None = None
    executor_kind: str | None = None
    message: str = ""
    exit_code: int | None = None
    stdout: str = ""
    stderr: str = ""


@dataclass(frozen=True)
class ApiRunResult:
    """Result of a direct HTTP API executor call."""

    returncode: int
    stdout: str
    stderr: str
    status_code: int
    headers: dict[str, str]


def _planfile_env() -> dict[str, str]:
    """Force a wide, non-TTY console so planfile's Rich output stays one
    JSON object per line. Without this, long handler strings get wrapped
    by Rich and break json.loads on the koru side."""
    return {**os.environ, "COLUMNS": "10000", "TERM": "dumb"}


def _run_process(command: Sequence[str], project: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=project,
        text=True,
        capture_output=True,
        check=False,
        env=_planfile_env(),
    )


def _run_shell_command(command: str, project: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=project,
        shell=True,
        text=True,
        capture_output=True,
        check=False,
    )


def _run_api_request(request: dict[str, Any], _project: Path) -> ApiRunResult:
    body = request.get("body")
    data: bytes | None = None
    headers = {str(k): str(v) for k, v in (request.get("headers") or {}).items()}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers.setdefault("content-type", "application/json")

    api_request = urllib.request.Request(
        str(request["endpoint"]),
        data=data,
        headers=headers,
        method=str(request.get("method") or "GET").upper(),
    )
    timeout = float(request.get("timeout_seconds") or 30.0)

    try:
        with urllib.request.urlopen(api_request, timeout=timeout) as response:
            text = response.read().decode("utf-8", errors="replace")
            return ApiRunResult(
                returncode=0,
                stdout=text,
                stderr="",
                status_code=int(response.status),
                headers=dict(response.headers.items()),
            )
    except urllib.error.HTTPError as exc:
        text = exc.read().decode("utf-8", errors="replace")
        return ApiRunResult(
            returncode=1,
            stdout=text,
            stderr=f"HTTP {exc.code}",
            status_code=int(exc.code),
            headers=dict(exc.headers.items()),
        )
    except urllib.error.URLError as exc:
        return ApiRunResult(
            returncode=1,
            stdout="",
            stderr=str(exc.reason),
            status_code=0,
            headers={},
        )


def _planfile_command(
    project: Path,
    args: Sequence[str],
    runner: Callable[[Sequence[str], Path], CommandResult] = _run_process,
) -> CommandResult:
    configured = os.getenv("KORU_PLANFILE_CMD")
    if configured:
        base_command = shlex.split(configured)
    elif find_spec("planfile") is not None:
        base_command = [sys.executable, "-m", "planfile.cli"]
    else:
        base_command = ["planfile"]
    return runner([*base_command, *args], project)


def _parse_next_ticket(stdout: str) -> dict | None:
    stripped = stdout.strip()
    if not stripped or "No runnable ticket found" in stripped:
        return None
    return json.loads(stripped)


def _ticket_command(ticket: dict) -> str | None:
    inputs = ticket.get("inputs") or {}
    executor = ticket.get("executor") or {}
    return inputs.get("script") or executor.get("handler")


def _ticket_api_request(ticket: dict) -> dict[str, Any] | None:
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


def _result_json(result: CommandResult) -> str:
    payload = {
        "exit_code": result.returncode,
        "stdout": result.stdout[-4000:],
        "stderr": result.stderr[-4000:],
    }
    if hasattr(result, "status_code"):
        payload["status_code"] = result.status_code  # type: ignore[attr-defined]
    return json.dumps(payload)


def run_next_planfile_task(
    *,
    project: Path,
    actor: str = "koru-shell",
    dry_run: bool = False,
    queue_name: str | None = None,
    planfile_runner: Callable[[Sequence[str], Path], CommandResult] = _run_process,
    shell_runner: Callable[[str, Path], CommandResult] = _run_shell_command,
    api_runner: Callable[[dict[str, Any], Path], CommandResult] = _run_api_request,
) -> QueueRunResult:
    """Execute one runnable planfile ticket, if any."""
    project = project.resolve()
    next_args = ["ticket", "next", "--format", "json"]
    if queue_name:
        next_args.extend(["--queue", queue_name])
    next_result = _planfile_command(
        project,
        next_args,
        runner=planfile_runner,
    )
    if next_result.returncode != 0:
        return QueueRunResult(
            status="planfile_error",
            message="planfile ticket next failed",
            exit_code=next_result.returncode,
            stdout=next_result.stdout,
            stderr=next_result.stderr,
        )

    ticket = _parse_next_ticket(next_result.stdout)
    if ticket is None:
        return QueueRunResult(status="idle", message="No runnable ticket found")

    ticket_id = str(ticket["id"])
    executor = ticket.get("executor") or {}
    executor_kind = str(executor.get("kind") or "human")

    if executor_kind == "human":
        inputs = ticket.get("inputs") or {}
        prompt = (
            inputs.get("prompt")
            or ticket.get("description")
            or ticket.get("name")
            or ticket_id
        )
        return QueueRunResult(
            status="waiting_input",
            ticket_id=ticket_id,
            executor_kind=executor_kind,
            message=str(prompt),
        )

    if executor_kind not in {"api", "shell"}:
        return QueueRunResult(
            status="unsupported_executor",
            ticket_id=ticket_id,
            executor_kind=executor_kind,
            message=f"Executor kind '{executor_kind}' is not implemented yet",
        )

    if executor_kind == "api":
        action = _ticket_api_request(ticket)
        missing_prompt = "API ticket is missing inputs.api_endpoint or executor.handler"
    else:
        action = _ticket_command(ticket)
        missing_prompt = "Shell ticket is missing inputs.script or executor.handler"

    if not action:
        _planfile_command(
            project,
            ["ticket", "input", ticket_id, "--prompt", missing_prompt],
            runner=planfile_runner,
        )
        return QueueRunResult(
            status="waiting_input",
            ticket_id=ticket_id,
            executor_kind=executor_kind,
            message=missing_prompt,
        )

    if dry_run:
        message = json.dumps(action) if isinstance(action, dict) else action
        return QueueRunResult(
            status="dry_run",
            ticket_id=ticket_id,
            executor_kind=executor_kind,
            message=message,
        )

    _planfile_command(
        project,
        ["ticket", "claim", ticket_id, "--assigned-to", actor],
        runner=planfile_runner,
    )
    _planfile_command(
        project,
        ["ticket", "start", ticket_id, "--assigned-to", actor],
        runner=planfile_runner,
    )

    if executor_kind == "api":
        result = api_runner(action, project)
        action_label = f"{action['method']} {action['endpoint']}"
    else:
        result = shell_runner(str(action), project)
        action_label = str(action)

    if result.returncode == 0:
        _planfile_command(
            project,
            [
                "ticket",
                "complete",
                ticket_id,
                "--note",
                f"Executed by {actor}: {action_label}",
                "--result-json",
                _result_json(result),
            ],
            runner=planfile_runner,
        )
        status = "completed"
    else:
        _planfile_command(
            project,
            [
                "ticket",
                "fail",
                ticket_id,
                "--error",
                result.stderr[-1000:] or f"Command exited with {result.returncode}",
            ],
            runner=planfile_runner,
        )
        status = "failed"

    return QueueRunResult(
        status=status,
        ticket_id=ticket_id,
        executor_kind=executor_kind,
        message=action_label,
        exit_code=result.returncode,
        stdout=result.stdout,
        stderr=result.stderr,
    )
