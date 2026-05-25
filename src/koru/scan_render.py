"""Text and Markdown rendering for ``koru scan`` results."""

from __future__ import annotations

import os
import sys

from koru.scan_types import ScanResult

_RESET = "\033[0m"
_DIM = "\033[2m"
_BOLD = "\033[1m"
_RED = "\033[31m"
_GREEN = "\033[32m"
_YELLOW = "\033[33m"
_BLUE = "\033[34m"
_MAGENTA = "\033[35m"
_CYAN = "\033[36m"


def supports_color() -> bool:
    if os.environ.get("NO_COLOR"):
        return False
    if os.environ.get("CLICOLOR_FORCE") in {"1", "true", "TRUE", "yes", "YES"}:
        return True
    return bool(getattr(sys.stdout, "isatty", lambda: False)())


def color_signal(signal: str, *, enabled: bool) -> str:
    if not enabled:
        return signal
    lowered = signal.lower()
    if "critical" in lowered or "bug" in lowered:
        return f"{_RED}{signal}{_RESET}"

    by_token = {
        "code2llm": _CYAN,
        "jscpd": _BLUE,
        "redup": _MAGENTA,
        "pytest": _YELLOW,
        "testql": _GREEN,
        "mypy": _BLUE,
        "ruff": _GREEN,
        "pylint": _YELLOW,
    }
    for token, color in by_token.items():
        if token in lowered:
            return f"{color}{signal}{_RESET}"

    return f"{_DIM}{signal}{_RESET}"


def color_priority(priority: str, *, enabled: bool) -> str:
    if not enabled:
        return priority
    mapping = {
        "critical": _RED,
        "high": _YELLOW,
        "normal": _CYAN,
        "low": _DIM,
    }
    code = mapping.get(priority, _DIM)
    return f"{code}{priority}{_RESET}"


def render_scan_text(result: ScanResult) -> str:
    color = supports_color()
    if not result.suggestions:
        return "koru scan: no suggestions — repo looks clean."
    lines: list[str] = [f"koru scan: {len(result.suggestions)} suggestion(s)"]
    for s in result.suggestions:
        marker = {"critical": "!!", "high": "!", "normal": "·", "low": " "}.get(
            s.priority,
            "·",
        )
        priority = color_priority(f"{s.priority:<8}", enabled=color)
        signal = color_signal(f"{s.signal:<15}", enabled=color)
        marker_prefix = f"{_BOLD}[{marker}]{_RESET}" if color else f"[{marker}]"
        lines.append(f"  {marker_prefix} {priority} {signal} {s.title}")
    if result.applied:
        lines.append("")
        lines.append(f"Applied ({len(result.applied)}):")
        for t in result.applied:
            lines.append(f"  + {t}")
    if result.skipped:
        lines.append("")
        lines.append(f"Skipped ({len(result.skipped)}):")
        for t in result.skipped:
            lines.append(f"  - {t}")
    return "\n".join(lines)


def render_scan_markdown(result: ScanResult) -> str:
    if not result.suggestions:
        return "# koru scan\n\n_No suggestions — repo looks clean._\n"
    lines = [
        "# koru scan",
        "",
        f"Found **{len(result.suggestions)}** suggestion(s).",
        "",
        "| priority | signal | title |",
        "| --- | --- | --- |",
    ]
    for s in result.suggestions:
        lines.append(f"| `{s.priority}` | `{s.signal}` | {s.title} |")
    if result.applied:
        lines.append("")
        lines.append(f"## Applied ({len(result.applied)})")
        for t in result.applied:
            lines.append(f"- {t}")
    if result.skipped:
        lines.append("")
        lines.append(f"## Skipped ({len(result.skipped)})")
        for t in result.skipped:
            lines.append(f"- {t}")
    return "\n".join(lines) + "\n"


__all__ = [
    "color_priority",
    "color_signal",
    "render_scan_markdown",
    "render_scan_text",
    "supports_color",
]
