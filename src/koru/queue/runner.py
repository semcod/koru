"""Main queue runner logic for executing planfile tickets."""

from __future__ import annotations

import json
import logging
import uuid
from collections.abc import Callable
from pathlib import Path

from .human import default_human_prompt
from .locking import queue_runner_lock, ticket_claim_or_error
from .planfile_ticket_note import append_shell_evidence_note
from .runners import (
    _DEFAULT_LLM_MODEL,
    run_api_request,
    run_llm_request,
    run_process,
    run_shell_command,
)
from .shell_evidence import format_shell_run_note
from .ticket import (
    parse_next_ticket,
    planfile_command,
    ticket_api_request,
    ticket_command,
    ticket_llm_request,
)
from .types import CommandResult, QueueRunResult

_logger = logging.getLogger(__name__)


def _source_tool(ticket: dict) -> str:
    source = ticket.get("source")
    if isinstance(source, dict):
        return str(source.get("tool") or "")
    return str(source or "")


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
        ticket_name = str(ticket.get("name") or ticket_id)
        try:
            from koru.activity_log import activity

            activity(
                "QUEUE",
                f"start {ticket_id} ({ticket_name}) executor="
                f"{(ticket.get('executor') or {}).get('kind', 'human')}",
            )
        except Exception:
            pass
        executor = ticket.get("executor") or {}
        raw_kind = executor.get("kind")
        executor_kind = str(raw_kind or "human")
        # In non-interactive mode, legacy tickets created before --executor-kind
        # existed should not block the queue. Default them to shell so they can
        # be auto-completed with a no-op script. Explicit human tickets are
        # preserved and still return waiting_input as before.
        if raw_kind is None and _source_tool(ticket) == "koru-scan":
            executor_kind = "human"
        elif raw_kind is None and not interactive and not dry_run:
            executor_kind = "shell"

        if executor_kind == "human":
            inputs = ticket.get("inputs") or {}
            prompt = str(
                inputs.get("prompt") or ticket.get("description") or ticket.get("name") or ticket_id
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
            # Fallback no-op for legacy tickets auto-converted to shell above,
            # or any shell ticket missing a script. Prevents queue blocking.
            if executor_kind == "shell" and not interactive and not dry_run:
                action = "true"
            else:
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

        claimed = ticket_claim_or_error(project, ticket_id, actor, planfile_runner=planfile_runner)
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
            try:
                from koru.activity_log import activity

                activity("QUEUE", f"shell {ticket_id}: {action}")
            except Exception:
                pass
            result = shell_runner(str(action), project)
            action_label = str(action)

        if result.returncode == 0:
            # Shell stdout/stderr: append via `ticket update --note` / `-n`
            # when the installed planfile supports it; else a run artifact under
            # `.planfile/.koru/runs/`. Full streams remain in QueueRunResult.
            if executor_kind == "shell":
                run_id = uuid.uuid4().hex[:16]
                note = format_shell_run_note(
                    run_id=run_id,
                    exit_code=result.returncode,
                    stdout=result.stdout,
                    stderr=result.stderr,
                )
                up, evidence_kind = append_shell_evidence_note(
                    project,
                    ticket_id,
                    note,
                    run_id=run_id,
                    planfile_runner=planfile_runner,
                )
                if up.returncode == 0:
                    if evidence_kind == "artifact":
                        _logger.info(
                            "koru.queue.shell_evidence_appended_artifact ticket_id=%s "
                            "run_id=%s path=%s",
                            ticket_id,
                            run_id,
                            (up.stdout or "").strip(),
                        )
                    else:
                        _logger.info(
                            "koru.queue.shell_evidence_appended ticket_id=%s run_id=%s",
                            ticket_id,
                            run_id,
                        )
                else:
                    _logger.warning(
                        "koru.queue.shell_evidence_note_failed ticket_id=%s run_id=%s "
                        "planfile_exit=%s planfile_stderr=%s",
                        ticket_id,
                        run_id,
                        up.returncode,
                        (up.stderr or "")[:500],
                    )
            planfile_command(
                project,
                ["ticket", "done", ticket_id],
                runner=planfile_runner,
            )
            status = "completed"
        else:
            # Use `block --reason` for failures (planfile has no `fail`
            # verb). The full stderr stays in QueueRunResult / run log.
            reason = result.stderr[-500:].strip() or f"Command exited with {result.returncode}"
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
