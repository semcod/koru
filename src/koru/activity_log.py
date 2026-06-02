"""Real-time, human-visible activity log for koru orchestration."""

import os
import re
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
    return f"{one_line[: limit - 1]}…"


from koru.env_flags import env_disabled as _env_disabled


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
            hint = ""
            if isinstance(exc, ModuleNotFoundError) and "nfo" in str(exc):
                hint = (
                    " (optional dependency; install with "
                    "'pip install nfo' or 'pip install \"koru[obs]\"' "
                    "to enable the structured activity log)"
                )
            print(
                f"koru: nfo activity log disabled: {type(exc).__name__}: {exc}{hint}",
                file=sys.stderr,
                flush=True,
            )


_ANSI_BOLD = "\033[1m"
_ANSI_DIM = "\033[2m"
_ANSI_RED = "\033[31m"
_ANSI_GREEN = "\033[32m"
_ANSI_YELLOW = "\033[33m"
_ANSI_BLUE = "\033[34m"
_ANSI_MAGENTA = "\033[35m"
_ANSI_CYAN = "\033[36m"
_ANSI_GRAY = "\033[90m"
_ANSI_RESET = "\033[0m"


def _supports_color(stream: TextIO) -> bool:
    if os.environ.get("NO_COLOR"):
        return False
    force = os.environ.get("KORU_FORCE_COLOR", "").strip().lower()
    if force in {"1", "true", "yes", "on"}:
        return True
    raw = os.environ.get("KORU_COLOR", "").strip().lower()
    if raw in {"0", "false", "no", "off", "never"}:
        return False
    if raw in {"1", "true", "yes", "on", "always"}:
        return True
    return hasattr(stream, "isatty") and stream.isatty()


def _ansi(text: str, color: str) -> str:
    return f"{color}{text}{_ANSI_RESET}"


def _color_status(value: str) -> str:
    normalized = value.lower()
    if normalized in {
        "ok",
        "done",
        "completed",
        "connected",
        "accepted",
        "passed",
        "success",
        "true",
    }:
        return _ansi(value, _ANSI_GREEN)
    if normalized in {"waiting_input", "pending", "changed", "warn", "warning", "skipped"}:
        return _ansi(value, _ANSI_YELLOW)
    if normalized in {"failed", "fail", "error", "blocked", "missing", "false", "rejected"}:
        return _ansi(value, _ANSI_RED)
    if normalized in {"idle", "open", "running", "in_progress"}:
        return _ansi(value, _ANSI_CYAN)
    return value


_URL_RE = re.compile(r"https?://[^\s)>\]}]+")
_COMMAND_RE = re.compile(r"`([^`\n]+)`")
_TICKET_RE = re.compile(r"\b[A-Z][A-Z0-9]+-\d+\b")
_SOCKET_RE = re.compile(r"(?<!\S)/(?:[\w.@+-]+/)*[\w.@+-]+\.sock\b")
_PATH_RE = re.compile(r"(?<!\S)(?:~|\.{1,2}|/)[^\s:;,)]*[/][^\s:;,)]*")
_KEY_VALUE_RE = re.compile(r"\b([A-Za-z_][A-Za-z0-9_.-]*=)([^\s,;)]+)")
_STATUS_WORD_RE = re.compile(
    r"\b("
    r"waiting_input|in_progress|completed|connected|accepted|passed|success|"
    r"skipped|pending|changed|failed|blocked|missing|running|idle|open|done|ok|"
    r"error|false|true"
    r")\b",
    re.IGNORECASE,
)
_NUMBER_RE = re.compile(r"(?<![\w.-])(#?\d+(?:\.\d+)?s?|pid=\d+|fd\d+)(?![\w.-])")


