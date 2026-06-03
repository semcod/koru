"""Chat-control log analysis helpers for ``koru doctor``."""

from __future__ import annotations

from dataclasses import dataclass

from koru.doctor_constants import PASS, WARN


def autopilot_debug_event_name(line: str) -> str:
    parts = line.split(maxsplit=2)
    if len(parts) < 2 or not parts[0][:4].isdigit():
        return ""
    return parts[1]


def autopilot_debug_event_has(line: str, token: str) -> bool:
    event_name = autopilot_debug_event_name(line)
    if event_name == token:
        return True
    return event_name == "OUT" and token in line


def activity_line_mentions_selected(line: str, selected: str) -> bool:
    return (
        f"ide={selected}" in line
        or f"'ide': '{selected}'" in line
        or f'"ide": "{selected}"' in line
        or f'"ide":"{selected}"' in line
    )


def count_daemon_metrics(activity: list[str]) -> tuple[int, int, int, int]:
    daemon_successes = sum(
        any(token in line for token in ("autopilot: ok", "drive wynik: ok=True", "message.sent"))
        for line in activity
    )
    daemon_failures = sum(
        any(
            token in line
            for token in (
                "verification=plugin_error",
                "verification=submit_unverified",
                "autopilot skipped",
                "autopilot: failed",
                "manual_send_required",
            )
        )
        for line in activity
    )
    last_activity_success_index = max(
        (
            idx
            for idx, line in enumerate(activity)
            if any(
                token in line
                for token in ("autopilot: ok", "drive wynik: ok=True", "message.sent")
            )
        ),
        default=-1,
    )
    last_activity_failure_index = max(
        (
            idx
            for idx, line in enumerate(activity)
            if any(
                token in line
                for token in (
                    "verification=plugin_error",
                    "verification=submit_unverified",
                    "autopilot skipped",
                    "autopilot: failed",
                    "manual_send_required",
                )
            )
        ),
        default=-1,
    )
    return (
        daemon_successes,
        daemon_failures,
        last_activity_success_index,
        last_activity_failure_index,
    )


def count_chat_control_metrics(relevant: list[str]) -> dict[str, int]:
    fast_send_errors = sum(
        autopilot_debug_event_has(line, "WINDSURF_FASTPATH_EXECUTE_SEND_ERROR")
        for line in relevant
    )
    paste_failures = sum(
        autopilot_debug_event_has(line, "chat opened but paste command failed")
        for line in relevant
    )
    focus_rejections = sum(
        autopilot_debug_event_has(line, "PROBE_FOCUS_REJECT")
        for line in relevant
    )
    paste_rejections = sum(
        autopilot_debug_event_has(line, "PROBE_PASTE_REJECT")
        for line in relevant
    )
    input_refusals = sum(
        autopilot_debug_event_has(line, token)
        for line in relevant
        for token in (
            "HOST_PASTE_NO_INPUT_FOCUS",
            "PROBE_PASTE_NO_INPUT_FOCUS",
            "TYPE_PASTE_NO_INPUT_FOCUS_REFUSED",
            "FOCUS_INPUT_ALL_FAILED",
        )
    )
    send_successes = sum(
        autopilot_debug_event_has(line, token)
        for line in relevant
        for token in (
            "WINDSURF_FASTPATH_EXECUTE_SEND_OK",
            "winning_paste=windsurf.sendTextToChat",
            "winning_submit=windsurf.sendTextToChat",
            "message.sent",
        )
    )
    submit_unverified = sum(
        "submit_unverified" in line or "intent_not_validated" in line
        for line in relevant
    )
    manual_send_required = sum("manual_send_required" in line for line in relevant)
    return {
        "fast_send_errors": fast_send_errors,
        "paste_failures": paste_failures,
        "focus_rejections": focus_rejections,
        "paste_rejections": paste_rejections,
        "input_refusals": input_refusals,
        "send_successes": send_successes,
        "submit_unverified": submit_unverified,
        "manual_send_required": manual_send_required,
    }


