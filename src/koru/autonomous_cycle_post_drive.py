from pathlib import Path
from typing import Any

from koru.autonomous_cycle_common import _queue_loop_waiting_ticket_label
from koru.autonomy.autopilot_status import parse_autopilot_status
from koru.autonomy.decision_arbiter import ArbiterSignals, decide
from koru.autonomy.planning_llm import (
    evaluate_drive_result as _llm_evaluate_drive_result,
    generate_better_prompt as _llm_generate_better_prompt,
    get_budget_tracker as _get_planning_budget,
)
from koru.autonomy.state import AutoloopState
from koru.autonomy.verification_engine import (
    Verdict,
    assess_verdict,
    collect_evidence,
    take_snapshot,
)
from koru.queue import QueueLoopResult


def _take_pre_drive_snapshot(
    project: Path,
    state: AutoloopState,
    wup_health: Any,
) -> None:
    """Capture project state before autopilot drive (ADR AUTO-002 Phase 1)."""
    test_status = str(getattr(wup_health, "status", "unknown") or "unknown")
    snapshot = take_snapshot(project, test_status=test_status)
    state.last_drive_snapshot = snapshot.to_dict()


def _drive_effect_payload(
    *,
    ticket_id: str,
    queue_status: str,
    evidence: Any,
    drive_status: str,
) -> dict[str, Any]:
    prompt_submitted = drive_status == "ok" and bool(evidence.chat.has_message_sent)
    ticket_still_waiting = queue_status == "waiting_input" and bool(ticket_id)
    work_applied = evidence.git.files_changed > 0 or not ticket_still_waiting
    planfile_delta = "still_waiting_input" if ticket_still_waiting else queue_status or "unknown"
    return {
        "prompt_submitted": prompt_submitted,
        "work_applied": work_applied,
        "ticket_before": ticket_id or "-",
        "ticket_after": ticket_id if ticket_still_waiting else "-",
        "git_delta": {
            "files_changed": evidence.git.files_changed,
            "insertions": evidence.git.insertions,
            "deletions": evidence.git.deletions,
        },
        "planfile_delta": planfile_delta,
        "test_delta": evidence.tests.status,
        "chat_events_since_drive": evidence.chat.events_since_drive,
    }


def _submitted_but_no_effect(verdict: Verdict, effect: dict[str, Any]) -> Verdict:
    reason = (
        "prompt_submitted=true; work_applied=false; "
        f"git_delta={effect['git_delta']['files_changed']} files; "
        f"planfile_delta={effect['planfile_delta']}; "
        f"test_delta={effect['test_delta']}"
    )
    return Verdict(
        outcome="submitted_but_no_effect",
        confidence=0.95,
        reason=reason,
        evidence=verdict.evidence,
        ticket_id=verdict.ticket_id,
    )


def _snapshot_before_drive(state: AutoloopState) -> Any | None:
    from koru.autonomy.verification_engine import Snapshot

    snap_dict = state.last_drive_snapshot
    if not snap_dict:
        return None
    return Snapshot(
        git_head=str(snap_dict.get("git_head", "")),
        git_dirty_count=int(snap_dict.get("git_dirty_count", 0)),
        test_status=str(snap_dict.get("test_status", "unknown")),
        timestamp=float(snap_dict.get("timestamp", 0)),
    )


def _post_drive_ticket_id(queue_result: QueueLoopResult) -> str:
    waiting_ticket = _queue_loop_waiting_ticket_label(queue_result)
    return "" if waiting_ticket == "-" else waiting_ticket


def _update_drive_count(state: AutoloopState, ticket_id: str) -> None:
    if not ticket_id:
        return
    if ticket_id == state.last_driven_ticket_for_count:
        state.drive_count_for_ticket += 1
        return
    state.drive_count_for_ticket = 1
    state.last_driven_ticket_for_count = ticket_id


