"""Rendering helpers for ``koru doctor`` reports."""

from __future__ import annotations

from typing import Any

from koru.doctor_constants import FAIL, PASS, SKIP, WARN, _PROBLEM_CATALOG

_STATUS_GLYPH = {PASS: "OK ", WARN: "WARN", FAIL: "FAIL", SKIP: "SKIP"}


def detected_problems(report: Any) -> list[dict[str, str]]:
    """Return warnings/failures as an explicit problem list for UX and JSON output."""
    return [
        c.to_dict()
        for c in report.checks
        if c.status in (WARN, FAIL)
    ]


def render_problem_catalog_text() -> str:
    """Render known problem classes in a compact text table."""
    lines = ["Known problems and detection rules:"]
    for item in _PROBLEM_CATALOG:
        sev = item.severity.upper()
        lines.append(f"  - [{sev}] {item.check}: {item.problem}")
        lines.append(f"      detection: {item.detection}")
    return "\n".join(lines)


def render_text(report: Any) -> str:
    """Human-readable rendering — fixed-width status column."""
    lines: list[str] = []
    lines.append(f"koru doctor — {report.project}")
    lines.append("")
    width = max((len(c.name) for c in report.checks), default=0)
    for c in report.checks:
        glyph = _STATUS_GLYPH.get(c.status, c.status.upper())
        lines.append(f"  [{glyph}] {c.name.ljust(width)}  {c.detail}")
    counts = report.summary()
    total = sum(counts.values())
    parts = [f"{total} checks"]
    if counts.get(PASS):
        parts.append(f"{counts[PASS]} passed")
    if counts.get(WARN):
        parts.append(f"{counts[WARN]} warning(s)")
    if counts.get(FAIL):
        parts.append(f"{counts[FAIL]} failed")
    lines.append("")
    lines.append(f"  {', '.join(parts)}")

    problems = detected_problems(report)
    if problems:
        lines.append("")
        lines.append("Detected problems:")
        for p in problems:
            glyph = _STATUS_GLYPH.get(p["status"], p["status"].upper())
            lines.append(f"  - [{glyph}] {p['name']}: {p['detail']}")
    return "\n".join(lines)


__all__ = ["detected_problems", "render_problem_catalog_text", "render_text"]
