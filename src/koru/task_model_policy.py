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


def select_task_model(
    task: Mapping[str, Any] | None,
    *,
    client_id: str,
    default_model: str = "",
    explicit_model: str = "",
    environ: Mapping[str, str] | None = None,
) -> dict[str, str]:
    env = os.environ if environ is None else environ
    task = task if isinstance(task, Mapping) else {}
    inputs = task.get("inputs")
    inputs = inputs if isinstance(inputs, Mapping) else {}
    model = explicit_model or str(inputs.get("llm_model") or "")
    reason = "explicit_request"
    if not model:
        model = env.get("KORU_TILLM_FORCE_MODEL", "").strip()
        reason = "operator_pin"
    if model:
        return {"model": model, "reason": reason}
    default = default_model or env.get("KORU_TILLM_MODEL", "").strip()
    simple = env.get("KORU_TILLM_SIMPLE_MODEL", "").strip()
    reason = "simple_model_disabled" if not simple else "unclassified_task"
    files = task.get("files")
    codes = inputs.get("ruff_codes")
    labels = task.get("labels")
    valid_labels = labels is None or (isinstance(labels, list) and all(isinstance(x, str) for x in labels))
    labels = set(labels or []) if valid_labels else set()
    # Smallness is a closed, structured contract, not a guess from prompt/title.
    if simple and client_id == "opencode" and inputs.get("llm_task_kind") == "lint_fix":
        reason = "unbounded_lint_scope"
        if isinstance(files, list) and len(files) == 1 and isinstance(files[0], str):
            path = PurePosixPath(files[0])
            bounded = (
                not path.is_absolute()
                and ".." not in path.parts
                and "\\" not in files[0]
                and not any(c in files[0] for c in "*?[]")
                and path.suffix == ".py"
                and path.parts[0] in {"src", "tests", "test"}
                and valid_labels
                and not labels.intersection(_COMPLEX_LABELS)
                and isinstance(codes, list)
                and 0 < len(codes) <= 10
                and all(isinstance(code, str) and code in _LINT_CODES for code in codes)
            )
            if bounded:
                return {"model": simple, "reason": "bounded_lint"}
    return {"model": default, "reason": reason}


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