def _collect_post_drive_evidence(
    project: Path,
    state: AutoloopState,
    wup_health: Any,
) -> Any:
    return collect_evidence(
        project,
        before=_snapshot_before_drive(state),
        wup_health=wup_health,
        autopilot_events=state.autopilot_events,
        drive_timestamp=state.last_message_sent_ts,
    )


def _post_drive_verdict(
    state: AutoloopState,
    evidence: Any,
    ticket_id: str,
    effect: dict[str, Any],
) -> Verdict:
    verdict = assess_verdict(
        evidence,
        ticket_id=ticket_id,
        drive_count=state.drive_count_for_ticket,
    )
    if effect["prompt_submitted"] and not effect["work_applied"]:
        return _submitted_but_no_effect(verdict, effect)
    return verdict


def _emit_drive_effect_if_needed(
    cycle: int,
    ticket_id: str,
    effect: dict[str, Any],
    hp: callable,
    emit: callable,
) -> None:
    if not (effect["prompt_submitted"] and not effect["work_applied"]):
        return
    hp(
        "  drive_effect: submitted_but_no_effect "
        f"ticket={ticket_id or '-'} git_delta={effect['git_delta']['files_changed']} "
        f"planfile_delta={effect['planfile_delta']} test_delta={effect['test_delta']}"
    )
    emit(
        "DriveEffect",
        {
            "cycle": cycle,
            "ticket_id": ticket_id,
            **effect,
        },
    )


def _emit_drive_verdict(
    *,
    cycle: int,
    ticket_id: str,
    verdict: Verdict,
    drive_count: int,
    drive_status: str,
    evidence: Any,
    effect: dict[str, Any],
    hp: callable,
    emit: callable,
) -> None:
    hp(
        f"  verdict: {verdict.outcome} (confidence={verdict.confidence:.2f}) "
        f"ticket={ticket_id or '-'} drives={drive_count}"
    )
    emit(
        "DriveVerdict",
        {
            "cycle": cycle,
            "ticket_id": ticket_id,
            "outcome": verdict.outcome,
            "confidence": verdict.confidence,
            "reason": verdict.reason,
            "drive_count": drive_count,
            "autopilot_status": drive_status,
            "git_files_changed": evidence.git.files_changed,
            "test_status": evidence.tests.status,
            "chat_events_since_drive": evidence.chat.events_since_drive,
            "prompt_submitted": effect["prompt_submitted"],
            "work_applied": effect["work_applied"],
            "git_delta": effect["git_delta"],
            "planfile_delta": effect["planfile_delta"],
            "test_delta": effect["test_delta"],
        },
    )


def _maybe_emit_llm_evaluation(
    *,
    cycle: int,
    ticket_id: str,
    queue_result: QueueLoopResult,
    state: AutoloopState,
    verdict: Verdict,
    evidence: Any,
    hp: callable,
    emit: callable,
) -> None:
    try:
        llm_eval = _llm_evaluate_drive_result(
            evidence,
            ticket_id=ticket_id,
            ticket_title=str(getattr(queue_result, "last_message", "") or ""),
            driven_prompt=state.last_driven_prompt,
            heuristic_verdict=verdict,
        )
    except Exception:  # noqa: BLE001
        return
    if llm_eval is None:
        return
    hp(
        f"  llm_eval: {llm_eval.outcome} (confidence={llm_eval.confidence:.2f}) "
        f"{llm_eval.reason[:80]}"
    )
    emit(
        "LlmEvaluation",
        {
            "cycle": cycle,
            "ticket_id": ticket_id,
            "outcome": llm_eval.outcome,
            "confidence": llm_eval.confidence,
            "reason": llm_eval.reason,
            "suggestion": llm_eval.suggestion,
        },
    )


