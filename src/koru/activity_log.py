"""Real-time, human-visible activity log for koru orchestration."""

from __future__ import annotations

import os
import sys
from typing import TextIO

from .stdio_events import default_stdio_format_from_env


def activity_enabled() -> bool:
    raw = os.environ.get("KORU_ACTIVITY_LOG", "1").strip().lower()
    return raw not in {"0", "false", "no", "off"}


def preview_text(text: str, *, limit: int = 120) -> str:
    one_line = " ".join(text.split())
    if len(one_line) <= limit:
        return one_line
    return one_line[: limit - 1] + "…"


def _out_stream(fmt: str) -> TextIO:
    return sys.stderr if fmt == "jsonl" else sys.stdout


def activity(
    category: str,
    message: str,
    *,
    fmt: str | None = None,
    preview: str | None = None,
) -> None:
    """Emit one timestamped line (always flushed)."""
    if not activity_enabled():
        return
    fmt = fmt or default_stdio_format_from_env()
    from datetime import UTC, datetime

    ts = datetime.now(UTC).strftime("%H:%M:%S")
    line = f"[{ts}] koru ▸ {category}: {message}"
    if preview:
        line += f" «{preview_text(preview)}»"
    stream = _out_stream(fmt)
    print(line, file=stream, flush=True)


def activity_info(msg: str, *, fmt: str | None = None) -> None:
    """Legacy-style line with activity timestamp prefix."""
    if not activity_enabled():
        fmt = fmt or default_stdio_format_from_env()
        print(msg, file=_out_stream(fmt), flush=True)
        return
    if msg.startswith("koru "):
        rest = msg.split(": ", 1)
        if len(rest) == 2:
            activity(rest[0].replace("koru ", "KORU", 1).upper(), rest[1], fmt=fmt)
            return
    activity("INFO", msg, fmt=fmt)


__all__ = [
    "activity",
    "activity_enabled",
    "activity_info",
    "preview_text",
]
