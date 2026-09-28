"""Structured classification: missing metadata never implies a simple task."""
from collections.abc import Mapping
from pathlib import PurePosixPath

from .contracts import Task, TaskClass

_SAFE_RUFF = {"F401", "F541", "I001", "UP017", "UP035"}
_COMPLEX = {"security", "governance", "architecture", "dependencies", "refactor", "cqrs"}


def classify_task(task: Mapping | None) -> Task:
    if not isinstance(task, Mapping):
        return Task(TaskClass.OTHER, "unknown", "missing_metadata")
    inputs = task.get("inputs")
    inputs = inputs if isinstance(inputs, Mapping) else {}
    source = task.get("source")
    context = source.get("context") if isinstance(source, Mapping) else None
    routing = context.get("model_routing") if isinstance(context, Mapping) else None
    routing = routing if isinstance(routing, Mapping) else inputs
    files = task.get("files")
    files = files if isinstance(files, list) and all(isinstance(f, str) for f in files) else []
    labels = task.get("labels")
    labels = {v.lower() for v in labels if isinstance(v, str)} if isinstance(labels, list) else set()
    kind = routing.get("task_kind") or routing.get("llm_task_kind")
    complexity = str(routing.get("complexity") or task.get("complexity") or "").upper()
    if labels & _COMPLEX or len(files) > 2 or complexity in {"M", "L", "XL", "COMPLEX"}:
        return Task(TaskClass.COMPLEX, "coding", "broad_or_sensitive_scope")
    codes = routing.get("ruff_codes")
    if kind == "lint_fix" and len(files) == 1 and isinstance(codes, list) and codes:
        path = PurePosixPath(files[0])
        if (not path.is_absolute() and ".." not in path.parts and path.suffix == ".py"
                and not any(c in files[0] for c in "*?[]\\")
                and all(isinstance(c, str) and c in _SAFE_RUFF for c in codes)):
            return Task(TaskClass.SIMPLE, "ruff", "bounded_safe_ruff")
    if kind in {"docs", "doc_fix", "documentation"}:
        return Task(TaskClass.OTHER, "docs", "explicit_documentation")
    if kind in {"code_change", "quick_fix", "small_task", "typing_fix"} and files:
        return Task(TaskClass.SIMPLE, "coding", "explicit_small_coding")
    if kind in {"coding", "complex_refactor"}:
        return Task(TaskClass.COMPLEX, "coding", "explicit_coding")
    return Task(TaskClass.OTHER, "unknown", "unclassified_metadata")
