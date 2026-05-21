"""CLI helpers for ``koru queue``."""


from argparse import Namespace
from collections.abc import Callable
from typing import Any

from koru.events import emit_management_event
from koru.queue import (
    QueueLoopResult,
    QueueRunResult,
    run_next_planfile_task,
    run_planfile_queue_loop,
)
from koru.queue.local_manager import (
    queue_local_manager_session,
    queue_manager_complete,
    queue_manager_decision_action,
    queue_manager_health,
    queue_manager_start,
    queue_manager_stop_callback,
)
from koru.run_log import open_run_log_eagerly

QUEUE_STATUS_MARKERS: dict[str, str] = {
    "completed": "✓",
    "failed": "✗",
    "waiting_input": "⏸",
    "idle": "•",
    "dry_run": "?",
    "unsupported_executor": "!",
    "planfile_error": "!",
}

SUCCESS_QUEUE_STATUSES = frozenset({"completed", "idle", "waiting_input", "dry_run"})


def queue_status_marker(status: str) -> str:
    return QUEUE_STATUS_MARKERS.get(status, "·")


def queue_loop_exit_code(last_status: str) -> int:
    return 0 if last_status in SUCCESS_QUEUE_STATUSES else 1


def single_task_ticket_lists(result: Any) -> tuple[list[str], list[str], list[str]]:
    completed = [result.ticket_id] if result.status == "completed" and result.ticket_id else []
    failed = [result.ticket_id] if result.status == "failed" and result.ticket_id else []
    waiting = [result.ticket_id] if result.status == "waiting_input" and result.ticket_id else []
    return completed, failed, waiting


def emit_queue_run_started(args: Namespace) -> None:
    emit_management_event(
        tool="koru.queue",
        action="started",
        status="running",
        message="loop" if args.loop else "single",
        queue=args.queue_name,
        details={
            "project": str(args.project),
            "actor": args.actor,
            "dry_run": args.dry_run,
            "interactive": args.interactive,
        },
    )


def open_queue_run_log(args: Namespace) -> Any | None:
    if args.no_log or args.dry_run:
        return None
    run_log = open_run_log_eagerly(args.project, prefix="queue")
    run_log.write_header(
        project=args.project,
        mode="loop" if args.loop else "single",
        actor=args.actor,
        queue_name=args.queue_name,
        interactive=args.interactive,
    )
    return run_log


def _queue_progress_callback(
    args: Namespace,
    run_log: Any | None,
) -> Callable[[QueueRunResult, int], None]:
    def _progress(result: QueueRunResult, iteration: int) -> None:
        ticket = result.ticket_id or "-"
        kind = result.executor_kind or "-"
        marker = queue_status_marker(result.status)
        print(f"  [{iteration:>3}] {marker} {result.status:<22} {ticket:<14} ({kind})")
        if run_log is not None:
            run_log.write_iteration(iteration=iteration, result=result)
        emit_management_event(
            tool="koru.queue",
            action="iteration",
            status=result.status,
            level="error" if result.status in {"failed", "planfile_error"} else "info",
            message=result.message,
            queue=args.queue_name,
            details={
                "iteration": iteration,
                "ticket_id": result.ticket_id,
                "executor_kind": result.executor_kind,
                "exit_code": result.exit_code,
            },
        )

    return _progress


def _emit_queue_completed(
    args: Namespace, *, exit_code: int, status: str, message: str, details: dict
) -> None:
    emit_management_event(
        tool="koru.queue",
        action="completed" if exit_code == 0 else "failed",
        status=status,
        level="error" if exit_code else "info",
        message=message,
        queue=args.queue_name,
        details=details,
    )


