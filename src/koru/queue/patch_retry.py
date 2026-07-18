"""Retry policy for patch tickets.

Sits above the deterministic transaction: it decides *whether to ask the agent
again*, which is a policy question, while the transaction only decides whether
a given patch may land. Only mechanical failures — a malformed diff, one that
no longer applies — are retried, because those are the ones a model can fix
once it sees the diagnostic. A patch that applied but failed its gate is wrong
on the merits, and re-asking would spend another agent run on the same idea.
"""

from __future__ import annotations

import os
from collections.abc import Callable
from pathlib import Path
from typing import Any
from uuid import uuid4

from koru.queue.patch_mode import (
    MANIFEST_MISMATCH,
    PATCH_DOES_NOT_APPLY,
    PatchOutcome,
    build_manifest,
    build_retry_prompt,
    current_file_excerpt,
    diff_target_files,
    extract_unified_diff,
    manifest_drift,
    persist_manifest,
    promotion_mode,
    redact_secrets,
)
from koru.queue.patch_transaction import apply_proposed_patch, resolve_verify_command
from koru.queue.types import CommandResult


def patch_retry_budget(ticket: dict | None = None) -> int:
    """How many times to re-ask an agent whose diff would not apply."""
    if ticket is not None:
        per_ticket = (ticket.get("inputs") or {}).get("max_patch_attempts")
        if per_ticket is not None:
            try:
                return max(0, int(per_ticket))
            except (TypeError, ValueError):
                pass
        execution = ticket.get("execution") or {}
        exec_attempts = execution.get("max_attempts")
        if exec_attempts is not None:
            try:
                return max(0, int(exec_attempts))
            except (TypeError, ValueError):
                pass
    raw = (os.environ.get("KORU_QUEUE_PATCH_RETRIES") or "").strip()
    try:
        return max(0, int(raw)) if raw else 1
    except ValueError:
        return 1


def apply_patch_with_retry(
    project: Path,
    result: CommandResult,
    ticket: dict,
    action: dict[str, Any],
    llm_runner: Callable[[dict[str, Any], Path], CommandResult],
    shell_runner: Callable[[str, Path], CommandResult],
    enrich: Callable[[dict[str, Any], Path], dict[str, Any]] | None = None,
) -> tuple[CommandResult, PatchOutcome | None]:
    """Apply the agent's patch, re-asking with the exact rejection on failure.

    A malformed or stale diff is a mechanical problem the agent can fix once it
    sees ``git apply``'s complaint, so those attempts are retried. A patch that
    applies but fails verification is a *substantive* failure — retrying it
    would just burn another agent run on the same wrong idea — so it is not.

    ``enrich`` re-attaches project context to the retry request; it is injected
    rather than imported so this module stays independent of the queue runner.
    """
    base_prompt = str(action.get("prompt") or "")
    budget = patch_retry_budget(ticket)
    remaining = budget
    manifest: dict | None = None

    while True:
        result, outcome = apply_proposed_patch(project, result, ticket, shell_runner, manifest)
        if outcome is None or not outcome.retryable or remaining <= 0:
            return result, outcome

        # Pin the base on the first failure. Every later attempt is judged
        # against that same snapshot, so a retry can never silently rebase onto
        # a workspace another session has moved in the meantime.
        if manifest is None:
            manifest = _pin_base(project, ticket, result, budget)
            persist_manifest(project, manifest)
        elif (drift := manifest_drift(project, manifest)):
            return result, PatchOutcome(
                code=MANIFEST_MISMATCH,
                message=(
                    "the workspace changed between patch attempts, so the retry was "
                    f"abandoned rather than rebased onto a moving target ({drift}). "
                    "Re-run the ticket against the new state."
                ),
            )

        remaining -= 1
        # git and test output can quote file contents, so redact before it
        # travels back out to the model.
        diagnostic = redact_secrets(outcome.diagnostics or outcome.message)
        prompt = build_retry_prompt(base_prompt, diagnostic)
        if manifest and outcome.code == PATCH_DOES_NOT_APPLY:
            # Safe only because the manifest guarantees these contents are still
            # the ones the patch must apply to.
            prompt += current_file_excerpt(project, tuple(manifest.get("touched_files") or ()))
        retry_action = {**action, "prompt": prompt}
        if enrich is not None:
            retry_action = enrich(retry_action, project)
        result = llm_runner(retry_action, project)
        if result.returncode != 0:
            return result, outcome


def _pin_base(project: Path, ticket: dict, result: CommandResult, budget: int) -> dict:
    """Freeze the base the remaining attempts must target.

    The first attempt is pinned precisely when it failed for a reason that still
    let us read its targets. A corrupt diff yields none — ``git apply
    --numstat`` cannot parse it — which is exactly the case retries exist for,
    so fall back to the files the ticket declared. A manifest that pins nothing
    would silently permit the rebase it is meant to prevent.
    """
    diff = extract_unified_diff(result.stdout) or ""
    targets = diff_target_files(project, diff) or tuple(
        str(rel) for rel in (ticket.get("files") or [])
    )
    return build_manifest(
        project,
        run_id=uuid4().hex[:12],
        ticket=ticket,
        diff=diff,
        targets=targets,
        verify_command=resolve_verify_command(project, ticket),
        mode=promotion_mode(ticket),
        attempt=1,
        max_attempts=budget + 1,
    )
