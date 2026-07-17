"""Ticket parsing and command building for the planfile queue."""

import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import time
from collections.abc import Callable, Sequence
from functools import lru_cache
from importlib.util import find_spec
from pathlib import Path
from typing import Any

from koru.queue.types import CommandResult


def _explicit_queue_value(ticket: dict[str, Any]) -> str | None:
    execution = ticket.get("execution")
    if isinstance(execution, dict):
        queue = execution.get("queue")
        if queue:
            return str(queue)
    queue = ticket.get("queue_name") or ticket.get("queue")
    if queue:
        return str(queue)
    return None


def ticket_queue_name(ticket: dict[str, Any]) -> str:
    return _explicit_queue_value(ticket) or "default"


def ticket_has_explicit_queue(ticket: dict[str, Any]) -> bool:
    return _explicit_queue_value(ticket) is not None


def _source_tool(ticket: dict[str, Any]) -> str:
    source = ticket.get("source")
    if isinstance(source, dict):
        return str(source.get("tool") or "").lower()
    return str(source or "").lower()


def ticket_is_implicit_diagnostic(ticket: dict[str, Any]) -> bool:
    labels = ticket.get("labels") or []
    label_set = {str(label).lower() for label in labels if label is not None}
    title = str(ticket.get("name") or ticket.get("title") or ticket.get("description") or "")
    return (
        _source_tool(ticket) == "wup"
        or "auto-diag" in label_set
        or title.lstrip().startswith("[AUTO-DIAG]")
    )


def ticket_matches_queue(ticket: dict[str, Any], queue_name: str | None) -> bool:
    if not queue_name:
        return True
    if (
        queue_name == "default"
        and not ticket_has_explicit_queue(ticket)
        and ticket_is_implicit_diagnostic(ticket)
    ):
        return False
    return ticket_queue_name(ticket) == queue_name


