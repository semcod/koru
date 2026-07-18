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

from koru.queue.patch_mode import PatchOutcome, build_retry_prompt, redact_secrets
from koru.queue.patch_transaction import apply_proposed_patch
from koru.queue.types import CommandResult


def patch_retry_budget() -> int:
    """How many times to re-ask an agent whose diff would not apply."""
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
) -> tuple[CommandResult, PatchOutcome | None]:
    """Apply the agent's patch, re-asking with the exact rejection on failure.

    A malformed or stale diff is a mechanical problem the agent can fix once it
    sees ``git apply``'s complaint, so those attempts are retried. A patch that
    applies but fails verification is a *substantive* failure — retrying it
    would just burn another agent run on the same wrong idea — so it is not.
    """
    base_prompt = str(action.get("prompt") or "")
    remaining = patch_retry_budget()
    while True:
        result, outcome = apply_proposed_patch(project, result, ticket, shell_runner)
        if outcome is None or not outcome.retryable or remaining <= 0:
            return result, outcome
        remaining -= 1
        retry_action = _enrich_llm_request_with_context(
            {**action, "prompt": build_retry_prompt(base_prompt, outcome.diagnostics or outcome.message)},
            project,
        )
        result = llm_runner(retry_action, project)
        if result.returncode != 0:
            return result, outcome