def _maybe_emit_improved_prompt(
    *,
    cycle: int,
    ticket_id: str,
    queue_result: QueueLoopResult,
    state: AutoloopState,
    verdict: Verdict,
    hp: callable,
    emit: callable,
) -> None:
    if not (
        verdict.outcome == "no_change"
        and state.drive_count_for_ticket >= 2
        and state.last_driven_prompt
    ):
        return
    try:
        llm_improved_prompt = _llm_generate_better_prompt(
            ticket_id=ticket_id,
            ticket_title=str(getattr(queue_result, "last_message", "") or ""),
            original_prompt=state.last_driven_prompt,
            drive_count=state.drive_count_for_ticket,
            last_verdict_reason=verdict.reason,
        )
    except Exception:  # noqa: BLE001
        return
    if not llm_improved_prompt:
        return
    hp(f"  llm_prompt: improved prompt generated ({len(llm_improved_prompt)} chars)")
    emit(
        "LlmImprovedPrompt",
        {
            "cycle": cycle,
            "ticket_id": ticket_id,
            "original_length": len(state.last_driven_prompt),
            "improved_length": len(llm_improved_prompt),
        },
    )


def _emit_post_drive_action_plan(
    *,
    cycle: int,
    queue_result: QueueLoopResult,
    state: AutoloopState,
    evidence: Any,
    verdict: Verdict,
    ticket_id: str,
    hp: callable,
    emit: callable,
) -> None:
    _get_planning_budget().reset_cycle()
    signals = ArbiterSignals(
        queue_status=str(queue_result.last_status or ""),
        waiting_ticket=ticket_id,
        stagnation_streak=state.stagnation_streak,
        drive_count_for_ticket=state.drive_count_for_ticket,
        test_status=evidence.tests.status,
        verdict=verdict,
        has_open_tickets=bool(getattr(queue_result, "waiting", None)),
    )
    plan = decide(signals)
    state.last_drive_action_plan = plan.to_dict()

    hp(
        f"  decision: {plan.action} "
        f"(reason={plan.reason!r}, confidence={plan.confidence:.2f})"
    )
    emit(
        "ActionPlan",
        {
            "cycle": cycle,
            "action": plan.action,
            "ticket_id": plan.ticket_id,
            "reason": plan.reason,
            "confidence": plan.confidence,
            "sleep_seconds": plan.sleep_seconds,
        },
    )


def _handle_post_drive_verification(
    project: Path,
    state: AutoloopState,
    cycle: int,
    queue_result: QueueLoopResult,
    drive_status: str,
    wup_health: Any,
    _hp: callable,
    _emit: callable,
) -> None:
    """Collect evidence and assess verdict after autopilot drive (ADR AUTO-002 Phase 1)."""
    status = parse_autopilot_status(drive_status)
    if not (status.ok or status.failed):
        return

    ticket_id = _post_drive_ticket_id(queue_result)
    _update_drive_count(state, ticket_id)
    evidence = _collect_post_drive_evidence(project, state, wup_health)
    effect = _drive_effect_payload(
        ticket_id=ticket_id,
        queue_status=str(queue_result.last_status or ""),
        evidence=evidence,
        drive_status=drive_status,
    )
    verdict = _post_drive_verdict(state, evidence, ticket_id, effect)
    state.last_drive_verdict = verdict.to_dict()

    _emit_drive_effect_if_needed(cycle, ticket_id, effect, _hp, _emit)
    _emit_drive_verdict(
        cycle=cycle,
        ticket_id=ticket_id,
        verdict=verdict,
        drive_count=state.drive_count_for_ticket,
        drive_status=drive_status,
        evidence=evidence,
        effect=effect,
        hp=_hp,
        emit=_emit,
    )
    _maybe_emit_llm_evaluation(
        cycle=cycle,
        ticket_id=ticket_id,
        queue_result=queue_result,
        state=state,
        verdict=verdict,
        evidence=evidence,
        hp=_hp,
        emit=_emit,
    )
    _maybe_emit_improved_prompt(
        cycle=cycle,
        ticket_id=ticket_id,
        queue_result=queue_result,
        state=state,
        verdict=verdict,
        hp=_hp,
        emit=_emit,
    )
    _emit_post_drive_action_plan(
        cycle=cycle,
        queue_result=queue_result,
        state=state,
        evidence=evidence,
        verdict=verdict,
        ticket_id=ticket_id,
        hp=_hp,
        emit=_emit,
    )
