"""Autopilot debug-log and chat-control probes for ``koru doctor``."""

from __future__ import annotations

import json
import os
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from koru import doctor_chat_control as _chat_control
from koru import doctor_plugin_console as _plugin_console
from koru.doctor_constants import PASS, SKIP, WARN
from koru.runtime import runtime_dir

ChatControlContext = tuple[str, Path, list[str], list[str], str | None, str | None]


def autopilot_debug_log_path() -> Path:
    return Path(os.environ.get("KORU_PLUGIN_DEBUG_LOG", "/tmp/koru-plugin-debug.log"))


def read_recent_autopilot_debug_lines(path: Path, *, limit: int = 400) -> list[str]:
    return path.read_text(encoding="utf-8", errors="replace").splitlines()[-limit:]


def autopilot_line_mentions_selected(
    line: str,
    *,
    selected: str,
    socket_text: str,
) -> bool:
    if f'"ide":"{selected}"' in line or socket_text in line or f"ide={selected}" in line:
        return True
    if selected == "windsurf" and "WINDSURF_" in line:
        return True
    if selected == "antigravity" and "ANTIGRAVITY_" in line:
        return True
    return False


autopilot_debug_event_name = _chat_control.autopilot_debug_event_name
autopilot_debug_event_has = _chat_control.autopilot_debug_event_has


def read_recent_autopilot_activity_lines(project: Path, *, limit: int = 600) -> list[str]:
    path = runtime_dir(project) / "nfo-events.jsonl"
    if not path.is_file():
        return []
    try:
        rows = path.read_text(encoding="utf-8", errors="replace").splitlines()[-limit:]
    except OSError:
        return []
    activity: list[str] = []
    for row in rows:
        try:
            payload = json.loads(row)
        except json.JSONDecodeError:
            continue
        extra = payload.get("extra")
        if isinstance(extra, dict):
            message = str(extra.get("activity_message") or "")
        else:
            message = ""
        if not message:
            message = str(payload.get("kwargs") or "")
        if message:
            activity.append(message)
    return activity


@dataclass(frozen=True)
class AutopilotDebugContext:
    selected: str | None
    path: Path
    socket_text: str
    relevant: list[str]
    skip_reason: str | None


def recent_autopilot_debug_context(
    *,
    selected_ide: Callable[[], str | None],
    debug_log_path: Callable[[], Path],
    socket_resolver: Callable[[], Path],
    read_lines: Callable[[Path], list[str]],
    line_matches: Callable[..., bool],
) -> AutopilotDebugContext:
    selected = selected_ide()
    path = debug_log_path()
    if not selected:
        return AutopilotDebugContext(selected, path, "", [], "autopilot env unset")
    if not path.is_file():
        return AutopilotDebugContext(selected, path, "", [], f"{path} missing")
    socket_text = str(socket_resolver())
    lines = read_lines(path)
    relevant = [
        line
        for line in lines
        if line_matches(line, selected=selected, socket_text=socket_text)
    ]
    return AutopilotDebugContext(selected, path, socket_text, relevant, None)


def check_autopilot_debug_log(
    *,
    recent_context: Callable[[], AutopilotDebugContext],
    debug_log_path: Callable[[], Path],
) -> tuple[str, str]:
    try:
        context = recent_context()
    except OSError as exc:
        path = debug_log_path()
        return WARN, f"cannot read {path}: {exc}"
    if context.skip_reason:
        return SKIP, context.skip_reason
    if not context.relevant:
        return WARN, (
            f"{context.path}: no recent entries for ide={context.selected} "
            f"or socket={context.socket_text}"
        )
    if any("CONNECT_OK" in line or "HELLO" in line for line in context.relevant):
        return PASS, f"{context.path}: {len(context.relevant)} recent matching entrie(s)"
    if any("CONNECT_ERROR" in line for line in context.relevant):
        return (
            WARN,
            f"{context.path}: {len(context.relevant)} matching entrie(s), "
            "latest connection errors present",
        )
    return PASS, f"{context.path}: {len(context.relevant)} recent matching entrie(s)"


activity_line_mentions_selected = _chat_control.activity_line_mentions_selected
count_daemon_metrics = _chat_control.count_daemon_metrics
count_chat_control_metrics = _chat_control.count_chat_control_metrics
calculate_command_indices = _chat_control.calculate_command_indices
calculate_success_failure_indices = _chat_control.calculate_success_failure_indices
ChatControlAnalysis = _chat_control.ChatControlAnalysis
build_chat_control_detail_bits = _chat_control.build_chat_control_detail_bits
chat_control_has_failures = _chat_control.chat_control_has_failures
chat_control_command_hints = _chat_control.chat_control_command_hints
chat_control_recovered_after_retry = _chat_control.chat_control_recovered_after_retry
chat_control_result = _chat_control.chat_control_result
analyze_chat_control = _chat_control.analyze_chat_control


