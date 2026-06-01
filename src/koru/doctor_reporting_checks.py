import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from koru.doctor_constants import PASS, SKIP, WARN


def _count_chat_control_metrics(relevant: list[str]) -> dict[str, int]:
    return {
        "fast_send_errors": sum("FAST_SEND_ERROR" in line for line in relevant),
        "paste_failures": sum("PASTE_VERIFY_FAIL" in line for line in relevant),
        "focus_rejections": sum("FOCUS_REJECT" in line for line in relevant),
        "paste_rejections": sum("PASTE_REJECT" in line for line in relevant),
        "input_refusals": sum("INPUT_PROBE_REFUSED" in line for line in relevant),
        "send_successes": sum("message.sent" in line for line in relevant),
        "submit_unverified": sum("SUBMIT_UNVERIFIED" in line for line in relevant),
        "manual_send_required": sum("MANUAL_SEND_REQUIRED" in line for line in relevant),
    }


def _calculate_command_indices(relevant: list[str]) -> tuple[int, int]:
    command_available_index = max(
        (
            idx
            for idx, line in enumerate(relevant)
            if "native_send_command=available" in line
            or "NATIVE_SEND_AVAILABLE" in line
        ),
        default=-1,
    )
    command_missing_index = max(
        (
            idx
            for idx, line in enumerate(relevant)
            if "native_send_command_missing_seen=true" in line
            or "NATIVE_SEND_UNAVAILABLE" in line
        ),
        default=-1,
    )
    return command_available_index, command_missing_index


def _calculate_success_failure_indices(relevant: list[str]) -> tuple[int, int]:
    last_success_index = max(
        (
            idx
            for idx, line in enumerate(relevant)
            if any(
                token in line
                for token in (
                    "WINDSURF_FASTPATH_EXECUTE_SEND_OK",
                    "message.sent",
                    "winning_paste=windsurf.sendTextToChat",
                    "winning_submit=windsurf.sendTextToChat",
                )
            )
        ),
        default=-1,
    )
    last_failure_index = max(
        (
            idx
            for idx, line in enumerate(relevant)
            if any(
                token in line
                for token in (
                    "FAST_SEND_ERROR",
                    "PASTE_VERIFY_FAIL",
                    "FOCUS_REJECT",
                    "PASTE_REJECT",
                    "INPUT_PROBE_REFUSED",
                    "SUBMIT_UNVERIFIED",
                    "MANUAL_SEND_REQUIRED",
                )
            )
        ),
        default=-1,
    )
    return last_success_index, last_failure_index


@dataclass(frozen=True)
class ChatControlAnalysis:
    detail_bits: list[str]
    command_missing_latest: bool
    chat_metrics: dict[str, int]
    daemon_successes: int
    last_success_index: int
    last_failure_index: int
    last_activity_success_index: int
    last_activity_failure_index: int


def _build_chat_control_detail_bits(
    selected: str,
    relevant: list[str],
    chat_metrics: dict[str, int],
    daemon_successes: int,
    daemon_failures: int,
    activity: list[str],
    command_available: bool,
    command_missing_index: int,
) -> list[str]:
    detail_bits = [
        f"ide={selected}",
        f"entries={len(relevant)}",
        f"fast_send_errors={chat_metrics['fast_send_errors']}",
        f"paste_failures={chat_metrics['paste_failures']}",
        f"focus_rejections={chat_metrics['focus_rejections']}",
        f"paste_rejections={chat_metrics['paste_rejections']}",
        f"input_refusals={chat_metrics['input_refusals']}",
        f"send_successes={chat_metrics['send_successes']}",
        f"submit_unverified={chat_metrics['submit_unverified']}",
        f"manual_send_required={chat_metrics['manual_send_required']}",
    ]
    if activity:
        detail_bits.append(f"daemon_events={len(activity)}")
    if daemon_successes:
        detail_bits.append(f"daemon_successes={daemon_successes}")
    if daemon_failures:
        detail_bits.append(f"daemon_failures={daemon_failures}")
    if command_available:
        detail_bits.append("native_send_command=available")
    if command_missing_index >= 0:
        detail_bits.append("native_send_command_missing_seen=true")
    return detail_bits


