"""Cycle telemetry and Phase 4 planning-LLM advisory helpers.

Extracted verbatim from ``koru.autonomous_cycle`` (STARTER-545). The legacy
``_underscored`` names remain importable from ``koru.autonomous_cycle`` via
``import as`` re-exports so existing tests/callers keep working unchanged.

Cross-module calls to names that tests monkeypatch on the facade
(``_load_open_tickets_for_planning``, ``_llm_prioritize_tickets``,
``load_autonomy_strategy``, ``load_recent_decisions``,
``_llm_propose_strategy_tuning``, ``_run_process``) are resolved late via
``from koru import autonomous_cycle as _cycle_mod`` at call time.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from koru.env_flags import env_truthy as _env_truthy
from koru.environment_profile import environment_profile_payload
from koru.autonomy.state import AutoloopState
from koru.queue import QueueLoopResult
from koru.queue.ticket import planfile_command


def _initialize_cycle_telemetry() -> dict[str, Any]:
    return {
        "autopilot_skipped_idle_streak": False,
        "scan_after_idle_run": False,
        "scan_after_idle_applied": 0,
        "scan_after_idle_skipped_rate_limit": False,
    }


def _load_open_tickets_for_planning(
    project: Path,
    *,
    queue_name: str | None,
) -> list[dict[str, Any]]:
    payload = _load_planfile_ticket_payload(project)
    if payload is None:
        return []
    return [
        row
        for item in payload
        if isinstance(item, dict)
        for row in [_planning_ticket_row(item, queue_name)]
        if row is not None
    ]


def _load_planfile_ticket_payload(project: Path) -> list[Any] | None:
    from koru import autonomous_cycle as _cycle_mod

    try:
        result = planfile_command(
            project,
            ["ticket", "list", "--format", "json"],
            runner=lambda command, cwd: _cycle_mod._run_process(list(command), cwd),
        )
    except Exception:  # noqa: BLE001
        return []
    if result.returncode != 0:
        return []
    try:
        payload = json.loads((result.stdout or "").strip() or "[]")
    except json.JSONDecodeError:
        return None
    if isinstance(payload, dict):
        payload = [payload]
    if not isinstance(payload, list):
        return None
    return payload


def _planning_ticket_row(item: dict[str, Any], queue_name: str | None) -> dict[str, Any] | None:
    closed = {"done", "closed", "cancelled", "canceled"}
    ticket_id = str(item.get("id") or "").strip()
    ticket_queue = str(item.get("queue") or "").strip() or None
    status = str(item.get("status") or "open").strip().lower()
    if not ticket_id or status in closed:
        return None
    if queue_name and ticket_queue and ticket_queue != queue_name:
        return None
    return {
        "id": ticket_id,
        "title": str(item.get("name") or item.get("title") or "").strip(),
        "status": status,
    }


def _recent_verdicts_for_planning(state: AutoloopState) -> list[dict[str, Any]] | None:
    last_verdict = getattr(state, "last_drive_verdict", None)
    if isinstance(last_verdict, dict):
        return [last_verdict]
    if last_verdict is not None and callable(getattr(last_verdict, "to_dict", None)):
        return [last_verdict.to_dict()]
    return None


def _run_phase4_ticket_priority_advice(
    *,
    project: Path,
    state: AutoloopState,
    cycle: int,
    queue_name: str | None,
    cycle_telemetry: dict[str, Any],
    _hp: callable,
    _emit: callable,
) -> None:
    from koru import autonomous_cycle as _cycle_mod

    try:
        tickets = _cycle_mod._load_open_tickets_for_planning(project, queue_name=queue_name)
        advice = _cycle_mod._llm_prioritize_tickets(
            tickets=tickets,
            test_status="unknown",
            recent_verdicts=_recent_verdicts_for_planning(state),
        )
    except Exception:  # noqa: BLE001
        advice = None
    if advice is None:
        return
    payload = {
        "cycle": cycle,
        "ordered_ticket_ids": list(advice.ordered_ticket_ids),
        "reason": advice.reason,
        "confidence": advice.confidence,
    }
    cycle_telemetry["llm_ticket_priority"] = payload
    _emit("LlmTicketPriority", payload)
    _hp(
        "  llm_ticket_priority: "
        f"{len(advice.ordered_ticket_ids)} tickets (confidence={advice.confidence:.2f})",
    )


def _run_phase4_strategy_tuning_advice(
    *,
    project: Path,
    cycle: int,
    cycle_telemetry: dict[str, Any],
    _hp: callable,
    _emit: callable,
) -> None:
    from koru import autonomous_cycle as _cycle_mod

    try:
        strategy = _cycle_mod.load_autonomy_strategy(project) or {}
        recent_decisions = _cycle_mod.load_recent_decisions(project, limit=20)
        strategy_doc = json.dumps(strategy, ensure_ascii=False, indent=2)
        tuning = _cycle_mod._llm_propose_strategy_tuning(
            current_strategy_yaml=strategy_doc,
            recent_decisions=recent_decisions,
            cycle_metrics=cycle_telemetry,
        )
    except Exception:  # noqa: BLE001
        tuning = None
    if tuning is None:
        return
    payload = {
        "cycle": cycle,
        "reason": tuning.reason,
        "confidence": tuning.confidence,
        "patch": tuning.patch,
    }
    cycle_telemetry["llm_strategy_tuning"] = {
        "reason": tuning.reason,
        "confidence": tuning.confidence,
        "patch_preview": tuning.patch[:200],
    }
    _emit("LlmStrategyTuningAdvice", payload)
    _hp(f"  llm_strategy_tuning: confidence={tuning.confidence:.2f}")


def _run_phase4_advisory_hooks(
    *,
    project: Path,
    state: AutoloopState,
    cycle: int,
    queue_result: QueueLoopResult,
    queue_name: str | None,
    cycle_telemetry: dict[str, Any],
    _hp: callable,
    _emit: callable,
) -> None:
    """Run optional Phase 4 advisory hooks (no state mutation side effects)."""
    enable_priority = _env_truthy("KORU_PLANNING_LLM_PRIORITIZE_TICKETS")
    enable_tuning = _env_truthy("KORU_PLANNING_LLM_STRATEGY_TUNING")
    if not (enable_priority or enable_tuning):
        return

    if enable_priority:
        _run_phase4_ticket_priority_advice(
            project=project,
            state=state,
            cycle=cycle,
            queue_name=queue_name,
            cycle_telemetry=cycle_telemetry,
            _hp=_hp,
            _emit=_emit,
        )

    if enable_tuning:
        _run_phase4_strategy_tuning_advice(
            project=project,
            cycle=cycle,
            cycle_telemetry=cycle_telemetry,
            _hp=_hp,
            _emit=_emit,
        )


def _attach_environment_profile(
    project: Path,
    cycle_telemetry: dict[str, Any],
    *,
    autopilot_ide: str,
) -> None:
    try:
        cycle_telemetry["environment_profile"] = environment_profile_payload(
            project,
            ide=autopilot_ide,
        )
    except Exception as exc:
        cycle_telemetry["environment_profile_error"] = f"{type(exc).__name__}: {exc}"
