"""Main queue runner logic for executing planfile tickets."""


import hashlib
import json
import logging
import os
import uuid
from collections.abc import Callable
from pathlib import Path
from typing import Any

from koru.queue.context import build_project_context
from koru.queue.human import default_human_prompt
from koru.queue.locking import queue_runner_lock, ticket_claim_or_error
from koru.queue.patch_mode import (
    apply_unified_diff,
    build_patch_prompt,
    build_retry_prompt,
    diff_target_files,
    extract_unified_diff,
    patch_mode_enabled,
    revert_files,
    staging_worktree,
    worktree_enabled,
)
from koru.queue.planfile_ticket_note import append_shell_evidence_note
from koru.queue.runners import (
    _DEFAULT_LLM_MODEL,
    run_api_request,
    run_llm_request,
    run_process,
    run_shell_command,
)
from koru.queue.shell_evidence import LLM_RUN_NOTE_TAG, SHELL_RUN_NOTE_TAG, format_shell_run_note
from koru.queue.ticket import (
    parse_next_ticket,
    planfile_command,
    ticket_api_request,
    ticket_command,
    ticket_llm_request,
)
from koru.queue.types import CommandResult, QueueRunResult

_logger = logging.getLogger(__name__)


def _source_tool(ticket: dict) -> str:
    source = ticket.get("source")
    if isinstance(source, dict):
        return str(source.get("tool") or "")
    return str(source or "")


def _resolve_executor_kind(ticket: dict, interactive: bool, dry_run: bool) -> str:
    """Determine executor kind from ticket metadata."""
    executor = ticket.get("executor") or {}
    raw_kind = executor.get("kind")
    if raw_kind is None:
        return "human"
    return str(raw_kind or "human")


def _handle_human_ticket(
    ticket: dict,
    ticket_id: str,
    interactive: bool,
    dry_run: bool,
    project: Path,
    actor: str,
    planfile_runner: Callable[[list[str], Path], CommandResult],
    prompt_runner: Callable[[str, str], str | None],
) -> QueueRunResult:
    """Handle human executor ticket."""
    inputs = ticket.get("inputs") or {}
    prompt = str(
        inputs.get("prompt") or ticket.get("description") or ticket.get("name") or ticket_id,
    )
    if not interactive or dry_run:
        return QueueRunResult(
            status="waiting_input",
            ticket_id=ticket_id,
            executor_kind="human",
            message=prompt,
        )
    answer = prompt_runner(prompt, ticket_id)
    if not answer:
        return QueueRunResult(
            status="waiting_input",
            ticket_id=ticket_id,
            executor_kind="human",
            message=prompt,
        )
    claimed = ticket_claim_or_error(
        project,
        ticket_id,
        actor,
        planfile_runner=planfile_runner,
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
        executor_kind="human",
        message=answer,
    )


def _resolve_ticket_action(
    ticket: dict,
    executor_kind: str,
) -> tuple[Any, str] | None:
    """Return (action, missing_prompt) or None for unsupported executor."""
    if executor_kind == "api":
        return ticket_api_request(
            ticket
        ), "API ticket is missing inputs.api_endpoint or executor.handler"
    if executor_kind == "llm":
        return ticket_llm_request(
            ticket
        ), "LLM ticket is missing inputs.prompt (or description / name)"
    if executor_kind == "shell":
        return ticket_command(ticket), "Shell ticket is missing inputs.script or executor.handler"
    return None


def _handle_dry_run(
    ticket_id: str,
    executor_kind: str,
    action: Any,
) -> QueueRunResult:
    message = json.dumps(action) if isinstance(action, dict) else str(action)
    return QueueRunResult(
        status="dry_run",
        ticket_id=ticket_id,
        executor_kind=executor_kind,
        message=message,
    )


def _claim_and_start(
    project: Path,
    ticket_id: str,
    actor: str,
    planfile_runner: Callable[[list[str], Path], CommandResult],
) -> QueueRunResult | None:
    claimed = ticket_claim_or_error(project, ticket_id, actor, planfile_runner=planfile_runner)
    if claimed:
        return claimed
    planfile_command(
        project,
        ["ticket", "start", ticket_id],
        runner=planfile_runner,
    )
    return None


