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


class _LoopState:
    """Accumulated outcome of a queue-drain loop."""

    def __init__(self) -> None:
        self.completed: list[str] = []
        self.failed: list[str] = []
        self.waiting: list[str] = []
        self.last_status = "idle"
        self.last_message = ""
        self.last_ticket_id: str | None = None
        self.autopilot_blocked = False
        self.iterations = 0

    def record(self, res: QueueRunResult) -> None:
        self.last_status = res.status
        self.last_message = res.message
        self.last_ticket_id = res.ticket_id
        self.autopilot_blocked = res.autopilot_blocked
        if res.status == "completed" and res.ticket_id:
            self.completed.append(res.ticket_id)
        elif res.status == "failed" and res.ticket_id:
            self.failed.append(res.ticket_id)
        elif res.status == "waiting_input" and res.ticket_id:
            self.waiting.append(res.ticket_id)

    def result(self) -> QueueLoopResult:
        return QueueLoopResult(
            iterations=self.iterations,
            completed=self.completed,
            failed=self.failed,
            waiting=self.waiting,
            last_status=self.last_status,
            last_message=self.last_message,
            last_ticket_id=self.last_ticket_id,
            autopilot_blocked=self.autopilot_blocked,
        )


def _run_sequential_loop(
    state: _LoopState,
    *,
    run_kwargs: dict,
    max_iterations: int,
    progress_callback: Callable[[QueueRunResult, int], None] | None,
    stop_callback: Callable[[QueueRunResult, int], bool] | None,
) -> QueueLoopResult:
    for i in range(max_iterations):
        state.iterations = i + 1
        result = run_next_planfile_task(**run_kwargs)
        if progress_callback is not None:
            progress_callback(result, state.iterations)

        state.record(result)

        if stop_callback is not None and stop_callback(result, state.iterations):
            break
        if result.status in _LOOP_TERMINAL_STATUSES:
            break
        if result.status not in _LOOP_CONTINUE_STATUSES:
            # Unknown / future status — terminate to be safe.
            break
    return state.result()


def _run_parallel_loop(
    state: _LoopState,
    *,
    run_kwargs: dict,
    concurrency: int,
    max_iterations: int,
    interactive: bool,
    progress_callback: Callable[[QueueRunResult, int], None] | None,
    stop_callback: Callable[[QueueRunResult, int], bool] | None,
) -> QueueLoopResult:
    import concurrent.futures
    import threading

    from koru.queue.runner import _next_tickets_or_result
    from koru.queue.ticket import ticket_file_scope

    progress_lock = threading.Lock()
    worker_counter = 0

    def _execute_worker(ticket_dict: dict[str, any], worker_num: int) -> QueueRunResult:
        t_id = str(ticket_dict.get("id") or "")
        kwargs = {
            **run_kwargs,
            "actor": f"{run_kwargs['actor']}-w{worker_num}",
            "target_ticket_id": t_id,
        }
        return run_next_planfile_task(**kwargs)

    active_futures: dict[concurrent.futures.Future[QueueRunResult], tuple[str, set[str]]] = {}
    worker_counter = 0

    def _dispatch_batch(pool, slots_available: int) -> bool:
        """Submit new disjoint tickets; returns True when the loop must stop."""
        nonlocal worker_counter
        current_locked_files: set[str] = set()
        current_running_ids: set[str] = set()
        for t_id, f_set in active_futures.values():
            current_running_ids.add(t_id)
            current_locked_files.update(f_set)

        new_tickets, batch_err = _next_tickets_or_result(
            run_kwargs["project"],
            run_kwargs["planfile_runner"],
            count=slots_available,
            queue_name=run_kwargs["queue_name"],
            disjoint_files=True,
            interactive=interactive,
            locked_files=current_locked_files,
            exclude_ids=current_running_ids,
        )
        if batch_err is not None:
            if not active_futures:
                state.last_status = batch_err.status
                state.last_message = batch_err.message
                return True
        elif new_tickets:
            for t in new_tickets:
                t_id = str(t.get("id") or "")
                t_files = ticket_file_scope(t)
                worker_counter += 1
                fut = pool.submit(_execute_worker, t, worker_counter)
                active_futures[fut] = (t_id, t_files)
        return False

    def _resolve_future(fut) -> QueueRunResult:
        t_id, _ = active_futures.pop(fut)
        state.iterations += 1
        try:
            return fut.result()
        except Exception as exc:
            return QueueRunResult(
                status="failed", message=str(exc), exit_code=1, ticket_id=t_id
            )

    def _record_result(res: QueueRunResult) -> bool:
        with progress_lock:
            if progress_callback is not None:
                progress_callback(res, state.iterations)
            state.record(res)
            if stop_callback is not None and stop_callback(res, state.iterations):
                return True
            return res.status in _LOOP_TERMINAL_STATUSES

    with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as pool:
        while state.iterations < max_iterations:
            slots_available = min(
                concurrency - len(active_futures),
                max_iterations - (state.iterations + len(active_futures)),
            )
            if slots_available > 0 and _dispatch_batch(pool, slots_available):
                break

            if not active_futures:
                state.last_status = "idle"
                state.last_message = "No runnable ticket found"
                break

            done, _ = concurrent.futures.wait(
                active_futures.keys(),
                return_when=concurrent.futures.FIRST_COMPLETED,
            )

            should_stop = False
            for fut in done:
                res = _resolve_future(fut)
                if _record_result(res):
                    should_stop = True
                if state.iterations >= max_iterations:
                    should_stop = True

            if should_stop:
                for fut in active_futures:
                    fut.cancel()
                break

    return state.result()


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

    run_kwargs: dict[str, any] = {
        "project": project,
        "actor": actor,
        "queue_name": queue_name,
        "interactive": interactive,
        "dry_run": dry_run,
        "planfile_runner": planfile_runner,
        "shell_runner": shell_runner,
        "api_runner": api_runner,
        "llm_runner": llm_runner,
        "prompt_runner": prompt_runner,
    }
    state = _LoopState()

    if concurrency > 1:
        return _run_parallel_loop(
            state,
            run_kwargs=run_kwargs,
            concurrency=concurrency,
            max_iterations=max_iterations,
            interactive=interactive,
            progress_callback=progress_callback,
            stop_callback=stop_callback,
        )
    return _run_sequential_loop(
        state,
        run_kwargs=run_kwargs,
        max_iterations=max_iterations,
        progress_callback=progress_callback,
        stop_callback=stop_callback,
    )
