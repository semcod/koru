"""Plugin console-log probes for ``koru doctor``."""

from __future__ import annotations

import json
import os
import re
from collections.abc import Callable
from pathlib import Path

from koru.autopilot.ide import normalize_ide_id
from koru.doctor_constants import PASS, SKIP, WARN


def doctor_console_log_tail_limit() -> int:
    raw = os.environ.get("KORU_DOCTOR_CONSOLE_LOG_LINES", "").strip()
    if not raw:
        return 8
    try:
        value = int(raw)
    except ValueError:
        return 8
    return min(max(value, 1), 40)


def compact_plugin_console_entry(
    entry: dict[str, object],
    *,
    max_len: int = 220,
) -> str:
    timestamp = str(entry.get("timestamp") or "-").strip()
    ide = str(entry.get("ide") or "-").strip()
    message = str(entry.get("message") or "").strip()
    data = entry.get("data")
    if data is None:
        data_text = ""
    else:
        try:
            data_text = json.dumps(
                data,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            )
        except (TypeError, ValueError):
            data_text = str(data)
    text = " ".join(part for part in (timestamp, ide, message, data_text) if part)
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) > max_len:
        text = text[: max_len - 3].rstrip() + "..."
    return text


def plugin_console_entry_matches_selected(
    entry: dict[str, object],
    selected: str,
) -> bool:
    ide = normalize_ide_id(str(entry.get("ide") or ""))
    if ide:
        return ide == selected
    data = entry.get("data")
    if isinstance(data, dict):
        data_ide = normalize_ide_id(str(data.get("ide") or ""))
        if data_ide:
            return data_ide == selected
    message = str(entry.get("message") or "")
    if selected == "windsurf" and "WINDSURF_" in message:
        return True
    if selected == "antigravity" and "ANTIGRAVITY_" in message:
        return True
    return not ide


def daemon_console_logs_for_doctor(
    socket_path: Path,
) -> tuple[list[dict[str, object]], str | None]:
    try:
        from koru.autopilot.client import AutopilotClient

        status = AutopilotClient(socket_path=socket_path, timeout=1.5).status()
    except (OSError, RuntimeError) as exc:
        return [], str(exc)
    raw_logs = status.get("console_logs")
    if not isinstance(raw_logs, list):
        return [], None
    return [row for row in raw_logs if isinstance(row, dict)], None


def plugin_debug_log_tail_for_doctor(
    limit: int,
    *,
    recent_context: Callable[[], object],
    debug_log_path: Callable[[], Path],
) -> tuple[Path, list[str], str | None]:
    try:
        context = recent_context()
    except OSError as exc:
        path = debug_log_path()
        return path, [], str(exc)
    skip_reason = context.skip_reason
    path = context.path
    if skip_reason:
        return path, [], str(skip_reason)
    relevant = context.relevant
    return path, list(relevant[-limit:]), None


def plugin_console_logs_daemon_result(
    *,
    selected: str,
    socket_path: Path,
    selected_logs: list[dict[str, object]],
    limit: int,
    compact_entry: Callable[[dict[str, object]], str] = compact_plugin_console_entry,
) -> tuple[str, str] | None:
    if not selected_logs:
        return None
    tail = selected_logs[-limit:]
    latest = " | ".join(compact_entry(entry) for entry in tail)
    return PASS, (
        f"ide={selected}; source=daemon; socket={socket_path}; "
        f"entries={len(selected_logs)}; latest={latest}"
    )


def plugin_console_logs_debug_tail_result(
    *,
    selected: str,
    socket_path: Path,
    debug_path: Path,
    debug_tail: list[str],
    daemon_error: str | None,
    offline_noise_checker: Callable[..., bool],
) -> tuple[str, str] | None:
    if not debug_tail:
        return None
    latest = " | ".join(re.sub(r"\s+", " ", line).strip() for line in debug_tail)
    offline_after_stop = offline_noise_checker(
        debug_tail,
        selected=selected,
        socket_path=socket_path,
        daemon_error=daemon_error,
    )
    status = PASS if offline_after_stop or not daemon_error else WARN
    reason = f"; daemon_status_error={daemon_error}" if daemon_error else ""
    if offline_after_stop:
        reason = f"; daemon_offline_expected_after_stop=true{reason}"
    return status, (
        f"ide={selected}; source=plugin_debug_log; path={debug_path}; "
        f"entries={len(debug_tail)}; latest={latest}{reason}"
    )


def plugin_console_logs_empty_result(
    *,
    selected: str,
    socket_path: Path,
    debug_path: Path,
    daemon_error: str | None,
    debug_error: str | None,
) -> tuple[str, str]:
    if daemon_error:
        return WARN, f"ide={selected}; socket={socket_path}; daemon_status_error={daemon_error}"
    if debug_error:
        return WARN, (
            f"ide={selected}; source=daemon; entries=0; debug_log={debug_path}; "
            f"debug_error={debug_error}"
        )
    return WARN, (
        f"ide={selected}; source=daemon; socket={socket_path}; "
        "no console logs received yet"
    )


def plugin_debug_tail_is_daemon_offline_noise(
    lines: list[str],
    *,
    selected: str,
    socket_path: Path,
    daemon_error: str | None,
    event_name: Callable[[str], str],
    event_has: Callable[[str, str], bool],
) -> bool:
    if not daemon_error:
        return False
    error_text = daemon_error.lower()
    if "no such file" not in error_text and "enoent" not in error_text:
        return False

    allowed = {"CONNECT_CANDIDATES", "CONNECT_TRY", "CONNECT_ERROR", "CONNECT_CLOSE"}
    socket_text = str(socket_path)
    for line in lines:
        event = event_name(line)
        if event not in allowed:
            return False
        if selected not in line and socket_text not in line:
            return False
    return any(event_has(line, "CONNECT_ERROR") for line in lines)


def check_plugin_console_logs(
    *,
    selected_autopilot_ide: Callable[[], str | None],
    tail_limit: Callable[[], int],
    socket_resolver: Callable[[], Path],
    daemon_logs_reader: Callable[[Path], tuple[list[dict[str, object]], str | None]],
    debug_tail_reader: Callable[[int], tuple[Path, list[str], str | None]],
    entry_matches_selected: Callable[[dict[str, object], str], bool],
    daemon_result: Callable[..., tuple[str, str] | None],
    debug_tail_result: Callable[..., tuple[str, str] | None],
    empty_result: Callable[..., tuple[str, str]],
) -> tuple[str, str]:
    """Show recent extension-host console logs forwarded by the plugin."""
    selected = selected_autopilot_ide()
    if not selected:
        return SKIP, "autopilot env unset"
    limit = tail_limit()
    socket_path = socket_resolver()
    daemon_logs, daemon_error = daemon_logs_reader(socket_path)
    selected_logs = [
        entry
        for entry in daemon_logs
        if entry_matches_selected(entry, selected)
    ]
    daemon_outcome = daemon_result(
        selected=selected,
        socket_path=socket_path,
        selected_logs=selected_logs,
        limit=limit,
    )
    if daemon_outcome is not None:
        return daemon_outcome

    debug_path, debug_tail, debug_error = debug_tail_reader(limit)
    debug_outcome = debug_tail_result(
        selected=selected,
        socket_path=socket_path,
        debug_path=debug_path,
        debug_tail=debug_tail,
        daemon_error=daemon_error,
    )
    if debug_outcome is not None:
        return debug_outcome

    return empty_result(
        selected=selected,
        socket_path=socket_path,
        debug_path=debug_path,
        daemon_error=daemon_error,
        debug_error=debug_error,
    )