def _enrich_llm_request_with_context(
    action: dict[str, Any],
    project: Path,
) -> dict[str, Any]:
    """Attach project context to *action* when the ticket requests it.

    Builds the context string, injects it as ``context_text``, and records
    assembly metadata under ``context_metadata``.  Returns *action* unchanged
    when no context was requested.
    """
    ctx = build_project_context(project, action)
    if ctx is None:
        return action
    enriched = dict(action)
    enriched["context_text"] = ctx.text
    enriched["context_metadata"] = {
        "included_files": ctx.included_files,
        "truncated": ctx.truncated,
        "total_chars": ctx.total_chars if ctx.truncated else len(ctx.text),
    }
    _logger.debug(
        "koru.queue.llm_context files=%d truncated=%s chars=%d ticket_id=?",
        len(ctx.included_files),
        ctx.truncated,
        enriched["context_metadata"]["total_chars"],
    )
    return enriched


def _execute_action(
    executor_kind: str,
    action: Any,
    project: Path,
    ticket_id: str,
    api_runner: Callable[[dict[str, Any], Path], CommandResult],
    llm_runner: Callable[[dict[str, Any], Path], CommandResult],
    shell_runner: Callable[[str, Path], CommandResult],
) -> tuple[CommandResult, str]:
    if executor_kind == "api":
        result = api_runner(action, project)
        action_label = f"{action['method']} {action['endpoint']}"
    elif executor_kind == "llm":
        action = _enrich_llm_request_with_context(action, project)
        result = llm_runner(action, project)
        action_label = f"llm {action.get('model') or _DEFAULT_LLM_MODEL}"
    else:
        try:
            from koru.activity_log import activity

            activity("QUEUE", f"shell {ticket_id}: {action}")
        except Exception:
            pass  # best-effort progress logging — must never break the queue
        result = shell_runner(str(action), project)
        action_label = str(action)
    return result, action_label