def chat_control_context(
    project: Path,
    *,
    recent_context: Callable[[], AutopilotDebugContext],
    debug_log_path: Callable[[], Path],
    read_activity_lines: Callable[[Path], list[str]],
    activity_line_matches: Callable[[str, str], bool],
) -> ChatControlContext:
    """Return normalized context for chat-control checks."""
    try:
        context = recent_context()
    except OSError as exc:
        path = debug_log_path()
        return "", path, [], [], WARN, f"cannot read {path}: {exc}"

    if context.skip_reason:
        return context.selected or "", context.path, context.relevant, [], SKIP, context.skip_reason
    if not context.relevant:
        return (
            context.selected or "",
            context.path,
            context.relevant,
            [],
            WARN,
            f"{context.path}: no recent chat-control entries for ide={context.selected}",
        )

    activity = [
        line
        for line in read_activity_lines(project)
        if context.selected and activity_line_matches(line, context.selected)
    ]
    return context.selected or "", context.path, context.relevant, activity, None, None


def check_autopilot_chat_control(
    project: Path,
    *,
    context_factory: Callable[[Path], ChatControlContext],
    command_hints: Callable[[Path, str], list[str]],
) -> tuple[str, str]:
    selected, _path, relevant, activity, early_status, early_detail = context_factory(project)
    if early_status is not None and early_detail is not None:
        return early_status, early_detail

    analysis = analyze_chat_control(selected, relevant, activity)
    status, detail = chat_control_result(
        detail_bits=analysis.detail_bits,
        command_missing_latest=analysis.command_missing_latest,
        chat_metrics=analysis.chat_metrics,
        daemon_successes=analysis.daemon_successes,
        last_success_index=analysis.last_success_index,
        last_failure_index=analysis.last_failure_index,
        last_activity_success_index=analysis.last_activity_success_index,
        last_activity_failure_index=analysis.last_activity_failure_index,
    )
    if status == WARN:
        detail = "; ".join([detail, *command_hints(project, selected)])
    return status, detail


windsurf_chat_column_indexes = _chat_control.windsurf_chat_column_indexes
windsurf_line_mentions_chat_open_command = _chat_control.windsurf_line_mentions_chat_open_command
windsurf_chat_column_detail_bits = _chat_control.windsurf_chat_column_detail_bits
windsurf_chat_column_result = _chat_control.windsurf_chat_column_result


def check_windsurf_chat_column_control(
    *,
    recent_context: Callable[[], AutopilotDebugContext],
    debug_log_path: Callable[[], Path],
) -> tuple[str, str]:
    try:
        context = recent_context()
    except OSError as exc:
        path = debug_log_path()
        return WARN, f"cannot read {path}: {exc}"
    if context.skip_reason:
        return SKIP, context.skip_reason
    if context.selected != "windsurf":
        return SKIP, f"ide={context.selected or '-'}; only applicable to windsurf"
    if not context.relevant:
        return WARN, f"{context.path}: no recent Windsurf chat-column entries"

    indexes = windsurf_chat_column_indexes(context.relevant)
    detail_bits = windsurf_chat_column_detail_bits(context.relevant, indexes)
    return windsurf_chat_column_result(indexes, detail_bits)


doctor_console_log_tail_limit = _plugin_console.doctor_console_log_tail_limit
compact_plugin_console_entry = _plugin_console.compact_plugin_console_entry
plugin_console_entry_matches_selected = _plugin_console.plugin_console_entry_matches_selected
daemon_console_logs_for_doctor = _plugin_console.daemon_console_logs_for_doctor
plugin_console_logs_daemon_result = _plugin_console.plugin_console_logs_daemon_result
plugin_console_logs_empty_result = _plugin_console.plugin_console_logs_empty_result


def plugin_debug_log_tail_for_doctor(
    limit: int,
    *,
    recent_context: Callable[[], AutopilotDebugContext],
    debug_log_path: Callable[[], Path],
) -> tuple[Path, list[str], str | None]:
    return _plugin_console.plugin_debug_log_tail_for_doctor(
        limit,
        recent_context=recent_context,
        debug_log_path=debug_log_path,
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
    return _plugin_console.plugin_console_logs_debug_tail_result(
        selected=selected,
        socket_path=socket_path,
        debug_path=debug_path,
        debug_tail=debug_tail,
        daemon_error=daemon_error,
        offline_noise_checker=offline_noise_checker,
    )


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
    return _plugin_console.check_plugin_console_logs(
        selected_autopilot_ide=selected_autopilot_ide,
        tail_limit=tail_limit,
        socket_resolver=socket_resolver,
        daemon_logs_reader=daemon_logs_reader,
        debug_tail_reader=debug_tail_reader,
        entry_matches_selected=entry_matches_selected,
        daemon_result=daemon_result,
        debug_tail_result=debug_tail_result,
        empty_result=empty_result,
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
    return _plugin_console.plugin_debug_tail_is_daemon_offline_noise(
        lines,
        selected=selected,
        socket_path=socket_path,
        daemon_error=daemon_error,
        event_name=event_name,
        event_has=event_has,
    )