def _chat_control_has_failures(chat_metrics: dict[str, int]) -> bool:
    return any(
        (
            chat_metrics["fast_send_errors"],
            chat_metrics["paste_failures"],
            chat_metrics["focus_rejections"],
            chat_metrics["paste_rejections"],
            chat_metrics["input_refusals"],
            chat_metrics["submit_unverified"],
            chat_metrics["manual_send_required"],
        )
    )


def _chat_control_command_hints(project: Path, selected: str) -> list[str]:
    return [
        f"status_command=koru autopilot status --ide {selected} --explain",
        f"probe_command=koru autopilot drive --ide {selected} --require-plugin 'probe test'",
        f"validate_command=koru autopilot trace --project {project} --format drive-dsl --limit 30",
    ]


def _chat_control_recovered_after_retry(
    *,
    last_success_index: int,
    last_failure_index: int,
    last_activity_success_index: int,
    last_activity_failure_index: int,
) -> bool:
    return (
        last_success_index > last_failure_index >= 0
        or last_activity_success_index > last_activity_failure_index
    )


def _chat_control_result(
    *,
    detail_bits: list[str],
    command_missing_latest: bool,
    chat_metrics: dict[str, int],
    daemon_successes: int,
    last_success_index: int,
    last_failure_index: int,
    last_activity_success_index: int,
    last_activity_failure_index: int,
) -> tuple[str, str]:
    if command_missing_latest:
        return WARN, "; ".join(detail_bits + ["native chat command unavailable"])

    if _chat_control_has_failures(chat_metrics):
        if _chat_control_recovered_after_retry(
            last_success_index=last_success_index,
            last_failure_index=last_failure_index,
            last_activity_success_index=last_activity_success_index,
            last_activity_failure_index=last_activity_failure_index,
        ):
            detail_bits.append("recovered_after_retry=true")
        else:
            detail_bits.append("latest_chat_control_failure=true")
        return WARN, "; ".join(detail_bits)

    if chat_metrics["send_successes"] or daemon_successes:
        return PASS, "; ".join(detail_bits + ["chat_control=stable"])
    return WARN, "; ".join(detail_bits + ["no recent paste/submit success observed"])


def _analyze_chat_control(
    selected: str,
    relevant: list[str],
    activity: list[str],
    *,
    count_daemon_metrics: Callable[[list[str]], tuple[int, int, int, int]],
) -> ChatControlAnalysis:
    (
        daemon_successes,
        daemon_failures,
        last_activity_success_index,
        last_activity_failure_index,
    ) = count_daemon_metrics(activity)
    chat_metrics = _count_chat_control_metrics(relevant)
    command_available_index, command_missing_index = _calculate_command_indices(relevant)
    last_success_index, last_failure_index = _calculate_success_failure_indices(relevant)

    return ChatControlAnalysis(
        detail_bits=_build_chat_control_detail_bits(
            selected,
            relevant,
            chat_metrics,
            daemon_successes,
            daemon_failures,
            activity,
            command_available_index >= 0,
            command_missing_index,
        ),
        command_missing_latest=command_missing_index
        > max(command_available_index, last_success_index),
        chat_metrics=chat_metrics,
        daemon_successes=daemon_successes,
        last_success_index=last_success_index,
        last_failure_index=last_failure_index,
        last_activity_success_index=last_activity_success_index,
        last_activity_failure_index=last_activity_failure_index,
    )