def parse_next_ticket(stdout: str, *, queue_name: str | None = None) -> dict | None:
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
        return payload if ticket_matches_queue(payload, queue_name) else None
    if isinstance(payload, list):
        # planfile ticket list returns oldest-first; sort by priority
        # then treat the first entry whose status is open / ready / todo as runnable.
        runnable_states = {None, "open", "ready", "todo"}
        priority_order = {"critical": 0, "high": 1, "normal": 2, "low": 3}

        # Filter runnable tickets first
        runnable_tickets = [
            entry
            for entry in payload
            if isinstance(entry, dict)
            and entry.get("status") in runnable_states
            and ticket_matches_queue(entry, queue_name)
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

    Context fields (all optional):
      include_project_context – when truthy, auto-include file tree and
        common project files (Dockerfile, README, koru.yaml, …).
      context_files           – explicit list of file paths relative to the
        project root to include verbatim.
      context_globs           – glob patterns relative to the project root.
      max_context_chars       – hard cap on assembled context size
        (default 32 000 characters).
    """
    inputs = ticket.get("inputs") or {}
    executor = ticket.get("executor") or {}
    prompt = inputs.get("prompt") or ticket.get("description") or ticket.get("name")
    if not prompt:
        return None
    request: dict[str, Any] = {
        "endpoint": inputs.get("llm_endpoint") or executor.get("handler"),
        "model": inputs.get("llm_model"),
        "prompt": str(prompt),
        "system_prompt": inputs.get("system_prompt"),
        "max_tokens": inputs.get("llm_max_tokens"),
        "temperature": inputs.get("llm_temperature", 0.0),
        "response_schema": inputs.get("response_schema"),
        "timeout_seconds": inputs.get("llm_timeout_seconds") or 60.0,
    }
    # Context assembly inputs — passed through for the runner to act on.
    if inputs.get("include_project_context"):
        request["include_project_context"] = True
    if inputs.get("context_files"):
        request["context_files"] = list(inputs["context_files"])
    if inputs.get("context_globs"):
        request["context_globs"] = list(inputs["context_globs"])
    if inputs.get("max_context_chars") is not None:
        request["max_context_chars"] = int(inputs["max_context_chars"])
    # ticket.files — files listed on the ticket itself are passed for context
    ticket_files = ticket.get("files")
    if ticket_files:
        request["ticket_files"] = list(ticket_files)
    return request


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


def _python_has_planfile_cli(python: str) -> bool:
    try:
        proc = subprocess.run(
            [
                python,
                "-c",
                (
                    "import importlib.util, sys; "
                    "sys.exit(0 if importlib.util.find_spec('planfile.cli') else 1)"
                ),
            ],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return proc.returncode == 0


def _module_cli_command_for_project(project: Path) -> list[str] | None:
    """Prefer the project venv Python for planfile before the active interpreter."""
    from koru.utils.subprocess_runner import get_python_cmd

    for python in get_python_cmd(project):
        if _python_has_planfile_cli(python):
            return [python, "-m", "planfile.cli"]
    if _has_planfile_cli_module():
        return [sys.executable, "-m", "planfile.cli"]
    return None


_MIN_STRUCTURED_QUEUE_PLANFILE_VERSION = (0, 1, 100)
_PLANFILE_LOCK_RETRY_ATTEMPTS = 3
_PLANFILE_LOCK_RETRY_SLEEP_SECONDS = 0.25


def _parse_version_tuple(text: str) -> tuple[int, int, int] | None:
    match = re.search(r"(\d+)\.(\d+)\.(\d+)", text)
    if not match:
        return None
    return tuple(int(part) for part in match.groups())


@lru_cache(maxsize=32)
def _planfile_supports_structured_queue_json(executable: str) -> bool:
    try:
        result = subprocess.run(
            [executable, "--version"],
            check=False,
            capture_output=True,
            text=True,
            timeout=2,
        )
    except (OSError, subprocess.SubprocessError):
        return True
    version = _parse_version_tuple(f"{result.stdout}\n{result.stderr}")
    if version is None:
        return True
    return version >= _MIN_STRUCTURED_QUEUE_PLANFILE_VERSION


def _planfile_executable_candidates(project: Path) -> tuple[Path, ...]:
    project = project.resolve()
    candidates = [
        project.parent / "planfile" / ".venv" / "bin" / "planfile",
        project.parent / "planfile" / "venv" / "bin" / "planfile",
        project / ".venv" / "bin" / "planfile",
        project / "venv" / "bin" / "planfile",
    ]
    for root in _source_planfile_search_roots():
        candidates.extend(
            [
                root / "planfile" / ".venv" / "bin" / "planfile",
                root / "planfile" / "venv" / "bin" / "planfile",
            ]
        )

    deduped: list[Path] = []
    seen: set[str] = set()
    for candidate in candidates:
        key = str(candidate)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(candidate)
    return tuple(deduped)


def _source_planfile_search_roots() -> tuple[Path, ...]:
    return tuple(Path(__file__).resolve().parents)


def _local_planfile_executable(project: Path) -> Path | None:
    """Return a nearby Planfile CLI before falling back to an unrelated active venv."""
    for candidate in _planfile_executable_candidates(project):
        if (
            candidate.is_file()
            and os.access(candidate, os.X_OK)
            and _planfile_supports_structured_queue_json(str(candidate))
        ):
            return candidate
    return None


_PLANFILE_MODULE_MISSING_MARKERS = (
    "no module named 'planfile",
    "error while finding module specification for 'planfile",
)


def planfile_module_missing(text: str) -> bool:
    """True when command output carries the planfile module-missing signature."""
    lowered = text.lower()
    return any(marker in lowered for marker in _PLANFILE_MODULE_MISSING_MARKERS)


@lru_cache(maxsize=8)
def _configured_planfile_cmd_usable(configured: str) -> bool:
    """Cheaply verify a pinned ``KORU_PLANFILE_CMD`` can actually run.

    A pinned command like ``.venv/bin/python -m planfile.cli`` silently breaks
    the whole queue when planfile is not installed in that env. Only that
    specific module-missing signature bypasses the operator's pin — any other
    state (including a probe we cannot run) keeps the pin authoritative;
    ``koru doctor`` reports non-executable pins separately.
    """
    parts = shlex.split(configured)
    if not parts:
        return True
    try:
        proc = subprocess.run(
            [*parts, "--version"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return True
    if proc.returncode == 0:
        return True
    text = f"{proc.stdout}\n{proc.stderr}".lower()
    return not any(marker in text for marker in _PLANFILE_MODULE_MISSING_MARKERS)


_warned_planfile_cmd_fallbacks: set[str] = set()


def _warn_planfile_cmd_fallback_once(configured: str) -> None:
    if configured in _warned_planfile_cmd_fallbacks:
        return
    _warned_planfile_cmd_fallbacks.add(configured)
    print(
        f"[koru] KORU_PLANFILE_CMD={configured!r} cannot run planfile "
        "(module missing in that environment); falling back to auto-resolution. "
        "Install planfile into that env or unset KORU_PLANFILE_CMD.",
        file=sys.stderr,
    )


def resolve_planfile_base_command(project: Path) -> list[str]:
    """Resolve the Planfile command Koru should use for a project."""
    configured = os.getenv("KORU_PLANFILE_CMD")
    if configured:
        if _configured_planfile_cmd_usable(configured):
            return shlex.split(configured)
        _warn_planfile_cmd_fallback_once(configured)
    if local_planfile := _local_planfile_executable(project):
        return [str(local_planfile)]
    if module_cmd := _module_cli_command_for_project(project):
        return module_cmd
    if path_planfile := shutil.which("planfile"):
        if _planfile_supports_structured_queue_json(path_planfile):
            return [path_planfile]
    return ["planfile"]


def _planfile_lock_timeout(result: CommandResult) -> bool:
    if result.returncode == 0:
        return False
    stdout = getattr(result, "stdout", "") or ""
    stderr = getattr(result, "stderr", "") or ""
    text = f"{stdout}\n{stderr}".lower()
    return (
        "file lock" in text
        and "could not be acquired" in text
        or "timeout:" in text
        and ".lock" in text
        and "could not be acquired" in text
    )


def planfile_command(
    project: Path,
    args: Sequence[str],
    runner: Callable[[Sequence[str], Path], CommandResult],
) -> CommandResult:
    """Execute a planfile CLI command."""
    command = [*resolve_planfile_base_command(project), *args]
    result = runner(command, project)
    for attempt in range(1, _PLANFILE_LOCK_RETRY_ATTEMPTS):
        if not _planfile_lock_timeout(result):
            return result
        time.sleep(_PLANFILE_LOCK_RETRY_SLEEP_SECONDS * attempt)
        result = runner(command, project)
    return result


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
