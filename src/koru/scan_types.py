"""Shared data types for ``koru scan``.

Keep these small public containers outside the scan engine so CLI rendering,
autonomy phases, and API handlers can depend on the result shape without
pulling in every probe implementation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Suggestion:
    """One proposed planfile ticket derived from a repo signal."""

    signal: str
    title: str
    description: str
    priority: str = "normal"
    labels: tuple[str, ...] = ()
    files: tuple[str, ...] = ()
    source_context: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "signal": self.signal,
            "title": self.title,
            "description": self.description,
            "priority": self.priority,
            "labels": list(self.labels),
            "files": list(self.files),
            "source_context": dict(self.source_context),
        }


@dataclass(frozen=True)
class ScanResult:
    """Aggregate output of ``run_scan``."""

    suggestions: list[Suggestion]
    applied: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    skipped_as_duplicate: list[str] = field(default_factory=list)
    skipped_create_failed: list[str] = field(default_factory=list)
    skipped_create_failed_details: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "suggestions": [s.to_dict() for s in self.suggestions],
            "applied": list(self.applied),
            "skipped": list(self.skipped),
            "skipped_as_duplicate": list(self.skipped_as_duplicate),
            "skipped_create_failed": list(self.skipped_create_failed),
            "skipped_create_failed_details": list(self.skipped_create_failed_details),
        }


@dataclass(frozen=True)
class CreateTicketResult:
    ok: bool
    detail: str = ""


def format_create_exception(exc: BaseException) -> str:
    text = str(exc).strip()
    if text:
        return text
    return exc.__class__.__name__


__all__ = [
    "CreateTicketResult",
    "ScanResult",
    "Suggestion",
    "format_create_exception",
]
