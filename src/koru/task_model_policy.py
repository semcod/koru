"""Bounded task-based CLI model selection; never an execution permission."""

from __future__ import annotations

import json
import os
import re
import subprocess
import time
import uuid
from collections.abc import Callable, Mapping
from pathlib import Path, PurePosixPath
from typing import Any

_LINT_CODES = frozenset({"F401", "F541", "I001", "UP017", "UP035"})
_COMPLEX_LABELS = frozenset({"refactor", "code2llm", "security", "governance", "dependencies"})
_IDENTIFIER = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/-]{0,159}\Z")


def safe_identifier(value: object) -> str:
    return value if isinstance(value, str) and _IDENTIFIER.fullmatch(value) else ""


def _resolve_explicit_or_pinned_model(
    explicit_model: str,
    inputs: Mapping[str, Any],
    env: Mapping[str, str],
) -> tuple[str, str] | None:
    model = explicit_model or str(inputs.get("llm_model") or "")
    if model:
        return model, "explicit_request"
    pinned = env.get("KORU_TILLM_FORCE_MODEL", "").strip()
    if pinned:
        return pinned, "operator_pin"
    return None


def _resolve_routing_mapping(
    task: Mapping[str, Any],
    inputs: Mapping[str, Any],
) -> Mapping[str, Any]:
    source = task.get("source")
    context = source.get("context") if isinstance(source, Mapping) else None
    routing = context.get("model_routing") if isinstance(context, Mapping) else None
    return routing if isinstance(routing, Mapping) else inputs


def _is_valid_file_target(file_path: object) -> bool:
    if not isinstance(file_path, str):
        return False
    if "\\" in file_path or any(c in file_path for c in "*?[]"):
        return False
    path = PurePosixPath(file_path)
    return (
        not path.is_absolute()
        and ".." not in path.parts
        and path.suffix == ".py"
        and bool(path.parts)
        and path.parts[0] in {"src", "tests", "test"}
    )


def _is_valid_labels(raw_labels: object) -> tuple[bool, set[str]]:
    if raw_labels is None:
        return True, set()
    if isinstance(raw_labels, list) and all(isinstance(x, str) for x in raw_labels):
        return True, set(raw_labels)
    return False, set()


def _is_bounded_ruff_codes(codes: object) -> bool:
    return (
        isinstance(codes, list)
        and 0 < len(codes) <= 10
        and all(isinstance(code, str) and code in _LINT_CODES for code in codes)
    )


def _is_bounded_lint_fix(
    task: Mapping[str, Any],
    routing: Mapping[str, Any],
) -> bool:
    files = task.get("files")
    if not (isinstance(files, list) and len(files) == 1):
        return False
    if not _is_valid_file_target(files[0]):
        return False
    valid_labels, labels = _is_valid_labels(task.get("labels"))
    if not valid_labels or labels.intersection(_COMPLEX_LABELS):
        return False
    return _is_bounded_ruff_codes(routing.get("ruff_codes"))


def select_task_model(
    task: Mapping[str, Any] | None,
    *,
    client_id: str,
    default_model: str = "",
    explicit_model: str = "",
    environ: Mapping[str, str] | None = None,
) -> dict[str, str]:
    env = os.environ if environ is None else environ
    task_map = task if isinstance(task, Mapping) else {}
    inputs = task_map.get("inputs")
    inputs_map = inputs if isinstance(inputs, Mapping) else {}

    forced = _resolve_explicit_or_pinned_model(explicit_model, inputs_map, env)
    if forced is not None:
        model, reason = forced
        return {"model": model, "reason": reason}

    default = default_model or env.get("KORU_TILLM_MODEL", "").strip()
    simple = env.get("KORU_TILLM_SIMPLE_MODEL", "").strip()
    if not simple:
        return {"model": default, "reason": "simple_model_disabled"}

    routing = _resolve_routing_mapping(task_map, inputs_map)
    if client_id == "opencode" and routing.get("llm_task_kind") == "lint_fix":
        if _is_bounded_lint_fix(task_map, routing):
            return {"model": simple, "reason": "bounded_lint"}
        return {"model": default, "reason": "unbounded_lint_scope"}

    return {"model": default, "reason": "unclassified_task"}


def load_routing_task(project: Path, ticket_id: str) -> dict[str, Any]:
    """Missing metadata keeps the regular model. This query never creates tickets."""
    if not safe_identifier(ticket_id) or ticket_id.startswith("-"):
        return {}
    from koru.queue.ticket import resolve_planfile_base_command

    try:
        result = subprocess.run(
            [*resolve_planfile_base_command(project), "ticket", "show", ticket_id, "--format", "json"],
            cwd=project,
            capture_output=True,
            text=True,
            timeout=8,
            check=False,
        )
        task = json.loads(result.stdout) if result.returncode == 0 else {}
        return task if isinstance(task, dict) and task.get("id") == ticket_id else {}
    except (OSError, ValueError, subprocess.TimeoutExpired):
        return {}


def drive_with_model_policy(
    drive: Callable[..., dict[str, Any]],
    *,
    task: Mapping[str, Any] | None = None,
    explicit_model: str = "",
    **kwargs: Any,
) -> dict[str, Any]:
    from koru.model_history import append_routing_event

    task = task if isinstance(task, Mapping) else {}
    decision = select_task_model(
        task,
        client_id=kwargs["client_id"],
        default_model=kwargs.get("model") or "",
        explicit_model=explicit_model,
    )
    kwargs["model"] = decision["model"] or None
    receipt = {
        "request_id": uuid.uuid4().hex,
        "ticket": safe_identifier((task or {}).get("id")),
        "client": safe_identifier(kwargs["client_id"]),
        "requested_model": safe_identifier(decision["model"]),
        "reason": decision["reason"],
    }
    project = kwargs["project"]
    recorded = append_routing_event(project, {**receipt, "status": "started"})
    started = time.monotonic()
    try:
        reply = drive(**kwargs)
    except Exception:
        append_routing_event(
            project, {**receipt, "status": "error", "duration_ms": round((time.monotonic() - started) * 1000)}
        )
        raise
    finished = append_routing_event(
        project,
        {
            **receipt,
            "status": "cli_success" if reply.get("ok") and reply.get("exit_code", 0) == 0 else "error",
            "duration_ms": round((time.monotonic() - started) * 1000),
        },
    )
    return {**reply, "model_routing": {**receipt, "recorded": recorded and finished}}