def run_queue_loop_mode(
    args: Namespace,
    run_log: Any | None,
    *,
    planfile_runner: Callable[..., Any],
    shell_runner: Callable[..., Any],
    api_runner: Callable[..., Any],
    llm_runner: Callable[..., Any],
    prompt_runner: Callable[..., Any],
) -> int:
    manager = queue_local_manager_session(args)
    early_exit = queue_manager_start(args, manager)
    if early_exit is not None:
        print(f"koru queue: {early_exit.message}")
        _emit_queue_completed(
            args,
            exit_code=early_exit.exit_code,
            status=early_exit.status,
            message=early_exit.message,
            details=early_exit.details,
        )
        return early_exit.exit_code
    loop_result = run_planfile_queue_loop(
        project=args.project,
        actor=args.actor,
        queue_name=args.queue_name,
        interactive=args.interactive,
        max_iterations=args.max_iterations,
        progress_callback=_queue_progress_callback(args, run_log),
        stop_callback=queue_manager_stop_callback(manager),
        planfile_runner=planfile_runner,
        shell_runner=shell_runner,
        api_runner=api_runner,
        llm_runner=llm_runner,
        prompt_runner=prompt_runner,
    )
    if run_log is not None:
        run_log.write_footer(summary=loop_result)
    print()
    print(f"koru queue loop: {loop_result.summary()}")
    if loop_result.completed:
        print(f"  completed: {', '.join(loop_result.completed)}")
    if loop_result.failed:
        print(f"  failed:    {', '.join(loop_result.failed)}")
    if loop_result.waiting:
        print(f"  waiting:   {', '.join(loop_result.waiting)}")
    exit_code = queue_loop_exit_code(loop_result.last_status)
    _emit_queue_completed(
        args,
        exit_code=exit_code,
        status=loop_result.last_status,
        message=loop_result.summary(),
        details={
            "completed": loop_result.completed,
            "failed": loop_result.failed,
            "waiting": loop_result.waiting,
            "iterations": loop_result.iterations,
        },
    )
    queue_manager_complete(
        manager,
        exit_code=exit_code,
        result={
            "completed": loop_result.completed,
            "failed": loop_result.failed,
            "waiting": loop_result.waiting,
            "iterations": loop_result.iterations,
            "last_status": loop_result.last_status,
        },
    )
    return exit_code


def _single_task_summary(result: QueueRunResult) -> QueueLoopResult:
    completed, failed, waiting = single_task_ticket_lists(result)
    return QueueLoopResult(
        1,
        completed,
        failed,
        waiting,
        result.status,
        last_message=result.message or "",
        last_ticket_id=result.ticket_id,
    )


def run_queue_single_mode(
    args: Namespace,
    run_log: Any | None,
    *,
    planfile_runner: Callable[..., Any],
    shell_runner: Callable[..., Any],
    api_runner: Callable[..., Any],
    llm_runner: Callable[..., Any],
    prompt_runner: Callable[..., Any],
) -> int:
    manager = queue_local_manager_session(args)
    early_exit = queue_manager_start(args, manager)
    if early_exit is not None:
        print(f"koru queue: {early_exit.message}")
        _emit_queue_completed(
            args,
            exit_code=early_exit.exit_code,
            status=early_exit.status,
            message=early_exit.message,
            details=early_exit.details,
        )
        return early_exit.exit_code
    result = run_next_planfile_task(
        project=args.project,
        actor=args.actor,
        dry_run=args.dry_run,
        queue_name=args.queue_name,
        interactive=args.interactive,
        planfile_runner=planfile_runner,
        shell_runner=shell_runner,
        api_runner=api_runner,
        llm_runner=llm_runner,
        prompt_runner=prompt_runner,
    )
    if run_log is not None:
        run_log.write_iteration(iteration=1, result=result)
        run_log.write_footer(summary=_single_task_summary(result))
    print(
        f"koru queue: status={result.status} "
        f"ticket={result.ticket_id or '-'} executor={result.executor_kind or '-'}",
    )
    if result.message:
        print(result.message)
    if manager is not None:
        manager.heartbeat(
            health=queue_manager_health(result),
            metadata={
                "status": result.status,
                "ticket_id": result.ticket_id,
                "executor_kind": result.executor_kind,
            },
        )
        if manager.should_stop():
            action = queue_manager_decision_action(manager.last_reply)
            print(f"koru queue: local manager decision={action}; exiting after current task")
    exit_code = queue_loop_exit_code(result.status)
    _emit_queue_completed(
        args,
        exit_code=exit_code,
        status=result.status,
        message=result.message or "",
        details={
            "ticket_id": result.ticket_id,
            "executor_kind": result.executor_kind,
            "exit_code": result.exit_code,
            "dry_run": args.dry_run,
        },
    )
    queue_manager_complete(
        manager,
        exit_code=exit_code,
        result={
            "ticket_id": result.ticket_id,
            "executor_kind": result.executor_kind,
            "status": result.status,
            "exit_code": result.exit_code,
        },
    )
    return exit_code
