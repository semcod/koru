"""Loop driver for draining the planfile queue."""


from collections.abc import Callable
from pathlib import Path

from koru.queue.runner import run_next_planfile_task
from koru.queue.types import CommandResult, QueueLoopResult, QueueRunResult

# Statuses that should NOT terminate the loop (a transient outcome for the
# current ticket, but we can still try the next one).
_LOOP_CONTINUE_STATUSES: frozenset[str] = frozenset({"completed", "failed"})

# Statuses that DO terminate the loop. ``waiting_input`` requires human
# action; ``unsupported_executor`` and ``planfile_error`` indicate
# misconfiguration; ``idle`` means the queue is drained; ``dry_run`` is a
# preview that we do not advance past.
_LOOP_TERMINAL_STATUSES: frozenset[str] = frozenset(
    {
        "idle",
        "waiting_input",
        "unsupported_executor",
        "planfile_error",
        "dry_run",
        "claim_failed",
    },
)


def run_planfile_queue_loop(
    *,
    project: Path,
    actor: str = "koru-shell",
    queue_name: str | None = None,
    interactive: bool = False,
    max_iterations: int = 100,
    progress_callback: Callable[[QueueRunResult, int], None] | None = None,
    stop_callback: Callable[[QueueRunResult, int], bool] | None = None,
    planfile_runner: Callable[[list[str], Path], CommandResult],
    shell_runner: Callable[[str, Path], CommandResult],
    api_runner: Callable[[dict[str, any], Path], CommandResult],
    llm_runner: Callable[[dict[str, any], Path], CommandResult],
    prompt_runner: Callable[[str, str], str | None],
) -> QueueLoopResult:
    """Drain the planfile queue by repeatedly calling run_next_planfile_task.

    The loop terminates when the queue is idle, a ticket needs human
    input we cannot satisfy, an executor kind is unsupported, planfile
    itself errors out, or ``max_iterations`` is reached. Successful
    (``completed``) and ``failed`` tickets do not stop the loop — the
    next ticket is fetched.

    ``progress_callback`` (when provided) is invoked after each iteration
    with ``(result, iteration_number_starting_at_1)`` for live progress
    reporting.

    ``stop_callback`` (when provided) is invoked after progress reporting.
    If it returns true, the loop stops after the current iteration; this is
    used by the local manager to implement drain-and-exit lifecycle decisions.
    """
    if max_iterations < 1:
        raise ValueError("max_iterations must be >= 1")

    completed: list[str] = []
    failed: list[str] = []
    waiting: list[str] = []
    last_status = "idle"
    last_message = ""
    last_ticket_id: str | None = None
    iterations = 0

    for i in range(max_iterations):
        iterations = i + 1
        result = run_next_planfile_task(
            project=project,
            actor=actor,
            queue_name=queue_name,
            interactive=interactive,
            planfile_runner=planfile_runner,
            shell_runner=shell_runner,
            api_runner=api_runner,
            llm_runner=llm_runner,
            prompt_runner=prompt_runner,
        )
        if progress_callback is not None:
            progress_callback(result, iterations)

        last_status = result.status
        last_message = result.message
        last_ticket_id = result.ticket_id

        if result.status == "completed" and result.ticket_id:
            completed.append(result.ticket_id)
        elif result.status == "failed" and result.ticket_id:
            failed.append(result.ticket_id)
        elif result.status == "waiting_input" and result.ticket_id:
            waiting.append(result.ticket_id)

        if stop_callback is not None and stop_callback(result, iterations):
            break
        if result.status in _LOOP_TERMINAL_STATUSES:
            break
        if result.status not in _LOOP_CONTINUE_STATUSES:
            # Unknown / future status — terminate to be safe.
            break

    return QueueLoopResult(
        iterations=iterations,
        completed=completed,
        failed=failed,
        waiting=waiting,
        last_status=last_status,
        last_message=last_message,
        last_ticket_id=last_ticket_id,
    )