def calculate_command_indices(relevant: list[str]) -> tuple[int, int]:
    command_available_index = max(
        (
            idx
            for idx, line in enumerate(relevant)
            if autopilot_debug_event_has(line, "WINDSURF_FASTPATH_CHECK_COMMAND")
            and '"hasSendCmd":true' in line
        ),
        default=-1,
    )
    command_missing_index = max(
        (
            idx
            for idx, line in enumerate(relevant)
            if autopilot_debug_event_has(line, "WINDSURF_FASTPATH_ABORT_MISSING_COMMAND")
            or (
                autopilot_debug_event_has(line, "WINDSURF_FASTPATH_CHECK_COMMAND")
                and '"hasSendCmd":false' in line
            )
        ),
        default=-1,
    )
    return command_available_index, command_missing_index


def calculate_success_failure_indices(relevant: list[str]) -> tuple[int, int]:
    last_failure_index = max(
        (
            idx
            for idx, line in enumerate(relevant)
            if any(
                autopilot_debug_event_has(line, token)
                for token in (
                    "WINDSURF_FASTPATH_EXECUTE_SEND_ERROR",
                    "chat opened but paste command failed",
                    "PROBE_FOCUS_REJECT",
                    "PROBE_PASTE_REJECT",
                    "HOST_PASTE_NO_INPUT_FOCUS",
                    "PROBE_PASTE_NO_INPUT_FOCUS",
                    "TYPE_PASTE_NO_INPUT_FOCUS_REFUSED",
                    "FOCUS_INPUT_ALL_FAILED",
                )
            )
        ),
        default=-1,
    )
    last_success_index = max(
        (
            idx
            for idx, line in enumerate(relevant)
            if any(
                autopilot_debug_event_has(line, token)
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


def build_chat_control_detail_bits(
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


def chat_control_has_failures(chat_metrics: dict[str, int]) -> bool:
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


def chat_control_command_hints(project: object, selected: str) -> list[str]:
    return [
        f"status_command=koru autopilot status --ide {selected} --explain",
        f"probe_command=koru autopilot drive --ide {selected} --require-plugin 'probe test'",
        f"validate_command=koru autopilot trace --project {project} --format drive-dsl --limit 30",
    ]


def chat_control_recovered_after_retry(
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


def chat_control_result(
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

    if chat_control_has_failures(chat_metrics):
        if chat_control_recovered_after_retry(
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


def analyze_chat_control(
    selected: str,
    relevant: list[str],
    activity: list[str],
) -> ChatControlAnalysis:
    (
        daemon_successes,
        daemon_failures,
        last_activity_success_index,
        last_activity_failure_index,
    ) = count_daemon_metrics(activity)
    chat_metrics = count_chat_control_metrics(relevant)
    command_available_index, command_missing_index = calculate_command_indices(relevant)
    last_success_index, last_failure_index = calculate_success_failure_indices(relevant)

    return ChatControlAnalysis(
        detail_bits=build_chat_control_detail_bits(
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


def windsurf_chat_column_indexes(relevant: list[str]) -> dict[str, list[int]]:
    return {
        "send": [
            idx
            for idx, line in enumerate(relevant)
            if autopilot_debug_event_has(line, "WINDSURF_FASTPATH_EXECUTE_SEND_OK")
            or "winning_paste=windsurf.sendTextToChat" in line
        ],
        "disabled": [
            idx
            for idx, line in enumerate(relevant)
            if autopilot_debug_event_has(line, "WINDSURF_KEEP_OPEN_DISABLED")
        ],
        "keep_open_ok": [
            idx
            for idx, line in enumerate(relevant)
            if autopilot_debug_event_has(line, "WINDSURF_KEEP_OPEN_OK")
        ],
        "cascade_toggle": [
            idx
            for idx, line in enumerate(relevant)
            if autopilot_debug_event_has(line, "WINDSURF_KEEP_OPEN_OK")
            and windsurf_line_mentions_chat_open_command(line)
        ],
    }


def windsurf_line_mentions_chat_open_command(line: str) -> bool:
    return any(
        marker in line
        for marker in ("cascadePanel.open", "showCascade", "openChat", "panel.chat")
    )


def windsurf_chat_column_detail_bits(
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


def windsurf_chat_column_result(
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
