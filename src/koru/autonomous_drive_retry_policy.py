"""Retry-policy side effects for autonomous IDE drive attempts."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from koru.decision_engine import DriveRetryDecision, EnvironmentDecisionEngine
from koru.integration_ledger import record_integration_action


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
    from koru.autonomy.ide_operator_guidance import (
        chat_focus_operator_steps,
        emit_operator_guidance,
    )

    ide = None
    if reply:
        diagnostics = reply.get("diagnostics")
        if isinstance(diagnostics, dict):
            ide = str(diagnostics.get("ide") or "") or None
    emit_operator_guidance(
        chat_focus_operator_steps(ide, context="focus"),
        title="Operator — chat focus required",
    )
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
    from koru.autonomy.ide_operator_guidance import (
        chat_focus_operator_steps,
        emit_operator_guidance,
    )

    ide = None
    if reply:
        diagnostics = reply.get("diagnostics")
        if isinstance(diagnostics, dict):
            ide = str(diagnostics.get("ide") or "") or None
    emit_operator_guidance(
        chat_focus_operator_steps(ide, context="focus"),
        title="Operator — chat focus required",
    )
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
    from koru.autonomy.ide_operator_guidance import (
        emit_operator_guidance,
        manual_send_operator_steps,
    )

    ide = None
    if reply:
        diagnostics = reply.get("diagnostics")
        if isinstance(diagnostics, dict):
            ide = str(diagnostics.get("ide") or "") or None
    emit_operator_guidance(
        manual_send_operator_steps(ide),
        title="Operator — manual send / chat focus",
    )
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


def _warn_autopilot_semantic_required(reply: dict[str, Any] | None = None) -> None:
    import sys

    from koru.autonomy.ide_operator_guidance import (
        classify_drive_failure_guidance,
        emit_operator_guidance,
    )

    guidance = classify_drive_failure_guidance(reply or {}, ide="jetbrains") or []
    if guidance:
        emit_operator_guidance(
            guidance,
            title="Operator — verified vdisplay/photo-VQL required",
            stream=sys.stdout,
        )
    print("\033[1;33m")  # bold yellow
    print("================================================================================")
    print("[AUTOPILOT SEMANTIC TARGET REQUIRED] Not retrying blind JetBrains/Wayland drive.")
    if reply:
        for line in _format_autopilot_failure_details(reply):
            print(line)
    print("Fix vdisplay/photo-VQL capture first; Koru will not retry as a chat-focus error.")
    print("================================================================================")
    print("\033[0m")  # reset colors


def _drive_retry_decision(
    reply: dict[str, Any],
    attempt: int,
    attempts: int,
    *,
    engine: EnvironmentDecisionEngine | None = None,
) -> DriveRetryDecision:
    from koru.autopilot.drive_repair_policy import daemon_reply_blocks_direct_fallback

    if daemon_reply_blocks_direct_fallback(reply):
        from korullm import DriveFailureAssessment

        return DriveRetryDecision(
            assessment=DriveFailureAssessment(
                kind="semantic_required",
                failure_signature=str(reply.get("backend") or "semantic_required"),
                detail=str(reply.get("message") or "verified semantic target required"),
                warn_banner="semantic_required",
            ),
            should_retry=False,
            should_warn="semantic_required",
        )
    if engine is not None:
        return engine.assess_drive_failure(
            reply,
            attempt=attempt,
            max_attempts=attempts,
        )
    if _submit_retry_is_known_unsafe_without_engine(reply):
        from korullm import DriveFailureAssessment

        return DriveRetryDecision(
            assessment=DriveFailureAssessment(
                kind="stop",
                failure_signature=str(reply.get("verification") or "submit_unverified"),
                detail="submit_unverified_not_retryable",
            ),
            should_retry=False,
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


def _submit_retry_is_known_unsafe_without_engine(reply: dict[str, Any]) -> bool:
    verification = str(reply.get("verification") or "").strip().lower()
    if verification in {"submit_unverified", "submit_failed"}:
        return True
    if reply.get("submitted") is False and (
        reply.get("attempted_submit")
        or reply.get("winning_paste")
        or reply.get("submit_failure_reason")
    ):
        return True
    return "submit could not be verified" in str(reply.get("message") or "").lower()


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
    _record_drive_retry_decision(reply, retry_decision, attempt, attempts, engine=engine)
    if kind == "skip_cooldown":
        return False
    if not retry_decision.should_retry:
        if retry_decision.should_warn == "manual_focus":
            _warn_autopilot_manual_focus_required(reply)
        elif retry_decision.should_warn == "semantic_required":
            _warn_autopilot_semantic_required(reply)
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


def _record_drive_retry_decision(
    reply: dict[str, Any],
    retry_decision: DriveRetryDecision,
    attempt: int,
    attempts: int,
    *,
    engine: EnvironmentDecisionEngine | None,
) -> None:
    ide = getattr(engine, "ide_id", "auto") if engine is not None else "auto"
    project = getattr(engine, "project", None) if engine is not None else None
    if not isinstance(project, Path):
        project = None
    verification = str(reply.get("verification") or "-")
    reason = str(
        reply.get("submit_failure_reason")
        or reply.get("reason")
        or retry_decision.assessment.detail
        or reply.get("message")
        or ""
    )
    record_integration_action(
        project=project,
        action="drive.retry_decision",
        intent="decide whether another IDE interaction is safe",
        actor="autonomous-loop",
        target=str(ide),
        transport=str(reply.get("backend") or "unknown"),
        phase=verification,
        attempt=attempt + 1,
        outcome="retry" if retry_decision.should_retry else "stop",
        reason=reason,
        evidence=(
            f"kind={retry_decision.assessment.kind}; "
            f"warn={retry_decision.should_warn or '-'}; "
            f"sleep={retry_decision.sleep_seconds}; max_attempts={attempts}"
        ),
        next_step=(
            "retry after policy sleep"
            if retry_decision.should_retry
            else "do not paste again; surface root cause to operator"
        ),
        data={"reply": reply, "assessment": retry_decision.assessment.__dict__},
    )


__all__ = ["_handle_failed_drive_attempt"]
