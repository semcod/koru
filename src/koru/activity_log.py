"""Real-time, human-visible activity log for koru orchestration."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any, TextIO

from koru.stdio_events import default_stdio_format_from_env

_NFO_CONFIGURED_PATH: Path | None = None
_NFO_UNAVAILABLE = False
_NFO_UNAVAILABLE_WARNED = False


def activity_enabled() -> bool:
    raw = os.environ.get("KORU_ACTIVITY_LOG", "1").strip().lower()
    return raw not in {"0", "false", "no", "off"}


def preview_text(text: str, *, limit: int = 120) -> str:
    one_line = " ".join(text.split())
    if len(one_line) <= limit:
        return one_line
    return one_line[: limit - 1] + "…"


def _env_disabled(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in {"0", "false", "no", "off"}


def configure_nfo_activity_log(project: Path) -> Path | None:
    """Enable structured nfo JSONL logging for autonomous activity lines."""
    if _env_disabled("KORU_NFO_LOG"):
        return None
    raw = os.environ.get("KORU_NFO_LOG_PATH", "").strip()
    path = (
        Path(raw).expanduser()
        if raw
        else project / ".planfile" / ".koru" / "nfo-events.jsonl"
    )
    os.environ.setdefault("KORU_NFO_LOG", "1")
    os.environ["KORU_NFO_LOG_PATH"] = str(path)
    return path


def nfo_activity_log_path() -> Path | None:
    if _env_disabled("KORU_NFO_LOG"):
        return None
    raw = os.environ.get("KORU_NFO_LOG_PATH", "").strip()
    if raw:
        return Path(raw).expanduser()
    enabled = os.environ.get("KORU_NFO_LOG", "").strip().lower()
    if enabled in {"1", "true", "yes", "on"}:
        return Path.cwd() / ".planfile" / ".koru" / "nfo-events.jsonl"
    return None


def _emit_nfo_activity(
    category: str,
    message: str,
    *,
    fmt: str,
    preview: str | None,
    data: dict[str, Any] | None,
) -> None:
    global _NFO_CONFIGURED_PATH, _NFO_UNAVAILABLE, _NFO_UNAVAILABLE_WARNED

    if _NFO_UNAVAILABLE:
        return
    path = nfo_activity_log_path()
    if path is None:
        return
    try:
        from nfo import configure, event

        path.parent.mkdir(parents=True, exist_ok=True)
        if _NFO_CONFIGURED_PATH != path:
            configure(
                name="koru.nfo",
                sinks=[f"jsonl:{path}"],
                propagate_stdlib=False,
                force=True,
            )
            _NFO_CONFIGURED_PATH = path
        event(
            "koru.activity",
            category=category,
            activity_message=message,
            preview=preview or "",
            data=data or {},
            pid=os.getpid(),
            cwd=os.getcwd(),
            python=sys.executable,
            argv=list(sys.argv),
            stdio_format=fmt,
        )
    except Exception as exc:
        _NFO_UNAVAILABLE = True
        if not _NFO_UNAVAILABLE_WARNED:
            _NFO_UNAVAILABLE_WARNED = True
            print(
                f"koru: nfo activity log disabled: {type(exc).__name__}: {exc}",
                file=sys.stderr,
                flush=True,
            )


def _out_stream(fmt: str) -> TextIO:
    return sys.stderr if fmt == "jsonl" else sys.stdout


def activity(
    category: str,
    message: str,
    *,
    fmt: str | None = None,
    preview: str | None = None,
    data: dict[str, Any] | None = None,
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
    _emit_nfo_activity(category, message, fmt=fmt, preview=preview, data=data)


def activity_info(
    msg: str,
    *,
    fmt: str | None = None,
    data: dict[str, Any] | None = None,
) -> None:
    """Legacy-style line with activity timestamp prefix."""
    if not activity_enabled():
        fmt = fmt or default_stdio_format_from_env()
        print(msg, file=_out_stream(fmt), flush=True)
        return
    if msg.startswith("koru "):
        rest = msg.split(": ", 1)
        if len(rest) == 2:
            activity(
                rest[0].replace("koru ", "KORU", 1).upper(),
                rest[1],
                fmt=fmt,
                data=data,
            )
            return
    activity("INFO", msg, fmt=fmt, data=data)


__all__ = [
    "activity",
    "activity_enabled",
    "activity_info",
    "configure_nfo_activity_log",
    "nfo_activity_log_path",
    "preview_text",
]
