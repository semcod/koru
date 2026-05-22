"""Queue loop phase logic for autonomous cycle."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from koru.autonomy.phases.utils import is_topology_enabled
from koru.autonomy.post_run_verify import verify_completed_tickets
from koru.autonomy.state import AutoloopState
from koru.queue import QueueLoopResult, run_planfile_queue_loop
from koru.queue import default_human_prompt as _default_human_prompt
from koru.queue import run_api_request as _run_api_request
from koru.queue import run_llm_request as _run_llm_request
from koru.queue import run_process as _run_process
from koru.queue import run_shell_command as _run_shell_command
from koru.autonomy.ide_work import release_stale_in_progress_tickets, resolve_in_progress_stale_minutes


def handle_queue_hygiene(
    project: Path,
    cycle: int,
    _hp: Callable[..., Any],
    _emit: Callable[..., Any],
) -> None:
    stale_minutes = resolve_in_progress_stale_minutes(project)
    if stale_minutes is not None:
        released_stale = release_stale_in_progress_tickets(
            project,
            stale_minutes=stale_minutes,
            runner=_run_process,
        )
        if released_stale:
            _hp(
                f"  queue hygiene: reopened {released_stale} stale in_progress "
                f"(>{stale_minutes:.0f}m)",
            )
            _emit(
                "QueueStaleReleased",
                {"cycle": cycle, "count": released_stale, "stale_minutes": stale_minutes},
            )


def build_queue_command(max_iterations: int, queue_name: str | None) -> str:
    """Build the queue loop command string."""
    base = f"koru --queue --loop --max-iterations {max_iterations}"
    return base if queue_name is None else f"{base} --queue-name {queue_name}"


def run_queue_loop(
    project: Path,
    actor: str,
    queue_name: str | None,
    max_iterations: int,
) -> QueueLoopResult:
    """Execute the planfile queue loop."""
    return run_planfile_queue_loop(
        project=project,
        actor=actor,
        queue_name=queue_name,
        max_iterations=max_iterations,
        planfile_runner=_run_process,
        shell_runner=_run_shell_command,
        api_runner=_run_api_request,
        llm_runner=_run_llm_request,
        prompt_runner=_default_human_prompt,
    )


def emit_queue_iteration_event(
    queue_result: QueueLoopResult,
    cycle: int,
    queue_name: str | None,
    actor: str,
    qcmd: str,
    _emit: Callable[..., Any],
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


def handle_post_run_verify(
    project: Path,
    state: AutoloopState,
    cycle: int,
    queue_result: QueueLoopResult,
    verify_config: Any,
    _hp: Callable[..., Any],
    _emit: Callable[..., Any],
) -> None:
    """Handle post-run verification for completed tickets."""
    completed_ids = list(getattr(queue_result, "completed", []) or [])
    if completed_ids and verify_config is not None:
        verify_outcomes = verify_completed_tickets(
            project,
            completed_ids,
            config=verify_config,
            planfile_runner=_run_process,
            shell_runner=_run_shell_command,
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


def handle_queue_loop_phase(
    project: Path,
    state: AutoloopState,
    cycle: int,
    actor: str,
    queue_name: str | None,
    max_iterations: int,
    topology_integration: bool,
    verify_config: Any,
    _hp: Callable[..., Any],
    _emit: Callable[..., Any],
) -> tuple[QueueLoopResult, Any]:
    if not is_topology_enabled(
        project,
        "autoloop:queue",
        fallback=True,
        enabled=topology_integration,
    ):
        _hp("- autoloop queue phase skipped (autoloop:queue disabled in topology)")
        queue_result = QueueLoopResult(0, [], [], [], "disabled", "")
    else:
        qcmd = build_queue_command(max_iterations, queue_name)
        _hp(f"+ {qcmd}")
        queue_result = run_queue_loop(project, actor, queue_name, max_iterations)
        _hp(f"  queue: {queue_result.summary()}")
        emit_queue_iteration_event(queue_result, cycle, queue_name, actor, qcmd, _emit)
        handle_post_run_verify(project, state, cycle, queue_result, verify_config, _hp, _emit)
    return queue_result, verify_config
