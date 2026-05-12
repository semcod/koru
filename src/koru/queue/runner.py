"""Main queue runner logic for executing planfile tickets."""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path

from .human import default_human_prompt
from .locking import queue_runner_lock, ticket_claim_or_error
from .runners import (
    _DEFAULT_LLM_MODEL,
    run_api_request,
    run_llm_request,
    run_process,
    run_shell_command,
)
from .ticket import (
    parse_next_ticket,
    planfile_command,
    ticket_api_request,
    ticket_command,
    ticket_llm_request,
)
from .types import ApiRunResult, CommandResult, LlmRunResult, QueueRunResult


def run_next_planfile_task(
    *,
    project: Path,
    actor: str = "koru-shell",
    dry_run: bool = False,
    queue_name: str | None = None,
    interactive: bool = False,
    planfile_runner: Callable[[list[str], Path], CommandResult] = run_process,
    shell_runner: Callable[[str, Path], CommandResult] = run_shell_command,
    api_runner: Callable[[dict[str, any], Path], CommandResult] = run_api_request,
    llm_runner: Callable[[dict[str, any], Path], CommandResult] = run_llm_request,
    prompt_runner: Callable[[str, str], str | None] = default_human_prompt,
) -> QueueRunResult:
    """Execute one runnable planfile ticket, if any.

    When ``interactive`` is true and the next ticket is a ``human``
    executor, ``prompt_runner(prompt, ticket_id)`` is invoked to collect
    an answer. A non-empty answer triggers ``planfile ticket done``
    (the answer is appended to the run log under
    ``.planfile/.koru/runs/``); cancellation (``None``) leaves the
    ticket untouched and returns ``status=waiting_input`` as before.

    Concurrent drains (several IDE windows) are serialized per project
    via ``.planfile/.koru/queue-runner.lock`` (POSIX); disable with
    ``KORU_QUEUE_RUNNER_LOCK=0``. Before ``ticket start``, koru calls
    ``ticket claim --assigned-to <actor>`` for tracing / lease metadata.
    """
    project = project.resolve()

    with queue_runner_lock(project):
        # planfile has no `ticket next` and no `--queue` filter on `list`.
        # `--status open` selects runnable tickets; koru filters by
        # ``queue_name`` in-process below (best-effort: planfile tickets
        # may carry an ``execution.queue`` field).
        next_args = ["ticket", "list", "--status", "open", "--format", "json"]
        next_result = planfile_command(
            project,
            next_args,
            runner=planfile_runner,
        )
        if next_result.returncode != 0:
            return QueueRunResult(
                status="planfile_error",
                message="planfile ticket list failed",
                exit_code=next_result.returncode,
                stdout=next_result.stdout,
                stderr=next_result.stderr,
            )

        ticket = parse_next_ticket(next_result.stdout)
        if ticket is None:
            return QueueRunResult(status="idle", message="No runnable ticket found")

        ticket_id = str(ticket["id"])
        executor = ticket.get("executor") or {}
        executor_kind = str(executor.get("kind") or "human")

        if executor_kind == "human":
            inputs = ticket.get("inputs") or {}
            prompt = str(
                inputs.get("prompt")
                or ticket.get("description")
                or ticket.get("name")
                or ticket_id
            )
            if not interactive or dry_run:
                return QueueRunResult(
                    status="waiting_input",
                    ticket_id=ticket_id,
                    executor_kind=executor_kind,
                    message=prompt,
                )
            answer = prompt_runner(prompt, ticket_id)
            if not answer:
                return QueueRunResult(
                    status="waiting_input",
                    ticket_id=ticket_id,
                    executor_kind=executor_kind,
                    message=prompt,
                )
            claimed = ticket_claim_or_error(
                project, ticket_id, actor, planfile_runner=planfile_runner
            )
            if claimed:
                return claimed
            planfile_command(
                project,
                ["ticket", "start", ticket_id],
                runner=planfile_runner,
            )
            planfile_command(
                project,
                ["ticket", "done", ticket_id],
                runner=planfile_runner,
            )
            return QueueRunResult(
                status="completed",
                ticket_id=ticket_id,
                executor_kind=executor_kind,
                message=answer,
            )

        if executor_kind not in {"api", "shell", "llm"}:
            return QueueRunResult(
                status="unsupported_executor",
                ticket_id=ticket_id,
                executor_kind=executor_kind,
                message=f"Executor kind '{executor_kind}' is not implemented yet",
            )

        if executor_kind == "api":
            action = ticket_api_request(ticket)
            missing_prompt = "API ticket is missing inputs.api_endpoint or executor.handler"
        elif executor_kind == "llm":
            action = ticket_llm_request(ticket)
            missing_prompt = "LLM ticket is missing inputs.prompt (or description / name)"
        else:
            action = ticket_command(ticket)
            missing_prompt = "Shell ticket is missing inputs.script or executor.handler"

        if not action:
            # `block --reason` is the planfile equivalent of the older
            # `input --prompt` surface koru used to call.
            planfile_command(
                project,
                ["ticket", "block", ticket_id, "--reason", missing_prompt],
                runner=planfile_runner,
            )
            return QueueRunResult(
                status="waiting_input",
                ticket_id=ticket_id,
                executor_kind=executor_kind,
                message=missing_prompt,
            )

        if dry_run:
            message = json.dumps(action) if isinstance(action, dict) else action
            return QueueRunResult(
                status="dry_run",
                ticket_id=ticket_id,
                executor_kind=executor_kind,
                message=message,
            )

        claimed = ticket_claim_or_error(
            project, ticket_id, actor, planfile_runner=planfile_runner
        )
        if claimed:
            return claimed
        planfile_command(
            project,
            ["ticket", "start", ticket_id],
            runner=planfile_runner,
        )

        if executor_kind == "api":
            result = api_runner(action, project)
            action_label = f"{action['method']} {action['endpoint']}"
        elif executor_kind == "llm":
            result = llm_runner(action, project)
            action_label = f"llm {action.get('model') or _DEFAULT_LLM_MODEL}"
        else:
            result = shell_runner(str(action), project)
            action_label = str(action)

        if result.returncode == 0:
            # planfile's `done` has no `--note`/`--result-json`. The full
            # stdout/stderr is preserved in QueueRunResult and persisted to
            # `.planfile/.koru/runs/` by the run-log writer.
            planfile_command(
                project,
                ["ticket", "done", ticket_id],
                runner=planfile_runner,
            )
            status = "completed"
        else:
            # Use `block --reason` for failures (planfile has no `fail`
            # verb). The full stderr stays in QueueRunResult / run log.
            reason = (
                result.stderr[-500:].strip()
                or f"Command exited with {result.returncode}"
            )
            planfile_command(
                project,
                ["ticket", "block", ticket_id, "--reason", f"FAIL: {reason}"],
                runner=planfile_runner,
            )
            status = "failed"

        return QueueRunResult(
            status=status,
            ticket_id=ticket_id,
            executor_kind=executor_kind,
            message=action_label,
            exit_code=result.returncode,
            stdout=result.stdout,
            stderr=result.stderr,
        )