def _highlight_shell_data(text: str, *, enabled: bool) -> str:
    if not enabled or "\033[" in text:
        return text

    placeholders: list[str] = []

    def protect(value: str) -> str:
        placeholders.append(value)
        return f"\ue000KORUPH{len(placeholders) - 1}\ue001"

    def color_command(match: re.Match[str]) -> str:
        return protect(f"`{_ansi(match.group(1), _ANSI_MAGENTA)}`")

    text = _COMMAND_RE.sub(color_command, text)
    text = _URL_RE.sub(lambda m: protect(_ansi(m.group(0), _ANSI_BLUE)), text)
    text = _SOCKET_RE.sub(lambda m: protect(_ansi(m.group(0), _ANSI_CYAN)), text)
    text = _PATH_RE.sub(lambda m: protect(_ansi(m.group(0), _ANSI_CYAN)), text)
    text = _TICKET_RE.sub(lambda m: protect(_ansi(m.group(0), _ANSI_BOLD + _ANSI_MAGENTA)), text)

    def color_key_value(match: re.Match[str]) -> str:
        key, value = match.groups()
        return f"{_ansi(key, _ANSI_GRAY)}{_color_status(value)}"

    text = _KEY_VALUE_RE.sub(color_key_value, text)
    text = _STATUS_WORD_RE.sub(lambda m: _color_status(m.group(0)), text)
    text = _NUMBER_RE.sub(lambda m: _ansi(m.group(0), _ANSI_YELLOW), text)

    for idx, value in enumerate(placeholders):
        text = text.replace(f"\ue000KORUPH{idx}\ue001", value)
    return text


def _color_category(category: str, *, enabled: bool) -> str:
    if not enabled:
        return category
    palette = {
        "CHAT": _ANSI_MAGENTA,
        "QUEUE": _ANSI_CYAN,
        "SCAN": _ANSI_GREEN,
        "RUN": _ANSI_BLUE,
        "WARN": _ANSI_YELLOW,
        "ERROR": _ANSI_RED,
        "TICKET": _ANSI_MAGENTA,
        "HTTP": _ANSI_BLUE,
        "DASHBOARD": _ANSI_BLUE,
        "OPERATOR": _ANSI_CYAN,
        "INTEGRATION": _ANSI_BLUE,
        "INFO": _ANSI_GRAY,
        "DIAG": _ANSI_CYAN,
        "PLAN": _ANSI_GREEN,
        "ACTION": _ANSI_BOLD + _ANSI_MAGENTA,
    }
    color = palette.get(category.upper(), _ANSI_BOLD)
    return _ansi(category, color)


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
    stream = _out_stream(fmt)
    color = fmt != "jsonl" and _supports_color(stream)
    ts_text = _ansi(f"[{ts}]", _ANSI_DIM) if color else f"[{ts}]"
    category_text = _color_category(category, enabled=color)
    line = f"{ts_text} koru ▸ {category_text}: {_highlight_shell_data(message, enabled=color)}"
    if preview:
        preview_display = _highlight_shell_data(preview_text(preview), enabled=color)
        line += f" «{preview_display}»"
    print(line, file=stream, flush=True)
    _emit_nfo_activity(category, message, fmt=fmt, preview=preview, data=data)


def activity_warn(
    message: str,
    *,
    hint: str | None = None,
    fmt: str | None = None,
    data: dict[str, Any] | None = None,
) -> None:
    """Emit a yellow-highlighted WARN line to stdout — for actionable user warnings."""
    if not activity_enabled():
        return
    fmt = fmt or default_stdio_format_from_env()
    from datetime import UTC, datetime

    ts = datetime.now(UTC).strftime("%H:%M:%S")
    stream = _out_stream(fmt)
    color = _supports_color(stream) and fmt != "jsonl"
    warn_tag = f"{_ANSI_YELLOW}WARN{_ANSI_RESET}" if color else "WARN"
    msg_colored = f"{_ANSI_YELLOW}{message}{_ANSI_RESET}" if color else message
    line = f"[{ts}] koru ▸ {warn_tag}: {msg_colored}"
    if hint:
        hint_colored = f"{_ANSI_YELLOW}  → {hint}{_ANSI_RESET}" if color else f"  → {hint}"
        line = f"{line}\n{hint_colored}"
    print(line, file=stream, flush=True)
    _emit_nfo_activity("WARN", message, fmt=fmt, preview=hint, data=data)


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
    "activity_warn",
    "configure_nfo_activity_log",
    "nfo_activity_log_path",
    "preview_text",
]
