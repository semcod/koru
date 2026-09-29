"""Structured classification: missing metadata never implies a simple task."""
from collections.abc import Mapping
from pathlib import PurePosixPath

from .contracts import Task, TaskClass

_SAFE_RUFF = {"F401", "F541", "I001", "UP017", "UP035"}
_COMPLEX = {"security", "governance", "architecture", "dependencies", "refactor", "cqrs"}
_COMPLEX_LEVELS = {"M", "L", "XL", "COMPLEX"}
_DOCS_KINDS = {"docs", "doc_fix", "documentation"}
_SMALL_CODING_KINDS = {"code_change", "quick_fix", "small_task", "typing_fix"}
_EXPLICIT_COMPLEX_KINDS = {"coding", "complex_refactor"}


def _mapping(value: object) -> Mapping:
    return value if isinstance(value, Mapping) else {}


def _str_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return value if all(isinstance(f, str) for f in value) else []


def _labels(value: object) -> set[str]:
    if not isinstance(value, list):
        return set()
    return {v.lower() for v in value if isinstance(v, str)}


def _routing(task: Mapping, inputs: Mapping) -> Mapping:
    context = _mapping(_mapping(task.get("source")).get("context"))
    routing = context.get("model_routing")
    return routing if isinstance(routing, Mapping) else inputs


def _complexity_level(task: Mapping, routing: Mapping) -> str:
    return str(routing.get("complexity") or task.get("complexity") or "").upper()


def _is_safe_ruff_path(name: str) -> bool:
    path = PurePosixPath(name)
    return (
        not path.is_absolute()
        and ".." not in path.parts
        and path.suffix == ".py"
        and not any(c in name for c in "*?[]\\")
    )


def _is_bounded_safe_ruff(routing: Mapping, kind: object, files: list[str]) -> bool:
    codes = routing.get("ruff_codes")
    return (
        kind == "lint_fix"
        and len(files) == 1
        and isinstance(codes, list)
        and bool(codes)
        and _is_safe_ruff_path(files[0])
        and all(isinstance(c, str) and c in _SAFE_RUFF for c in codes)
    )


def classify_task(task: Mapping | None) -> Task:
    if not isinstance(task, Mapping):
        return Task(TaskClass.OTHER, "unknown", "missing_metadata")
    inputs = _mapping(task.get("inputs"))
    routing = _routing(task, inputs)
    files = _str_list(task.get("files"))
    if (
        _labels(task.get("labels")) & _COMPLEX
        or len(files) > 2
        or _complexity_level(task, routing) in _COMPLEX_LEVELS
    ):
        return Task(TaskClass.COMPLEX, "coding", "broad_or_sensitive_scope")
    kind = routing.get("task_kind") or routing.get("llm_task_kind")
    if _is_bounded_safe_ruff(routing, kind, files):
        return Task(TaskClass.SIMPLE, "ruff", "bounded_safe_ruff")
    if kind in _DOCS_KINDS:
        return Task(TaskClass.OTHER, "docs", "explicit_documentation")
    if kind in _SMALL_CODING_KINDS and files:
        return Task(TaskClass.SIMPLE, "coding", "explicit_small_coding")
    if kind in _EXPLICIT_COMPLEX_KINDS:
        return Task(TaskClass.COMPLEX, "coding", "explicit_coding")
    return Task(TaskClass.OTHER, "unknown", "unclassified_metadata")
