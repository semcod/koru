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
from typing import Any, NamedTuple

_LINT_CODES = frozenset({"F401", "F541", "I001", "UP017", "UP035"})
_COMPLEX_LABELS = frozenset({"refactor", "code2llm", "security", "governance", "dependencies"})
_IDENTIFIER = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/-]{0,159}\Z")


def safe_identifier(value: object) -> str:
    return value if isinstance(value, str) and _IDENTIFIER.fullmatch(value) else ""


class _ForcedModel(NamedTuple):
    model: str
    reason: str


class _TaskView(NamedTuple):
    task: Mapping[str, Any]
    inputs: Mapping[str, Any]


class _LabelsCheck(NamedTuple):
    valid: bool
    labels: set[str]


def _coerce_task(task: object) -> _TaskView:
    task_map = task if isinstance(task, Mapping) else {}
    inputs = task_map.get("inputs")
    return _TaskView(task_map, inputs if isinstance(inputs, Mapping) else {})


def _resolve_explicit_or_pinned_model(
    explicit_model: str,
    inputs: Mapping[str, Any],
    env: Mapping[str, str],
) -> _ForcedModel | None:
    model = explicit_model or str(inputs.get("llm_model") or "")
    if model:
        return _ForcedModel(model, "explicit_request")
    pinned = env.get("KORU_TILLM_FORCE_MODEL", "").strip()
    if pinned:
        return _ForcedModel(pinned, "operator_pin")
    return None


def _resolve_routing_mapping(
    task: Mapping[str, Any],
    inputs: Mapping[str, Any],
) -> Mapping[str, Any]:
    source = task.get("source")
    context = source.get("context") if isinstance(source, Mapping) else None
    routing = context.get("model_routing") if isinstance(context, Mapping) else None
    return routing if isinstance(routing, Mapping) else inputs


def _is_plain_python_path(file_path: str) -> bool:
    return "\\" not in file_path and not any(c in file_path for c in "*?[]")


def _is_safe_relative_py_path(path: PurePosixPath) -> bool:
    return (
        not path.is_absolute()
        and ".." not in path.parts
        and path.suffix == ".py"
        and bool(path.parts)
        and path.parts[0] in {"src", "tests", "test"}
    )


def _is_valid_file_target(file_path: object) -> bool:
    if not isinstance(file_path, str) or not _is_plain_python_path(file_path):
        return False
    return _is_safe_relative_py_path(PurePosixPath(file_path))


def _is_valid_labels(raw_labels: object) -> _LabelsCheck:
    if raw_labels is None:
        return _LabelsCheck(True, set())
    if isinstance(raw_labels, list) and all(isinstance(x, str) for x in raw_labels):
        return _LabelsCheck(True, set(raw_labels))
    return _LabelsCheck(False, set())


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
    labels = _is_valid_labels(task.get("labels"))
    if not labels.valid or labels.labels.intersection(_COMPLEX_LABELS):
        return False
    return _is_bounded_ruff_codes(routing.get("ruff_codes"))


def _is_lint_fix_request(client_id: str, routing: Mapping[str, Any]) -> bool:
    return client_id == "opencode" and routing.get("llm_task_kind") == "lint_fix"


def _fallback_reason(simple: str, client_id: str, routing: Mapping[str, Any]) -> str:
    if not simple:
        return "simple_model_disabled"
    if _is_lint_fix_request(client_id, routing):
        return "unbounded_lint_scope"
    return "unclassified_task"


def _select_fallback_model(
    view: _TaskView,
    *,
    client_id: str,
    default_model: str,
    env: Mapping[str, str],
) -> dict[str, str]:
    default = default_model or env.get("KORU_TILLM_MODEL", "").strip()
    simple = env.get("KORU_TILLM_SIMPLE_MODEL", "").strip()
    routing = _resolve_routing_mapping(view.task, view.inputs)
    # Smallness is a closed, structured contract, not a guess from prompt/title.
    if simple and _is_lint_fix_request(client_id, routing) and _is_bounded_lint_fix(view.task, routing):
        return {"model": simple, "reason": "bounded_lint"}
    return {"model": default, "reason": _fallback_reason(simple, client_id, routing)}


def select_task_model(
    task: Mapping[str, Any] | None,
    *,
    client_id: str,
    default_model: str = "",
    explicit_model: str = "",
    environ: Mapping[str, str] | None = None,
) -> dict[str, str]:
    """Resolve the CLI model for a task; never an execution permission.

    Precedence: explicit request or ticket ``inputs.llm_model``, then the
    operator pin ``KORU_TILLM_FORCE_MODEL``, then the simple model for a
    bounded single-file lint fix (opencode only), then the default model.
    The returned ``reason`` names the branch that produced the decision.
    """
    env = os.environ if environ is None else environ
    view = _coerce_task(task)
    forced = _resolve_explicit_or_pinned_model(explicit_model, view.inputs, env)
    if forced is not None:
        return {"model": forced.model, "reason": forced.reason}
    return _select_fallback_model(view, client_id=client_id, default_model=default_model, env=env)


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
