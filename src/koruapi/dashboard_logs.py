"""Log streaming endpoint for the koru dashboard.

Provides a Server-Sent Events (SSE) endpoint that tails the structured
``nfo-events.jsonl`` log and the autonomous cycle log, streaming entries
with severity levels (ERROR, WARNING, INFO, DEBUG) to the browser.

SSE is used instead of WebSocket because it works with stdlib's
``http.server`` without protocol upgrade, and log streaming is
unidirectional (server → client).
"""

from __future__ import annotations

import ast
import json
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any


def _nfo_log_path(project: Path) -> Path:
    return project / ".planfile" / ".koru" / "nfo-events.jsonl"


def _autonomous_log_path(project: Path) -> Path:
    return project / ".planfile" / ".koru" / "autonomous.log"


def _parse_nfo_line(line: str) -> dict[str, Any] | None:
    """Parse a single nfo-events.jsonl line into a structured log entry."""
    try:
        record = json.loads(line)
    except (json.JSONDecodeError, ValueError):
        return None
    if not isinstance(record, dict):
        return None
    level = str(record.get("level", "INFO")).upper()
    timestamp = record.get("timestamp", "")
    kwargs_raw = record.get("kwargs", "")
    message = ""
    category = ""
    if isinstance(kwargs_raw, str):
        try:
            kwargs = ast.literal_eval(kwargs_raw)
        except Exception:  # noqa: BLE001
            kwargs = {}
    elif isinstance(kwargs_raw, dict):
        kwargs = kwargs_raw
    else:
        kwargs = {}
    if not isinstance(kwargs, dict):
        kwargs = {}
    message = str(kwargs.get("activity_message", "") or "")
    category = str(kwargs.get("category", "") or "")
    event = str(kwargs.get("event", "") or "")
    if not message:
        message = f"{event} {category}".strip() or str(record.get("function_name", ""))
    return {
        "timestamp": timestamp,
        "level": level,
        "message": message,
        "category": category,
        "event": event,
        "source": "nfo",
    }


def _parse_autonomous_log_line(line: str) -> dict[str, Any] | None:
    """Parse a line from the autonomous log (plain text with optional level prefix)."""
    line = line.strip()
    if not line:
        return None
    level = "INFO"
    upper = line.upper()
    if upper.startswith("[ERROR]") or " ERROR " in upper or "✗" in line:
        level = "ERROR"
    elif upper.startswith("[WARN") or " WARNING " in upper or "⚠" in line:
        level = "WARNING"
    elif upper.startswith("[DEBUG]") or " DEBUG " in upper:
        level = "DEBUG"
    return {
        "timestamp": "",
        "level": level,
        "message": line,
        "category": "AUTONOMOUS",
        "event": "",
        "source": "autonomous",
    }


def read_recent_logs(project: Path, *, limit: int = 100) -> list[dict[str, Any]]:
    """Return the most recent log entries from nfo-events.jsonl and autonomous log."""
    entries: list[dict[str, Any]] = []
    nfo_path = _nfo_log_path(project)
    if nfo_path.exists():
        try:
            lines = nfo_path.read_text(encoding="utf-8", errors="ignore").splitlines()
            for line in lines[-limit:]:
                entry = _parse_nfo_line(line)
                if entry:
                    entries.append(entry)
        except OSError:
            pass
    auto_path = _autonomous_log_path(project)
    if auto_path.exists():
        try:
            lines = auto_path.read_text(encoding="utf-8", errors="ignore").splitlines()
            for line in lines[-limit:]:
                entry = _parse_autonomous_log_line(line)
                if entry:
                    entries.append(entry)
        except OSError:
            pass
    entries.sort(key=lambda e: e.get("timestamp", ""))
    return entries[-limit:]


def _initial_offset(path: Path) -> int:
    return path.stat().st_size if path.exists() else 0


