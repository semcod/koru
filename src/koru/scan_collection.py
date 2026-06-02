"""Suggestion collection orchestration for ``koru.scan``."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from pathlib import Path

from koru.scan_types import Suggestion


def collect_suggestions(
    project: Path,
    *,
    skip_pytest: bool,
    include_semcod_artifacts: bool,
    paths: Sequence[str | Path] | None,
    scan_pytest_collect: Callable[[Path], list[Suggestion]],
    scan_todo_markers: Callable[[Path], list[Suggestion]],
    scan_missing_gates: Callable[[Path], list[Suggestion]],
    scan_missing_tools: Callable[[Path], list[Suggestion]],
    scan_gitignore_drift: Callable[[Path], list[Suggestion]],
    scan_semcod_quality_artifacts: Callable[[Path], list[Suggestion]],
    filter_suggestions_by_paths: Callable[
        [list[Suggestion], Sequence[str | Path] | None],
        list[Suggestion],
    ],
) -> list[Suggestion]:
    """Run all scan probes and return combined suggestions."""
    project = project.resolve()
    suggestions: list[Suggestion] = []
    if not skip_pytest:
        suggestions.extend(scan_pytest_collect(project))
    suggestions.extend(scan_todo_markers(project))
    suggestions.extend(scan_missing_gates(project))
    suggestions.extend(scan_missing_tools(project))
    suggestions.extend(scan_gitignore_drift(project))
    if include_semcod_artifacts:
        suggestions.extend(scan_semcod_quality_artifacts(project))
    return filter_suggestions_by_paths(suggestions, paths)
