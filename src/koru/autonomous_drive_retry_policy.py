"""Retry-policy side effects for autonomous IDE drive attempts."""

from __future__ import annotations

import time
from typing import Any

from koru.decision_engine import DriveRetryDecision, EnvironmentDecisionEngine


def _format_autopilot_failure_details(reply: dict[str, Any]) -> list[str]:
    lines: list[str] = []
    message = str(reply.get("message") or "").strip()
    if message:
        lines.append(f"Plugin message: {message}")
    diagnostics = reply.get("diagnostics")
    if isinstance(diagnostics, dict):
        for key in ("ide", "appName", "logPath", "probeLadder", "cacheFocusOpen"):
            if key in diagnostics:
                lines.append(f"{key}: {diagnostics[key]}")
        candidates = diagnostics.get("focusOpenCandidates")
        if isinstance(candidates, list):
            preview = ", ".join(str(item) for item in candidates[:8])
            if len(candidates) > 8:
                preview += f", ... (+{len(candidates) - 8})"
            lines.append(f"focusOpenCandidates: {preview or '(none)'}")
        rejected = diagnostics.get("rejected")
        if isinstance(rejected, list) and rejected:
            lines.append(f"lastRejected: {rejected[-1]}")
    elif reply.get("details"):
        lines.append(f"Details: {reply['details']}")
    return lines


def _warn_autopilot_focus_retry(
    attempt: int,
    attempts: int,
    reply: dict[str, Any] | None = None,
) -> None:
    print("\033[1;31m")  # bold red
    print("================================================================================")
    print("[AUTOPILOT FOCUS ERROR] Please place your cursor inside the IDE chat input!")
    print("Make sure the cursor is blinking inside the chat input field.")
    if reply:
        for line in _format_autopilot_failure_details(reply):
            print(line)
    print(f"Retrying in 5 seconds... (Attempt {attempt + 1}/{attempts})")
    print("================================================================================")
    print("\033[0m")  # reset colors


def _warn_autopilot_manual_focus_required(reply: dict[str, Any] | None = None) -> None:
    from koru.activity_log import activity

    print("\033[1;31m")  # bold red
    print("================================================================================")
    print("[AUTOPILOT FOCUS REQUIRED] Please place your cursor inside the IDE chat input.")
    print("No focus-open command is available, so Koru will not retry this drive automatically.")
    if reply:
        for line in _format_autopilot_failure_details(reply):
            print(line)
    print("================================================================================")
    print("\033[0m")  # reset colors
    activity(
        "CHAT",
        "manual focus required; no automatic retry",
        data={"reply": reply or {}},
    )


def _warn_autopilot_plugin_retry(
    attempt: int,
    attempts: int,
    reply: dict[str, Any] | None = None,
) -> None:
    print("\033[1;33m")  # bold yellow
    print("================================================================================")
    print("[AUTOPILOT PLUGIN RETRY] Plugin send did not succeed yet.")
    print("This is usually transient in Windsurf; Koru will retry automatically.")
    if reply:
        for line in _format_autopilot_failure_details(reply):
            print(line)
    print(f"Retrying in 5 seconds... (Attempt {attempt + 1}/{attempts})")
    print("================================================================================")
    print("\033[0m")  # reset colors


def _warn_autopilot_submit_retry(
    attempt: int,
    attempts: int,
    reply: dict[str, Any] | None = None,
) -> None:
    print("\033[1;33m")  # bold yellow
    print("================================================================================")
    print("[AUTOPILOT SUBMIT RETRY] Text was pasted, but Send was not confirmed.")
    print("Koru will retry submit against the existing matching chat input.")
    if reply:
        for line in _format_autopilot_failure_details(reply):
            print(line)
    print(f"Retrying in 5 seconds... (Attempt {attempt + 1}/{attempts})")
    print("================================================================================")
    print("\033[0m")  # reset colors


def _drive_retry_decision(
    reply: dict[str, Any],
    attempt: int,
    attempts: int,
    *,
    engine: EnvironmentDecisionEngine | None = None,
) -> DriveRetryDecision:
    if engine is not None:
        return engine.assess_drive_failure(
            reply,
            attempt=attempt,
            max_attempts=attempts,
        )

    from korullm import resolve_active_llm_strategy

    assessment = resolve_active_llm_strategy().assess_drive_failure(
        reply,
        attempt=attempt,
        max_attempts=attempts,
    )
    should_retry = assessment.kind.startswith("retry_")
    return DriveRetryDecision(
        assessment=assessment,
        should_retry=should_retry,
        should_warn=assessment.warn_banner,
        sleep_seconds=assessment.sleep_seconds if should_retry else 0.0,
    )


def _handle_failed_drive_attempt(
    reply: dict[str, Any],
    attempt: int,
    attempts: int,
    *,
    engine: EnvironmentDecisionEngine | None = None,
) -> bool:
    """Use the decision engine's LLM-axis policy for retry/stop/warn."""
    retry_decision = _drive_retry_decision(
        reply,
        attempt,
        attempts,
        engine=engine,
    )
    kind = retry_decision.assessment.kind
    if kind == "skip_cooldown":
        return False
    if not retry_decision.should_retry:
        if retry_decision.should_warn == "manual_focus":
            _warn_autopilot_manual_focus_required(reply)
        return False
    banner = retry_decision.should_warn
    if banner == "submit":
        _warn_autopilot_submit_retry(attempt, attempts, reply)
    elif banner == "focus":
        _warn_autopilot_focus_retry(attempt, attempts, reply)
    elif banner == "plugin":
        _warn_autopilot_plugin_retry(attempt, attempts, reply)
    if retry_decision.sleep_seconds > 0:
        time.sleep(retry_decision.sleep_seconds)
    return True


__all__ = ["_handle_failed_drive_attempt"]