def _read_new_log_entries(
    log_path: Path,
    offset: int,
    parse_line: Callable[[str], dict[str, Any] | None],
    levels: set[str],
) -> tuple[int, list[dict[str, Any]]]:
    """Read newly appended lines from log_path starting at offset."""
    if not log_path.exists():
        return offset, []
    entries: list[dict[str, Any]] = []
    try:
        current_size = log_path.stat().st_size
        if current_size < offset:
            offset = 0  # file was truncated/rotated
        if current_size > offset:
            with log_path.open("r", encoding="utf-8", errors="ignore") as f:
                f.seek(offset)
                for line in f:
                    entry = parse_line(line)
                    if entry and entry["level"] in levels:
                        entries.append(entry)
                offset = f.tell()
    except OSError:
        pass
    return offset, entries


def sse_log_stream(
    project: Path,
    *,
    levels: set[str] | None = None,
    poll_interval: float = 0.5,
    max_events: int = 0,
    stop_event: Any = None,
) -> str:
    """Yield SSE-formatted log events by tailing log files.

    This is a generator that yields ``data: <json>\n\n`` strings.
    The caller should write them to the HTTP response.
    """
    if levels is None:
        levels = {"ERROR", "WARNING", "INFO", "DEBUG"}

    nfo_path = _nfo_log_path(project)
    auto_path = _autonomous_log_path(project)
    offsets = {
        nfo_path: _initial_offset(nfo_path),
        auto_path: _initial_offset(auto_path),
    }
    targets = (
        (nfo_path, _parse_nfo_line),
        (auto_path, _parse_autonomous_log_line),
    )
    events_sent = 0

    # Send recent history first
    for entry in read_recent_logs(project, limit=50):
        if entry["level"] in levels:
            yield f"data: {json.dumps(entry)}\n\n"
            events_sent += 1

    while True:
        if max_events and events_sent >= max_events:
            break
        if stop_event is not None and stop_event.is_set():
            break

        for log_path, parser in targets:
            offsets[log_path], new_entries = _read_new_log_entries(
                log_path, offsets[log_path], parser, levels
            )
            for entry in new_entries:
                yield f"data: {json.dumps(entry)}\n\n"
                events_sent += 1

        yield ": keepalive\n\n"
        time.sleep(poll_interval)


def handle_sse_logs_request(handler: Any, config: Any) -> None:
    """Handle GET /api/logs/stream — SSE log streaming endpoint."""
    import urllib.parse

    parsed = urllib.parse.urlparse(handler.path)
    qs = urllib.parse.parse_qs(parsed.query)
    level_param = qs.get("level", [""])[0].upper()
    limit_param = qs.get("limit", ["100"])[0]
    try:
        limit = int(limit_param)
    except ValueError:
        limit = 100

    if level_param and level_param != "ALL":
        levels = {level.strip() for level in level_param.split(",") if level.strip()}
    else:
        levels = {"ERROR", "WARNING", "INFO", "DEBUG"}

    project = handler._selected_project()

    handler.send_response(200)
    handler.send_header("Content-Type", "text/event-stream")
    handler.send_header("Cache-Control", "no-cache")
    handler.send_header("Connection", "keep-alive")
    handler.send_header("Access-Control-Allow-Origin", "*")
    handler.end_headers()

    try:
        stop_event = getattr(handler.server, "shutdown_event", None)
        for chunk in sse_log_stream(
            project, levels=levels, max_events=limit, stop_event=stop_event
        ):
            handler.wfile.write(chunk.encode("utf-8"))
            handler.wfile.flush()
    except (BrokenPipeError, ConnectionResetError):
        pass


def handle_logs_json_request(handler: Any, config: Any) -> None:
    """Handle GET /api/logs — return recent log entries as JSON."""
    import urllib.parse

    parsed = urllib.parse.urlparse(handler.path)
    qs = urllib.parse.parse_qs(parsed.query)
    limit_param = qs.get("limit", ["100"])[0]
    try:
        limit = int(limit_param)
    except ValueError:
        limit = 100

    project = handler._selected_project()
    entries = read_recent_logs(project, limit=limit)
    handler._send_json({"logs": entries, "ok": True})
