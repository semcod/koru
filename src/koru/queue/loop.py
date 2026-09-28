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
    dry_run: bool = False,
    concurrency: int = 1,
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

    When ``concurrency > 1``, uses dynamic pipelining with a thread pool to execute
    disjoint tickets in parallel without idle worker barriers.
    The loop terminates when the queue is idle, a ticket needs human
    input we cannot satisfy, an executor kind is unsupported, planfile
    itself errors out, or ``max_iterations`` is reached. Successful
    (``completed``) and ``failed`` tickets do not stop the loop — the
    next ticket is fetched.
    """
    if max_iterations < 1:
        raise ValueError("max_iterations must be >= 1")

    completed: list[str] = []
    failed: list[str] = []
    waiting: list[str] = []
    last_status = "idle"
    last_message = ""
    last_ticket_id: str | None = None
    autopilot_blocked = False
    iterations = 0

    if concurrency > 1:
        import concurrent.futures
        import threading

        from koru.queue.runner import _next_tickets_or_result
        from koru.queue.ticket import ticket_file_scope

        progress_lock = threading.Lock()

        def _execute_worker(ticket_dict: dict[str, any], worker_num: int) -> QueueRunResult:
            t_id = str(ticket_dict.get("id") or "")
            worker_actor = f"{actor}-w{worker_num}"
            return run_next_planfile_task(
                project=project,
                actor=worker_actor,
                queue_name=queue_name,
                target_ticket_id=t_id,
                interactive=interactive,
                dry_run=dry_run,
                planfile_runner=planfile_runner,
                shell_runner=shell_runner,
                api_runner=api_runner,
                llm_runner=llm_runner,
                prompt_runner=prompt_runner,
            )

        active_futures: dict[concurrent.futures.Future[QueueRunResult], tuple[str, set[str]]] = {}
        worker_counter = 0

        with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as pool:
            while iterations < max_iterations:
                slots_available = min(
                    concurrency - len(active_futures),
                    max_iterations - (iterations + len(active_futures)),
                )
                if slots_available > 0:
                    current_locked_files: set[str] = set()
                    current_running_ids: set[str] = set()
                    for t_id, f_set in active_futures.values():
                        current_running_ids.add(t_id)
                        current_locked_files.update(f_set)

                    new_tickets, batch_err = _next_tickets_or_result(
                        project,
                        planfile_runner,
                        count=slots_available,
                        queue_name=queue_name,
                        disjoint_files=True,
                        interactive=interactive,
                        locked_files=current_locked_files,
                        exclude_ids=current_running_ids,
                    )
                    if batch_err is not None:
                        if not active_futures:
                            last_status = batch_err.status
                            last_message = batch_err.message
                            break
                    elif new_tickets:
                        for t in new_tickets:
                            t_id = str(t.get("id") or "")
                            t_files = ticket_file_scope(t)
                            worker_counter += 1
                            fut = pool.submit(_execute_worker, t, worker_counter)
                            active_futures[fut] = (t_id, t_files)

                if not active_futures:
                    last_status = "idle"
                    last_message = "No runnable ticket found"
                    break

                done, _ = concurrent.futures.wait(
                    active_futures.keys(),
                    return_when=concurrent.futures.FIRST_COMPLETED,
                )

                should_stop = False
                for fut in done:
                    t_id, _ = active_futures.pop(fut)
                    iterations += 1
                    try:
                        res = fut.result()
                    except Exception as exc:
                        res = QueueRunResult(
                            status="failed", message=str(exc), exit_code=1, ticket_id=t_id
                        )

                    with progress_lock:
                        if progress_callback is not None:
                            progress_callback(res, iterations)

                        last_status = res.status
                        last_message = res.message
                        last_ticket_id = res.ticket_id
                        autopilot_blocked = res.autopilot_blocked

                        if res.status == "completed" and res.ticket_id:
                            completed.append(res.ticket_id)
                        elif res.status == "failed" and res.ticket_id:
                            failed.append(res.ticket_id)
                        elif res.status == "waiting_input" and res.ticket_id:
                            waiting.append(res.ticket_id)

                        if stop_callback is not None and stop_callback(res, iterations):
                            should_stop = True
                        if res.status in _LOOP_TERMINAL_STATUSES:
                            should_stop = True

                    if iterations >= max_iterations:
                        should_stop = True

                if should_stop:
                    for fut in active_futures:
                        fut.cancel()
                    break

        return QueueLoopResult(
            iterations=iterations,
            completed=completed,
            failed=failed,
            waiting=waiting,
            last_status=last_status,
            last_message=last_message,
            last_ticket_id=last_ticket_id,
            autopilot_blocked=autopilot_blocked,
        )

    for i in range(max_iterations):
        iterations = i + 1
        result = run_next_planfile_task(
            project=project,
            actor=actor,
            dry_run=dry_run,
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
        autopilot_blocked = result.autopilot_blocked

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
        autopilot_blocked=autopilot_blocked,
    )
