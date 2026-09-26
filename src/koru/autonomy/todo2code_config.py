"""Environment and ``.env`` knobs for ``todo2code`` discovery.

Every ``KORU_TODO2CODE_*`` knob is read from ``os.environ`` first, then the
target project's ``.env`` (via :func:`koru.queue.todo2code_support.config_value`).
This module owns knob parsing, the enable flag, output-directory containment
and the discovery limit resolution (artifact age, ticket cap, usefulness
threshold) shared by the ``todo2code`` pipeline modules.
"""

from __future__ import annotations

from pathlib import Path

from koru.queue.todo2code_support import config_value as _config_value

DEFAULT_SOURCE = "koru-todo2code-discovery"
DEFAULT_OUT_SUBDIR = ".intent"
DEFAULT_MAX_TICKETS = 10
DEFAULT_STALE_MINUTES = 60.0
DEFAULT_TIMEOUT_SECONDS = 900.0
DEFAULT_MIN_USEFULNESS = 8.0


def _env_flag(name: str, default: bool, project: Path | None = None) -> bool:
    raw = _config_value(name, project).lower()
    if not raw:
        return default
    return raw in {"1", "true", "yes", "on"}


def _env_float(name: str, default: float, project: Path | None = None) -> float:
    try:
        return float(_config_value(name, project) or default)
    except (TypeError, ValueError):
        return default


def _env_int(name: str, default: int, project: Path | None = None) -> int:
    try:
        return int(_config_value(name, project) or default)
    except (TypeError, ValueError):
        return default


def todo2code_enabled(project: Path | None = None) -> bool:
    return _env_flag("KORU_TODO2CODE_ENABLE", True, project)


def _out_dir(project: Path) -> Path:
    sub = _config_value("KORU_TODO2CODE_OUT", project) or DEFAULT_OUT_SUBDIR
    candidate = (project / sub).resolve()
    try:
        candidate.relative_to(project.resolve())
    except ValueError as exc:
        raise ValueError(
            "KORU_TODO2CODE_OUT must resolve inside the target project"
        ) from exc
    return candidate


def _discovery_limits(
    project: Path, stale_minutes: float | None, planfile_limit: int | None,
) -> tuple[float, int, float]:
    """Resolve bounded artifact age, ticket count, and usefulness thresholds."""
    stale = stale_minutes if stale_minutes is not None else _env_float(
        "KORU_TODO2CODE_STALE_MINUTES", DEFAULT_STALE_MINUTES, project
    )
    limit = planfile_limit if planfile_limit is not None else max(
        1, _env_int("KORU_TODO2CODE_MAX_TICKETS", DEFAULT_MAX_TICKETS, project)
    )
    usefulness = _env_float("KORU_TODO2CODE_MIN_USEFULNESS", DEFAULT_MIN_USEFULNESS, project)
    return stale, limit, usefulness
