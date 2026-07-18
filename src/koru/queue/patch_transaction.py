"""Deterministic patch transaction: apply, verify, promote or refuse.

This layer never talks to an LLM. It takes a diff that already exists and
decides — from the workspace state alone — whether it may land. Keeping the
model out of it is what makes the outcome reproducible: the same patch against
the same workspace always resolves the same way, so retry policy can live
above it without muddying the decision.
"""

from __future__ import annotations

import os
from collections.abc import Callable
from pathlib import Path

from koru.queue.patch_mode import (
    NO_PATCH_EMITTED,
    PATCH_DOES_NOT_APPLY,
    PROMOTION_CONFLICT,
    UNSAFE_DIRTY_WORKSPACE,
    VERIFY_FAILED_ISOLATED,
    VERIFY_FAILED_ROLLED_BACK,
    PatchOutcome,
    apply_unified_diff,
    changed_since,
    diff_target_files,
    dirty_paths,
    extract_unified_diff,
    fingerprint_files,
    revert_files,
    staging_worktree,
    worktree_enabled,
)
from koru.queue.types import CommandResult


def resolve_verify_command(project: Path, ticket: dict) -> str:
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


def apply_proposed_patch(
    project: Path,
    result: CommandResult,
    ticket: dict,
    shell_runner: Callable[[str, Path], CommandResult],
) -> tuple[CommandResult, PatchOutcome | None]:
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
        return result, PatchOutcome(
            code=NO_PATCH_EMITTED,
            message=(
                "agent returned no unified diff, so nothing could be applied. "
                f"First line of the reply: {summary}"
            ),
            retryable=True,
        )

    verify_command = resolve_verify_command(project, ticket)
    targets = diff_target_files(project, diff)
    isolated = verify_command and worktree_enabled(project)

    if isolated:
        # Fingerprint before staging so a concurrent edit during verification
        # is caught at promotion time rather than silently overwritten.
        baseline = fingerprint_files(project, targets)
        staged = _stage_patch_in_worktree(project, diff, verify_command, shell_runner)
        if staged is not None:
            return result, staged
        conflicted = changed_since(project, baseline)
        if conflicted:
            return result, PatchOutcome(
                code=PROMOTION_CONFLICT,
                message=(
                    "the workspace changed while the patch was being verified, so it "
                    f"was not promoted: {', '.join(conflicted)}. Another session most "
                    "likely edited these files; re-run the ticket against the new state."
                ),
            )
    else:
        # Without isolation the only rollback is `git checkout --`, which
        # restores from the index and would destroy any pre-existing unstaged
        # work. Refuse rather than promise a rollback that loses the user's edits.
        dirty = dirty_paths(project, targets)
        if dirty:
            return result, PatchOutcome(
                code=UNSAFE_DIRTY_WORKSPACE,
                message=(
                    "refusing to apply the patch directly: "
                    f"{', '.join(dirty)} already carry uncommitted changes, and a "
                    "rollback would discard them. Commit or stash them, or enable "
                    "worktree isolation (KORU_QUEUE_WORKTREE=1)."
                ),
            )

    applied = apply_unified_diff(project, diff)
    if not applied.ok:
        return result, PatchOutcome(
            code=PATCH_DOES_NOT_APPLY,
            message=applied.detail,
            retryable=True,
            diagnostics=applied.detail,
        )

    if not verify_command or isolated:
        return result, None  # already verified in the worktree

    verify = shell_runner(verify_command, project)
    if verify.returncode == 0:
        return result, None

    revert_files(project, applied.changed_files)
    output = (verify.stderr or verify.stdout or "").strip()[-600:]
    return result, PatchOutcome(
        code=VERIFY_FAILED_ROLLED_BACK,
        message=(
            f"patch applied but verification failed, so it was rolled back. "
            f"`{verify_command}` exited {verify.returncode}: {output}"
        ),
        workspace_left_untouched=True,
    )


def _stage_patch_in_worktree(
    project: Path,
    diff: str,
    verify_command: str,
    shell_runner: Callable[[str, Path], CommandResult],
) -> PatchOutcome | None:
    """Prove a patch in a throwaway worktree before it touches the workspace.

    Nothing reaches the real tree until the patch has both applied and passed
    its gate in isolation, so a bad patch — or one racing another agent's edits
    — costs a discarded directory rather than a broken workspace.
    """
    targets = diff_target_files(project, diff)
    with staging_worktree(project, targets) as staged:
        if staged is None:
            return None  # cannot isolate; the caller's dirty check still guards us
        applied = apply_unified_diff(staged, diff)
        if not applied.ok:
            return PatchOutcome(
                code=PATCH_DOES_NOT_APPLY,
                message=applied.detail,
                retryable=True,
                diagnostics=applied.detail,
            )
        verify = shell_runner(verify_command, staged)
        if verify.returncode == 0:
            return None
        output = (verify.stderr or verify.stdout or "").strip()[-600:]
        return PatchOutcome(
            code=VERIFY_FAILED_ISOLATED,
            message=(
                "patch failed verification in an isolated worktree, so the workspace "
                f"was left untouched. `{verify_command}` exited {verify.returncode}: {output}"
            ),
        )
