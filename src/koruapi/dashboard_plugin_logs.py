"""Plugin log payload helpers for the dashboard HTTP API."""

from __future__ import annotations

from pathlib import Path


def _plugin_debug_log_path() -> Path:
    return Path("/tmp/koru-plugin-debug.log")


def _daemon_plugin_logs() -> list[dict[str, object]]:
    from koru.autopilot.client import AutopilotClient
    from koruide.socket import default_socket_path

    socket_path = default_socket_path()
    status = AutopilotClient(socket_path=socket_path, timeout=1.0).status()
    daemon_logs = status.get("console_logs", [])
    return [row for row in daemon_logs if isinstance(row, dict)]


def _debug_log_row(line: str) -> dict[str, str] | None:
    stripped = line.strip()
    if not stripped:
        return None
    parts = stripped.split(" ", 1)
    if len(parts) == 2:
        return {"timestamp": parts[0], "message": parts[1]}
    return {"timestamp": "", "message": stripped}


def _file_plugin_logs(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        return []
    rows: list[dict[str, str]] = []
    try:
        content = path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return rows
    for line in content.splitlines()[-500:]:
        row = _debug_log_row(line)
        if row is not None:
            rows.append(row)
    return rows


def dashboard_plugin_logs_payload() -> dict[str, object]:
    """Return recent plugin logs from daemon status, falling back to debug file."""
    try:
        return {"ok": True, "source": "daemon", "logs": _daemon_plugin_logs()}
    except Exception:
        return {
            "ok": True,
            "source": "file",
            "logs": _file_plugin_logs(_plugin_debug_log_path()),
        }
