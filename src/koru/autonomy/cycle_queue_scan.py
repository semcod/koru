"""Scan/queue-loop phase helpers for the autonomous cycle.

Extracted verbatim from ``koru.autonomy.cycle.cycle`` (STARTER-545). The legacy
``_underscored`` names remain importable from ``koru.autonomy.cycle.cycle`` via
``import as`` re-exports so existing tests/callers keep working unchanged.

Cross-module calls to names that tests (or ``run_cycle_with_compat``)
monkeypatch on the facade (``run_scan``, ``run_planfile_queue_loop``, the
queue runners, ``verify_completed_tickets``,
``_run_code2llm_discovery_after_idle``) are resolved late via
``from koru import autonomous_cycle as _cycle_mod`` at call time.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from koru.autonomy.cycle.cycle_common import _queue_loop_waiting_ticket_label
from koru.autonomy.phases import queue_phase as _queue_phase
from koru.autonomy.state import AutoloopState
from koru.queue import QueueLoopResult
from koru.scan import ScanResult


def _handle_scan_phase(
    project: Path,
    state: AutoloopState,
    cycle: int,
    enable_scan: bool,
    include_semcod_artifacts: bool | None,
    scan_skip_if_clean: bool,
    scan_skip_after: int,
    topology_integration: bool,
    _hp: callable,
    _emit: callable,
) -> ScanResult | None:
    from koru import autonomous_cycle as _cycle_mod
    from koru.autonomy.phases import scan_phase

    scan_phase.run_scan = _cycle_mod.run_scan

    return scan_phase.handle_scan_phase(
        project,
        state,
        cycle,
        enable_scan,
        include_semcod_artifacts,
        scan_skip_if_clean,
        scan_skip_after,
        topology_integration,
        _hp,
        _emit,
    )


def _build_queue_command(max_iterations: int, queue_name: str | None) -> str:
    """Build the queue loop command string."""
    base = f"koru --queue --loop --max-iterations {max_iterations}"
    return base if queue_name is None else f"{base} --queue-name {queue_name}"


def _run_queue_loop(
    project: Path,
    actor: str,
    queue_name: str | None,
    max_iterations: int,
) -> QueueLoopResult:
    """Execute the planfile queue loop."""
    from koru import autonomous_cycle as _cycle_mod

    return _cycle_mod.run_planfile_queue_loop(
        project=project,
        actor=actor,
        queue_name=queue_name,
        max_iterations=max_iterations,
        planfile_runner=_cycle_mod._run_process,
        shell_runner=_cycle_mod._run_shell_command,
        api_runner=_cycle_mod._run_api_request,
        llm_runner=_cycle_mod._run_llm_request,
        prompt_runner=_cycle_mod._default_human_prompt,
    )


def _emit_queue_iteration_event(
    queue_result: QueueLoopResult,
    cycle: int,
    queue_name: str | None,
    actor: str,
    qcmd: str,
    _emit: callable,
) -> None:
    """Emit queue iteration event."""
    qname = "__all__" if queue_name is None else queue_name
    _sum_fn = getattr(queue_result, "summary", None)
    _queue_summary = _sum_fn() if callable(_sum_fn) else str(_sum_fn or "")
    _emit(
        "QueueIteration",
        {
            "cycle": cycle,
            "queue_name": qname,
            "actor": actor,
            "iterations": int(getattr(queue_result, "iterations", 0)),
            "completed": list(getattr(queue_result, "completed", []) or []),
            "failed": list(getattr(queue_result, "failed", []) or []),
            "waiting": list(getattr(queue_result, "waiting", []) or []),
            "last_status": str(getattr(queue_result, "last_status", "")),
            "last_message": str(getattr(queue_result, "last_message", "")),
            "last_ticket_id": getattr(queue_result, "last_ticket_id", None),
            "summary": _queue_summary,
        },
        command=qcmd,
    )


def _handle_post_run_verify(
    project: Path,
    state: AutoloopState,
    cycle: int,
    queue_result: QueueLoopResult,
    verify_config: Any,
    _hp: callable,
    _emit: callable,
) -> None:
    """Handle post-run verification for completed tickets."""
    from koru import autonomous_cycle as _cycle_mod

    completed_ids = list(getattr(queue_result, "completed", []) or [])
    if completed_ids and verify_config is not None:
        verify_outcomes = _cycle_mod.verify_completed_tickets(
            project,
            completed_ids,
            config=verify_config,
            planfile_runner=_cycle_mod._run_process,
            shell_runner=_cycle_mod._run_shell_command,
        )
        failed = [o for o in verify_outcomes if not o.get("ok")]
        for outcome in verify_outcomes:
            if outcome.get("ok"):
                tid = str(outcome.get("ticket_id") or "").strip()
                if tid:
                    state.post_verify_seen.add(tid)
        if verify_outcomes:
            _hp(
                f"  post_run_verify (queue): tickets={len(completed_ids)} failed={len(failed)}",
            )
            _emit(
                "PostRunVerifyCompleted",
                {
                    "cycle": cycle,
                    "ticket_count": len(completed_ids),
                    "failed_count": len(failed),
                    "outcomes": verify_outcomes,
                },
                command="; ".join(verify_config.commands),
            )


def _handle_queue_loop_phase(
    project: Path,
    state: AutoloopState,
    cycle: int,
    actor: str,
    queue_name: str | None,
    max_iterations: int,
    topology_integration: bool,
    verify_config: Any,
    _hp: callable,
    _emit: callable,
) -> tuple[QueueLoopResult, Any]:
    from koru import autonomous_cycle as _cycle_mod

    _queue_phase.run_planfile_queue_loop = _cycle_mod.run_planfile_queue_loop
    _queue_phase._run_process = _cycle_mod._run_process
    _queue_phase._run_shell_command = _cycle_mod._run_shell_command
    _queue_phase._run_api_request = _cycle_mod._run_api_request
    _queue_phase._run_llm_request = _cycle_mod._run_llm_request
    _queue_phase._default_human_prompt = _cycle_mod._default_human_prompt
    _queue_phase.verify_completed_tickets = _cycle_mod.verify_completed_tickets
    return _queue_phase.handle_queue_loop_phase(
        project,
        state,
        cycle,
        actor,
        queue_name,
        max_iterations,
        topology_integration,
        verify_config,
        _hp,
        _emit,
    )


def _handle_scan_after_idle(
    project: Path,
    state: AutoloopState,
    cycle: int,
    queue_result: QueueLoopResult,
    scan_after_idle_queue: bool,
    include_semcod_artifacts: bool | None,
    scan_after_idle_min_interval_seconds: float,
    topology_integration: bool,
    cycle_telemetry: dict[str, Any],
    _hp: callable,
    _emit: callable,
) -> ScanResult | None:
    from koru import autonomous_cycle as _cycle_mod
    from koru.autonomy.phases import scan_phase

    scan_phase.run_scan = _cycle_mod.run_scan
    scan_phase._run_code2llm_discovery_after_idle = _cycle_mod._run_code2llm_discovery_after_idle

    return scan_phase.handle_scan_after_idle(
        project,
        state,
        cycle,
        queue_result,
        scan_after_idle_queue,
        include_semcod_artifacts,
        scan_after_idle_min_interval_seconds,
        topology_integration,
        cycle_telemetry,
        _hp,
        _emit,
    )


def _run_code2llm_discovery_after_idle(
    project: Path,
    _hp: callable,
    _emit: callable,
    *,
    scope_paths: tuple[str, ...] | None = None,
) -> dict[str, Any] | None:
    """Run broad code2llm ticket discovery after an idle scan found no new work."""
    try:
        from koru.autonomy.code2llm_discovery import (
            format_discovery_summary,
            run_code2llm_discovery,
        )
        from koru.scan import resolve_scan_paths
    except Exception as exc:  # noqa: BLE001 - optional integration
        _hp(f"- code2llm discovery unavailable: {exc}")
        return None

    paths = scope_paths if scope_paths is not None else resolve_scan_paths(project)
    outcome = run_code2llm_discovery(project, scope_paths=paths)
    summary = format_discovery_summary(outcome)
    _hp(f"  {summary}")
    payload = outcome.to_dict()
    payload = _ensure_standardized_discovery_follow_up(project, payload=payload, _hp=_hp)
    _emit("Code2llmDiscoveryCompleted", payload)
    return payload


def _ensure_standardized_discovery_follow_up(
    project: Path,
    *,
    payload: dict[str, Any],
    _hp: callable,
) -> dict[str, Any]:
    """Guarantee a standard idle workflow ticket when discovery found no runnable work."""
    applied_items = payload.get("applied")
    if isinstance(applied_items, list) and applied_items:
        return payload
    try:
        from koru.autonomy.ide_work import ensure_project_discovery_ticket
    except Exception as exc:  # noqa: BLE001 - optional integration
        _hp(f"  idle workflow: standardized follow-up unavailable: {exc}")
        return payload
    try:
        ticket = ensure_project_discovery_ticket(project, auto_run_code2llm=False)
    except Exception as exc:  # noqa: BLE001 - best-effort fallback
        _hp(f"  idle workflow: failed to ensure standardized follow-up ticket: {exc}")
        return payload
    if not isinstance(ticket, dict):
        return payload
    ticket_id = str(ticket.get("id") or "").strip()
    if not ticket_id:
        return payload
    payload["follow_up_workflow"] = "standardized_project_discovery"
    payload["follow_up_ticket_id"] = ticket_id
    _hp(
        "  idle workflow: standardized follow-up ticket "
        f"{ticket_id} ready for IDE LLM",
    )
    return payload


def _update_stagnation_state(
    state: AutoloopState,
    queue_result: QueueLoopResult,
) -> None:
    waiting_ticket = _queue_loop_waiting_ticket_label(queue_result)
    signature = f"{queue_result.last_status}:{waiting_ticket}"
    if state.previous_signature and state.previous_signature == signature:
        state.stagnation_streak += 1
    else:
        state.stagnation_streak = 0
    state.previous_signature = signature
