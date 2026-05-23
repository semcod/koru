import threading
from typing import Any
from datetime import datetime

_console_logs_lock = threading.Lock()
_console_logs: list[dict[str, Any]] = []
_MAX_CONSOLE_LOGS = 2000
_current_session_id = "initial"
_current_session_name = "Initial Session"


def start_new_log_session(session_id: str | None = None, name: str | None = None) -> None:
    """Start a new console log session (service execution)."""
    global _current_session_id, _current_session_name
    with _console_logs_lock:
        _current_session_id = session_id or datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        _current_session_name = name or f"Session at {datetime.now().strftime('%H:%M:%S')}"


def add_console_log(
    message: str,
    data: Any | None,
    timestamp: str,
    *,
    ide: str | None = None,
    version: str | None = None,
) -> None:
    """Store a console log entry from the plugin."""
    entry: dict[str, Any] = {
        "message": message,
        "data": data,
        "timestamp": timestamp,
        "session_id": _current_session_id,
        "session_name": _current_session_name,
    }
    if ide:
        entry["ide"] = ide
    if version:
        entry["version"] = version
    with _console_logs_lock:
        _console_logs.append(entry)
        if len(_console_logs) > _MAX_CONSOLE_LOGS:
            _console_logs.pop(0)


def _clamp_session_rows(sid: str, s_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Clamp a single session's logs to 10KB."""
    total_size = 0
    keep_rows: list[dict[str, Any]] = []
    truncated = False
    
    for row in reversed(s_rows):
        msg_len = len(row.get("message") or "")
        if total_size + msg_len <= 10240:
            keep_rows.insert(0, row)
            total_size += msg_len
        else:
            truncated = True
            
    if truncated and keep_rows:
        first_ts = keep_rows[0].get("timestamp", "")
        keep_rows.insert(0, {
            "message": "[... session log truncated to 10KB ...]",
            "timestamp": first_ts,
            "session_id": sid,
            "session_name": s_rows[0].get("session_name", "Session"),
            "truncated": True
        })
    return keep_rows


def get_console_logs(*, limit: int | None = None) -> list[dict[str, Any]]:
    """Retrieve all stored console logs with 10KB clamping per session."""
    with _console_logs_lock:
        rows = list(_console_logs)

    sessions: dict[str, list[dict[str, Any]]] = {}
    session_order: list[str] = []
    for row in rows:
        sid = row.get("session_id", "default")
        if sid not in sessions:
            sessions[sid] = []
            session_order.append(sid)
        sessions[sid].append(row)

    clamped_rows: list[dict[str, Any]] = []
    for sid in session_order:
        clamped_rows.extend(_clamp_session_rows(sid, sessions[sid]))

    if limit is None:
        return clamped_rows
    if limit <= 0:
        return []
    return clamped_rows[-limit:]


def clear_console_logs() -> None:
    """Clear all stored console logs."""
    with _console_logs_lock:
        _console_logs.clear()