def _append_shell_evidence(
    project: Path,
    ticket_id: str,
    result: CommandResult,
    planfile_runner: Callable[[list[str], Path], CommandResult],
    *,
    tag: str = SHELL_RUN_NOTE_TAG,
) -> None:
    run_id = uuid.uuid4().hex[:16]
    note = format_shell_run_note(
        run_id=run_id,
        exit_code=result.returncode,
        stdout=result.stdout,
        stderr=result.stderr,
        tag=tag,
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
                "koru.queue.shell_evidence_appended_artifact ticket_id=%s run_id=%s path=%s",
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


def _resolve_verify_command(project: Path, ticket: dict) -> str:
    """Find the command that proves a patch is good.

    Ticket-level config is preferred but cannot be relied on: planfile's schema
    keeps a closed set of ``inputs`` keys and silently drops unknown ones. So
    fall back to the project's own declared gate — ``koru.yaml`` already names
    the command to run before completing a ticket, which is exactly this.
    """
    explicit = str((ticket.get("inputs") or {}).get("verify_command") or "").strip()
    if explicit:
        return explicit

    from_env = (os.environ.get("KORU_QUEUE_VERIFY_COMMAND") or "").strip()
    if from_env:
        return from_env

    try:
        import yaml

        config = yaml.safe_load((project / "koru.yaml").read_text(encoding="utf-8"))
        commands = (((config or {}).get("when") or {}).get("before_complete_ticket") or {}).get(
            "commands",
        ) or []
    except (OSError, ImportError, AttributeError, yaml.YAMLError):
        return ""
    return str(commands[0]).strip() if commands else ""


def _patch_retry_budget() -> int:
    """How many times to re-ask an agent whose diff would not apply."""
    raw = (os.environ.get("KORU_QUEUE_PATCH_RETRIES") or "").strip()
    try:
        return max(0, int(raw)) if raw else 1
    except ValueError:
        return 1


def _apply_patch_with_retry(
    project: Path,
    result: CommandResult,
    ticket: dict,
    action: dict[str, Any],
    llm_runner: Callable[[dict[str, Any], Path], CommandResult],
    shell_runner: Callable[[str, Path], CommandResult],
) -> tuple[CommandResult, str | None]:
    """Apply the agent's patch, re-asking with the exact rejection on failure.

    A malformed or stale diff is a mechanical problem the agent can fix once it
    sees ``git apply``'s complaint, so those attempts are retried. A patch that
    applies but fails verification is a *substantive* failure — retrying it
    would just burn another agent run on the same wrong idea — so it is not.
    """
    base_prompt = str(action.get("prompt") or "")
    remaining = _patch_retry_budget()
    while True:
        result, error, retryable = _apply_proposed_patch(project, result, ticket, shell_runner)
        if error is None or not retryable or remaining <= 0:
            return result, error
        remaining -= 1
        retry_action = _enrich_llm_request_with_context(
            {**action, "prompt": build_retry_prompt(base_prompt, error)},
            project,
        )
        result = llm_runner(retry_action, project)
        if result.returncode != 0:
            return result, error


def _apply_proposed_patch(
    project: Path,
    result: CommandResult,
    ticket: dict,
    shell_runner: Callable[[str, Path], CommandResult],
) -> tuple[CommandResult, str | None, bool]:
    """Apply the diff an agent proposed, then verify it, rolling back on failure.

    The agent's own exit code only says it produced *an answer*; whether that
    answer contained an applicable patch, and whether the patch is any good,
    are separate questions. A patch that fails its ticket's verify command is
    reverted, so a failed run leaves the workspace as it found it.
    """
    diff = extract_unified_diff(result.stdout)
    if diff is None:
        head = (result.stdout or "").strip().splitlines()
        summary = head[0][:200] if head else "(empty reply)"
        return result, (
            "agent returned no unified diff, so nothing could be applied. "
            f"First line of the reply: {summary}"
        ), True

    verify_command = _resolve_verify_command(project, ticket)

    if verify_command and worktree_enabled(project):
        staged_error, retryable = _stage_patch_in_worktree(
            project, diff, verify_command, shell_runner,
        )
        if staged_error is not None:
            return result, staged_error, retryable

    applied = apply_unified_diff(project, diff)
    if not applied.ok:
        return result, applied.detail, True

    if not verify_command:
        return result, None, False

    verify = shell_runner(verify_command, project)
    if verify.returncode == 0:
        return result, None, False

    revert_files(project, applied.changed_files)
    output = (verify.stderr or verify.stdout or "").strip()[-600:]
    return result, (
        f"patch applied but verification failed, so it was rolled back. "
        f"`{verify_command}` exited {verify.returncode}: {output}"
    ), False


def _stage_patch_in_worktree(
    project: Path,
    diff: str,
    verify_command: str,
    shell_runner: Callable[[str, Path], CommandResult],
) -> tuple[str | None, bool]:
    """Prove a patch in a throwaway worktree before it touches the workspace.

    Nothing reaches the real tree until the patch has both applied and passed
    its gate in isolation, so a bad patch — or one racing another agent's edits
    — costs a discarded directory rather than a broken workspace. Returns the
    failure reason and whether re-asking the agent could plausibly fix it.
    """
    targets = diff_target_files(project, diff)
    with staging_worktree(project, targets) as staged:
        if staged is None:
            return None, False  # cannot isolate; in-place apply + revert still guards us
        applied = apply_unified_diff(staged, diff)
        if not applied.ok:
            return applied.detail, True
        verify = shell_runner(verify_command, staged)
        if verify.returncode == 0:
            return None, False
        output = (verify.stderr or verify.stdout or "").strip()[-600:]
        return (
            "patch failed verification in an isolated worktree, so the workspace "
            f"was left untouched. `{verify_command}` exited {verify.returncode}: {output}"
        ), False


def _ticket_expects_edits(ticket: dict) -> bool:
    """Whether finishing this ticket means the declared files must change.

    Opt in explicitly with ``inputs.expect_files_changed``; scan-emitted
    refactor tickets are treated as edit tickets by default, since that is what
    "refactor" means. Tickets that merely *reference* files (a deploy recipe, a
    question) are unaffected.
    """
    inputs = ticket.get("inputs") or {}
    if "expect_files_changed" in inputs:
        return bool(inputs["expect_files_changed"])
    labels = {str(label).lower() for label in (ticket.get("labels") or [])}
    return "refactor" in labels


def _snapshot_declared_files(project: Path, ticket: dict) -> dict[str, str]:
    """Hash the ticket's declared files so edits can be detected afterwards."""
    snapshot: dict[str, str] = {}
    for rel in ticket.get("files") or []:
        path = project / str(rel)
        try:
            snapshot[str(rel)] = hashlib.sha256(path.read_bytes()).hexdigest()
        except OSError:
            snapshot[str(rel)] = ""  # missing now; creating it counts as a change
    return snapshot


def _verify_declared_files_changed(
    project: Path,
    ticket: dict,
    before: dict[str, str],
) -> str | None:
    """Return a failure reason when an edit ticket changed nothing.

    An agent that hits a permission prompt, refuses, or merely *describes* the
    change still exits 0, and without this check the queue closes the ticket as
    done while the code is untouched. Absence of any edit is cheap and
    unambiguous to detect, so it is worth catching even though it cannot prove
    the edit was *correct*.
    """
    if not before:
        return None
    after = _snapshot_declared_files(project, ticket)
    if any(after.get(rel) != digest for rel, digest in before.items()):
        return None
    listed = ", ".join(sorted(before))
    return (
        "agent reported success but left every declared file unchanged "
        f"({listed}). The work was not done — check the run note for a refusal, "
        "a permission prompt, or an answer that only described the change. "
        "Set inputs.expect_files_changed=false if this ticket is not meant to edit files."
    )


def _finalize_ticket(
    project: Path,
    ticket_id: str,
    executor_kind: str,
    result: CommandResult,
    action_label: str,
    planfile_runner: Callable[[list[str], Path], CommandResult],
    verification_error: str | None = None,
) -> QueueRunResult:
    if verification_error and result.returncode == 0:
        _append_shell_evidence(
            project, ticket_id, result, planfile_runner, tag=LLM_RUN_NOTE_TAG,
        )
        planfile_command(
            project,
            ["ticket", "block", ticket_id, "--reason", f"FAIL: {verification_error}"],
            runner=planfile_runner,
        )
        return QueueRunResult(
            status="failed",
            ticket_id=ticket_id,
            executor_kind=executor_kind,
            message=action_label,
            exit_code=1,
            stdout=result.stdout,
            stderr=verification_error,
        )
    if result.returncode == 0:
        if executor_kind == "shell":
            _append_shell_evidence(project, ticket_id, result, planfile_runner)
        elif executor_kind == "llm":
            # The model answer IS the deliverable — persist it on the ticket
            # instead of discarding stdout the way pre-0.1.373 releases did.
            _append_shell_evidence(
                project, ticket_id, result, planfile_runner, tag=LLM_RUN_NOTE_TAG
            )
        planfile_command(
            project,
            ["ticket", "done", ticket_id],
            runner=planfile_runner,
        )
        status = "completed"
    else:
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


def _next_ticket_or_result(
    project: Path,
    planfile_runner: Callable[[list[str], Path], CommandResult],
    queue_name: str | None = None,
) -> tuple[dict[str, Any] | None, QueueRunResult | None]:
    next_result = planfile_command(
        project,
        ["ticket", "list", "--status", "open", "--format", "json"],
        runner=planfile_runner,
    )
    if next_result.returncode != 0:
        from koru.queue.ticket import planfile_module_missing

        message = "planfile ticket list failed"
        if planfile_module_missing(f"{next_result.stdout}\n{next_result.stderr}"):
            message += (
                " — planfile module missing in the resolved environment; "
                "fix: pip install planfile into the project venv "
                "(or pip install 'koru[planfile]')"
            )
        return None, QueueRunResult(
            status="planfile_error",
            message=message,
            exit_code=next_result.returncode,
            stdout=next_result.stdout,
            stderr=next_result.stderr,
        )

    ticket = parse_next_ticket(next_result.stdout, queue_name=queue_name)
    if ticket is None:
        return None, QueueRunResult(status="idle", message="No runnable ticket found")
    return ticket, None


def _log_queue_ticket_start(ticket: dict[str, Any], ticket_id: str) -> None:
    ticket_name = str(ticket.get("name") or ticket_id)
    try:
        from koru.activity_log import activity

        activity(
            "QUEUE",
            f"start {ticket_id} ({ticket_name}) executor="
            f"{(ticket.get('executor') or {}).get('kind', 'human')}",
        )
    except Exception:
        pass  # best-effort progress logging — must never break the queue


def _resolve_action_or_result(
    *,
    ticket: dict[str, Any],
    ticket_id: str,
    executor_kind: str,
    interactive: bool,
    dry_run: bool,
    project: Path,
    planfile_runner: Callable[[list[str], Path], CommandResult],
) -> tuple[Any | None, QueueRunResult | None]:
    action_info = _resolve_ticket_action(ticket, executor_kind)
    if action_info is None:
        return None, QueueRunResult(
            status="unsupported_executor",
            ticket_id=ticket_id,
            executor_kind=executor_kind,
            message=f"Executor kind '{executor_kind}' is not implemented yet",
        )

    resolved_action, missing_prompt = action_info
    if resolved_action:
        return resolved_action, None
    if executor_kind == "shell" and not interactive and not dry_run:
        return "true", None

    planfile_command(
        project,
        ["ticket", "block", ticket_id, "--reason", missing_prompt],
        runner=planfile_runner,
    )
    return None, QueueRunResult(
        status="waiting_input",
        ticket_id=ticket_id,
        executor_kind=executor_kind,
        message=missing_prompt,
    )


def _run_next_planfile_task_impl(
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
    ``ticket claim --assigned-to <actor>`` for tracing / lease metadata when
    the installed planfile CLI supports it.
    """
    project = project.resolve()

    with queue_runner_lock(project):
        ticket, early_result = _next_ticket_or_result(
            project,
            planfile_runner,
            queue_name=queue_name,
        )
        if early_result is not None:
            return early_result
        assert ticket is not None

        ticket_id = str(ticket["id"])
        _log_queue_ticket_start(ticket, ticket_id)

        executor_kind = _resolve_executor_kind(ticket, interactive, dry_run)

        if executor_kind == "human":
            return _handle_human_ticket(
                ticket,
                ticket_id,
                interactive,
                dry_run,
                project,
                actor,
                planfile_runner,
                prompt_runner,
            )

        resolved_action, action_result = _resolve_action_or_result(
            ticket=ticket,
            ticket_id=ticket_id,
            executor_kind=executor_kind,
            interactive=interactive,
            dry_run=dry_run,
            project=project,
            planfile_runner=planfile_runner,
        )
        if action_result is not None:
            return action_result
        assert resolved_action is not None

        if dry_run:
            return _handle_dry_run(ticket_id, executor_kind, resolved_action)

        claimed = _claim_and_start(project, ticket_id, actor, planfile_runner)
        if claimed:
            return claimed

        expects_edits = _ticket_expects_edits(ticket)
        before = _snapshot_declared_files(project, ticket) if expects_edits else {}
        use_patch_mode = (
            executor_kind == "llm" and expects_edits and patch_mode_enabled(ticket)
        )
        if use_patch_mode:
            resolved_action = dict(resolved_action)
            resolved_action["prompt"] = build_patch_prompt(str(resolved_action.get("prompt") or ""))

        result, action_label = _execute_action(
            executor_kind,
            resolved_action,
            project,
            ticket_id,
            api_runner,
            llm_runner,
            shell_runner,
        )

        patch_error: str | None = None
        if use_patch_mode and result.returncode == 0:
            result, patch_error = _apply_patch_with_retry(
                project, result, ticket, resolved_action, llm_runner, shell_runner,
            )

        verification_error = patch_error
        if verification_error is None and expects_edits:
            verification_error = _verify_declared_files_changed(project, ticket, before)

        return _finalize_ticket(
            project,
            ticket_id,
            executor_kind,
            result,
            action_label,
            planfile_runner,
            verification_error,
        )


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
    from koru.bounded_contexts.planfile_queue.application import PlanfileQueueCommandService
    from koru.bounded_contexts.planfile_queue.commands import RunNextPlanfileTaskCommand
    from koru.cqrs import runtime_for_project

    return PlanfileQueueCommandService(runtime=runtime_for_project(project)).run_next_task(
        RunNextPlanfileTaskCommand(
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
    )