def check_autopilot_chat_control(
    project: Path,
    *,
    recent_context: Callable[[], tuple[str, Path, str, list[str], str | None]],
    read_recent_activity: Callable[[Path], list[str]],
    activity_line_mentions_selected: Callable[[str, str], bool],
    count_daemon_metrics: Callable[[list[str]], tuple[int, int, int, int]],
) -> tuple[str, str]:
    try:
        selected, path, _socket_text, relevant, skip_reason = recent_context()
    except OSError as exc:
        return WARN, f"cannot read {project}: {exc}"

    if skip_reason:
        return SKIP, skip_reason
    if not relevant:
        return WARN, f"{path}: no recent chat-control entries for ide={selected}"

    activity = [
        line
        for line in read_recent_activity(project)
        if selected and activity_line_mentions_selected(line, selected)
    ]

    analysis = _analyze_chat_control(
        selected,
        relevant,
        activity,
        count_daemon_metrics=count_daemon_metrics,
    )
    status, detail = _chat_control_result(
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
        detail = "; ".join([detail, *_chat_control_command_hints(project, selected)])
    return status, detail


def _windsurf_chat_column_indexes(
    relevant: list[str],
    *,
    debug_event_has: Callable[[str, str], bool],
) -> dict[str, list[int]]:
    return {
        "send": [
            idx
            for idx, line in enumerate(relevant)
            if debug_event_has(line, "WINDSURF_FASTPATH_EXECUTE_SEND_OK")
            or "winning_paste=windsurf.sendTextToChat" in line
        ],
        "disabled": [
            idx
            for idx, line in enumerate(relevant)
            if debug_event_has(line, "WINDSURF_KEEP_OPEN_DISABLED")
        ],
        "keep_open_ok": [
            idx
            for idx, line in enumerate(relevant)
            if debug_event_has(line, "WINDSURF_KEEP_OPEN_OK")
        ],
        "cascade_toggle": [
            idx
            for idx, line in enumerate(relevant)
            if debug_event_has(line, "WINDSURF_KEEP_OPEN_OK")
            and _windsurf_line_mentions_chat_open_command(line)
        ],
    }


def _windsurf_line_mentions_chat_open_command(line: str) -> bool:
    return any(
        marker in line
        for marker in ("cascadePanel.open", "showCascade", "openChat", "panel.chat")
    )


def _windsurf_chat_column_detail_bits(
    relevant: list[str],
    indexes: dict[str, list[int]],
) -> list[str]:
    return [
        "ide=windsurf",
        f"entries={len(relevant)}",
        f"native_sends={len(indexes['send'])}",
        f"keep_open_ok={len(indexes['keep_open_ok'])}",
        f"post_send_toggle_candidates={len(indexes['cascade_toggle'])}",
        f"keep_open_disabled={len(indexes['disabled'])}",
    ]


def _windsurf_chat_column_result(
    indexes: dict[str, list[int]],
    detail_bits: list[str],
) -> tuple[str, str]:
    last_send = max(indexes["send"], default=-1)
    last_disabled = max(indexes["disabled"], default=-1)
    last_toggle = max(indexes["cascade_toggle"], default=-1)
    if last_toggle > last_disabled and last_toggle > -1:
        return WARN, "; ".join(
            detail_bits
            + [
                "risk=post_send_cascade_open_may_toggle_right_chat_column",
                "upgrade_plugin_or_keep koruAutopilot.windsurfKeepOpenAfterSend=false",
            ]
        )
    if last_disabled > last_send >= 0:
        return PASS, "; ".join(detail_bits + ["post_send_keep_open_guard=disabled"])
    if last_send >= 0 and not indexes["disabled"] and not indexes["keep_open_ok"]:
        return WARN, "; ".join(
            detail_bits
            + ["post_send_keep_open_guard=unknown", "reload IDE if plugin was just upgraded"]
        )
    return PASS, "; ".join(detail_bits + ["no post-send toggle evidence"])


def check_windsurf_chat_column_control(
    *,
    recent_context: Callable[[], tuple[str, Path, str, list[str], str | None]],
    debug_event_has: Callable[[str, str], bool],
) -> tuple[str, str]:
    try:
        selected, path, _socket_text, relevant, skip_reason = recent_context()
    except OSError as exc:
        return WARN, f"cannot read debug context: {exc}"
    if skip_reason:
        return SKIP, skip_reason
    if selected != "windsurf":
        return SKIP, f"ide={selected or '-'}; only applicable to windsurf"
    if not relevant:
        return WARN, f"{path}: no recent Windsurf chat-column entries"

    indexes = _windsurf_chat_column_indexes(relevant, debug_event_has=debug_event_has)
    detail_bits = _windsurf_chat_column_detail_bits(relevant, indexes)
    return _windsurf_chat_column_result(indexes, detail_bits)


def _ide_console_log_roots(selected: str) -> list[Path]:
    override = os.environ.get("KORU_IDE_CONSOLE_LOG_DIR")
    if override:
        return [Path(override).expanduser()]
    home = Path.home()
    roots: dict[str, list[Path]] = {
        "windsurf": [home / ".config" / "Windsurf" / "logs"],
        "antigravity": [home / ".config" / "Antigravity" / "logs"],
        "vscode": [home / ".config" / "Code" / "logs"],
        "vscodium": [home / ".config" / "VSCodium" / "logs"],
        "cursor": [home / ".config" / "Cursor" / "logs"],
    }
    return roots.get(selected, [])


def _recent_ide_console_log_files(selected: str, *, max_sessions: int = 5) -> list[Path]:
    files: list[Path] = []
    for root in _ide_console_log_roots(selected):
        if not root.is_dir():
            continue
        sessions = sorted(
            (path for path in root.iterdir() if path.is_dir()),
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )[:max_sessions]
        root_files = [path for path in root.iterdir() if path.is_file()]
        for session in sessions:
            files.extend(
                path
                for path in session.rglob("*")
                if path.is_file() and path.suffix.lower() in {".log", ".txt"}
            )
        files.extend(path for path in root_files if path.suffix.lower() in {".log", ".txt"})
    return sorted(files, key=lambda path: path.stat().st_mtime, reverse=True)


def _read_recent_ide_console_lines(
    files: list[Path],
    *,
    per_file_limit: int = 120,
) -> list[tuple[Path, str]]:
    rows: list[tuple[Path, str]] = []
    for path in files[:30]:
        try:
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue
        rows.extend((path, line) for line in lines[-per_file_limit:] if line.strip())
    return rows


def _ide_console_line_is_interesting(line: str) -> bool:
    lowered = line.lower()
    tokens = (
        "[error]",
        " error ",
        " err ",
        "[warn]",
        " warn ",
        "warning",
        "exception",
        "rejected promise",
        "trustedscript",
        "trustedtypepolicy",
        "trustedstring",
        "trusted types",
        "language server has not been started",
        "cannot register",
        "already registered",
        "overwriting grammar scope",
        "marketplace",
        "404",
        "500",
        "acknowledgecascadecodeedit",
        "file or directory",
        "does not exist",
        "unable to read file",
        "app icon customization is not supported",
        "failed to find pyright executable",
        "lifecyclephase.restored",
        "extension host",
        "koru",
        "windsurf",
        "cascade",
        "chat",
    )
    return any(token in lowered for token in tokens)


def _ide_console_line_is_diagnostic_headline(line: str) -> bool:
    stripped = line.strip()
    if stripped.startswith("at ") or stripped.startswith("at async "):
        return False
    lowered = stripped.lower()
    return any(
        token in lowered
        for token in (
            "[error]",
            "[warn]",
            "console.error",
            "console.warn",
            " error:",
            " warn ",
            " warning",
            "rejected promise",
            "trustedscript",
            "trustedtypepolicy",
            "trustedstring",
            "trusted types",
            "language server has not been started",
            "cannot register",
            "already registered",
            "overwriting grammar scope",
            "marketplace",
            "acknowledgecascadecodeedit",
            "file or directory",
            "does not exist",
            "unable to read file",
            "app icon customization is not supported",
            "failed to find pyright executable",
            "lifecyclephase.restored",
        )
    )


def _compact_console_excerpt(path: Path, line: str, *, max_len: int = 220) -> str:
    text = re.sub(r"\s+", " ", line).strip()
    if len(text) > max_len:
        text = text[: max_len - 3].rstrip() + "..."
    parent = path.parent.name
    label = f"{parent}/{path.name}" if parent else path.name
    return f"{label}: {text}"


_IDE_CONSOLE_WARN_TOKENS: tuple[str, ...] = (
    "warn",
    "trustedscript",
    "trustedtypepolicy",
    "trustedstring",
    "trusted types",
    "rejected promise",
    "cannot register",
    "already registered",
    "overwriting grammar scope",
    "language server has not been started",
    "lifecyclephase.restored",
)


_IDE_CONSOLE_CATEGORY_PATTERNS: dict[str, tuple[tuple[str, ...], ...]] = {
    "trusted_types": (
        ("trustedscript",),
        ("trustedtypepolicy",),
        ("trustedstring",),
        ("trusted types",),
    ),
    "language_server_not_started": (("language server has not been started",),),
    "extension_registration": (("cannot register",), ("already registered",)),
    "grammar_scope_overwrite": (("overwriting grammar scope",),),
    "missing_extension_file": (("unable to read file", "nonexistent file"),),
    "missing_workspace_path": (("file or directory", "does not exist"),),
    "marketplace_404": (("marketplace", "404"),),
    "cascade_rpc_500": (("acknowledgecascadecodeedit", "500"),),
    "cascade_panel_early_restore": (("windsurf.cascadepanel", "lifecyclephase.restored"),),
    "app_icon_unsupported": (("app icon customization is not supported",),),
    "pyright_fallback": (("failed to find pyright executable",),),
}


def _ide_console_error_count(headlines: list[tuple[Path, str]]) -> int:
    return sum("error" in line.lower() or "[err" in line.lower() for _path, line in headlines)


def _ide_console_warn_count(headlines: list[tuple[Path, str]]) -> int:
    return sum(
        any(token in line.lower() for token in _IDE_CONSOLE_WARN_TOKENS)
        for _path, line in headlines
    )


def _ide_console_category_counts(interesting: list[tuple[Path, str]]) -> list[str]:
    counts: list[str] = []
    for name, patterns in _IDE_CONSOLE_CATEGORY_PATTERNS.items():
        count = sum(
            any(all(token in line.lower() for token in pattern) for pattern in patterns)
            for _path, line in interesting
        )
        if count:
            counts.append(f"{name}={count}")
    return counts


def _classify_ide_console_lines(
    rows: list[tuple[Path, str]],
) -> tuple[list[tuple[Path, str]], list[tuple[Path, str]], list[tuple[Path, str]]]:
    interesting = [
        (path, line) for path, line in rows if _ide_console_line_is_interesting(line)
    ]
    headlines = [
        (path, line)
        for path, line in interesting
        if _ide_console_line_is_diagnostic_headline(line)
    ]
    sample_rows = headlines or interesting
    return interesting, headlines, sample_rows


def _ide_console_build_detail(
    selected: str,
    existing_roots: list[Path],
    files: list[Path],
    interesting: list[tuple[Path, str]],
    error_count: int,
    warn_count: int,
    category_counts: list[str],
    sample_rows: list[tuple[Path, str]],
) -> str:
    detail = (
        f"ide={selected}; roots={','.join(str(path) for path in existing_roots)}; "
        f"files={len(files)}; interesting={len(interesting)}; errors={error_count}; "
        f"warnings={warn_count}"
    )
    if category_counts:
        detail += "; categories=" + ",".join(category_counts)
    if sample_rows:
        samples = [_compact_console_excerpt(path, line) for path, line in sample_rows[-3:]]
        detail += "; latest=" + " | ".join(samples)
    return detail


def check_ide_console_log(
    *,
    selected_autopilot_ide: Callable[[], str],
) -> tuple[str, str]:
    selected = selected_autopilot_ide()
    if not selected:
        return SKIP, "autopilot env unset"
    roots = _ide_console_log_roots(selected)
    if not roots:
        return SKIP, f"no known console log root for ide={selected}"
    existing_roots = [path for path in roots if path.is_dir()]
    if not existing_roots:
        roots_text = ", ".join(str(path) for path in roots)
        return WARN, f"ide={selected}; log root missing: {roots_text}"

    try:
        files = _recent_ide_console_log_files(selected)
        rows = _read_recent_ide_console_lines(files)
    except OSError as exc:
        return WARN, f"ide={selected}; cannot read console logs: {exc}"
    if not files:
        roots_text = ", ".join(str(path) for path in existing_roots)
        return WARN, f"ide={selected}; no log files found under {roots_text}"
    if not rows:
        return WARN, f"ide={selected}; files={len(files)}; no readable recent log lines"

    interesting, headlines, sample_rows = _classify_ide_console_lines(rows)
    error_count = _ide_console_error_count(headlines)
    warn_count = _ide_console_warn_count(headlines)
    category_counts = _ide_console_category_counts(interesting)
    detail = _ide_console_build_detail(
        selected,
        existing_roots,
        files,
        interesting,
        error_count,
        warn_count,
        category_counts,
        sample_rows,
    )
    if error_count or warn_count:
        return WARN, detail
    return PASS, detail + "; no recent warnings/errors"
