"""Deterministic patch transaction: apply, verify, promote or refuse.

This layer never talks to an LLM. It takes a diff that already exists and
decides — from the workspace state alone — whether it may land. Keeping the
model out of it is what makes the outcome reproducible: the same patch against
the same workspace always resolves the same way, so retry policy can live
above it without muddying the decision.
"""

from __future__ import annotations

import logging
import os
from collections.abc import Callable
from pathlib import Path
from uuid import uuid4

from koru.queue.patch_mode import (
    NO_PATCH_EMITTED,
    PATCH_DOES_NOT_APPLY,
    PATCH_INTRODUCES_SYMLINK,
    PROMOTION_APPLY,
    PROMOTION_ARTIFACT,
    PROMOTION_BRANCH,
    PROMOTION_COMMIT,
    PROMOTION_CONFLICT,
    PROMOTION_FAILED,
    PROMOTION_REFUSED_DIRTY_REPO,
    UNSAFE_DIRTY_WORKSPACE,
    VERIFY_BASELINE_FAILED,
    VERIFY_FAILED_ISOLATED,
    VERIFY_FAILED_ROLLED_BACK,
    PatchOutcome,
    apply_unified_diff,
    build_manifest,
    commit_worktree,
    diff_target_files,
    dirty_paths,
    extract_unified_diff,
    manifest_drift,
    promotion_mode,
    repository_is_clean,
    revert_files,
    staging_worktree,
    symlink_creations,
    symlinks_allowed,
    worktree_enabled,
    write_patch_artifact,
)
from koru.queue.types import CommandResult

_logger = logging.getLogger(__name__)


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
    manifest: dict | None = None,
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

    if symlink_creations(diff) and not symlinks_allowed():
        # git apply blocks `../` traversal but not a link pointing anywhere on
        # the filesystem, which would let a scoped patch reach outside its
        # workspace. Refuse by default; KORU_QUEUE_ALLOW_SYMLINKS=1 opts in.
        return result, PatchOutcome(
            code=PATCH_INTRODUCES_SYMLINK,
            message=(
                "the patch creates a symlink, which would let it point outside the "
                "workspace it is scoped to. Set KORU_QUEUE_ALLOW_SYMLINKS=1 if this "
                "project legitimately needs agent-authored symlinks."
            ),
        )

    verify_command = resolve_verify_command(project, ticket)
    targets = diff_target_files(project, diff)
    isolated = verify_command and worktree_enabled(project)
    mode = promotion_mode(ticket)
    run_id = uuid4().hex[:12]

    if mode == PROMOTION_ARTIFACT:
        # Deliver the patch as a reviewable file and change nothing. Useful on a
        # shared checkout, and the only mode that needs no verification at all.
        directory = write_patch_artifact(
            project,
            run_id,
            diff,
            {
                "run_id": run_id,
                "ticket_id": ticket.get("id"),
                "targets": list(targets),
                "verify_command": verify_command,
                "promotion_mode": mode,
            },
        )
        _logger.info("koru.queue.patch_artifact run_id=%s path=%s", run_id, directory)
        return result, None

    if mode == PROMOTION_COMMIT and not repository_is_clean(project):
        return result, PatchOutcome(
            code=PROMOTION_REFUSED_DIRTY_REPO,
            message=(
                "promotion_mode=commit requires a clean repository so the commit "
                "contains only this patch, but the working tree has uncommitted "
                "changes. Commit or stash them, or use promotion_mode=branch."
            ),
        )

    if isolated:
        # Freeze the plan before staging. The manifest records the base commit
        # and the exact content of every target, so promotion can prove the
        # world did not move underneath a verification that took minutes.
        plan = manifest or build_manifest(
            project,
            run_id=run_id,
            ticket=ticket,
            diff=diff,
            targets=targets,
            verify_command=verify_command,
            mode=mode,
            attempt=1,
            max_attempts=1,
        )
        staged = _stage_patch_in_worktree(
            project, diff, verify_command, shell_runner, mode=mode, run_id=run_id, ticket=ticket,
        )
        if staged is not None:
            return result, staged
        if mode == PROMOTION_BRANCH:
            # The verified result already lives on its own ref; deliberately
            # nothing is written to the shared working tree.
            return result, None
        drift = manifest_drift(project, plan)
        if drift:
            return result, PatchOutcome(
                code=PROMOTION_CONFLICT,
                message=(
                    "the workspace moved while the patch was being verified, so it was "
                    f"not promoted ({drift}). Another session most likely edited it; "
                    "re-run the ticket against the new state."
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
    *,
    mode: str = PROMOTION_APPLY,
    run_id: str = "",
    ticket: dict | None = None,
) -> PatchOutcome | None:
    """Prove a patch in a throwaway worktree before it touches the workspace.

    Nothing reaches the real tree until the patch has both applied and passed
    its gate in isolation, so a bad patch — or one racing another agent's edits
    — costs a discarded directory rather than a broken workspace. Under
    ``promotion_mode=branch`` the verified result is committed here and the
    branch ref outlives the worktree, so the shared tree is never written to.
    """
    targets = diff_target_files(project, diff)
    with staging_worktree(project, targets) as staged:
        if staged is None:
            return None  # cannot isolate; the caller's dirty check still guards us

        # Establish that the gate passes here *before* the patch exists. A suite
        # that resolves fixtures relative to the repo root, or otherwise assumes
        # its usual location on disk, fails inside a worktree no matter what the
        # patch says — and blaming the agent for that is a false negative.
        baseline = shell_runner(verify_command, staged)
        if baseline.returncode != 0:
            output = (baseline.stderr or baseline.stdout or "").strip()[-400:]
            return PatchOutcome(
                code=VERIFY_BASELINE_FAILED,
                message=(
                    f"`{verify_command}` already fails in a clean worktree "
                    f"(exit {baseline.returncode}), so the patch could not be judged "
                    "there and nothing was promoted. The suite likely depends on paths "
                    "outside the repository; re-run with KORU_QUEUE_WORKTREE=0 to "
                    f"verify in the checkout itself. Baseline output: {output}"
                ),
            )

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
            if mode == PROMOTION_BRANCH:
                branch = f"koru/run-{run_id}"
                ticket_id = (ticket or {}).get("id") or "ticket"
                ok, detail = commit_worktree(
                    staged,
                    branch,
                    f"koru({ticket_id}): verified patch\n\nrun_id: {run_id}",
                    applied.changed_files,
                )
                if not ok:
                    return PatchOutcome(
                        code=PROMOTION_FAILED,
                        message=f"verified patch could not be committed to {branch}: {detail}",
                    )
                _logger.info("koru.queue.patch_branch branch=%s commit=%s", branch, detail)
            return None
        output = (verify.stderr or verify.stdout or "").strip()[-600:]
        return PatchOutcome(
            code=VERIFY_FAILED_ISOLATED,
            message=(
                "patch failed verification in an isolated worktree, so the workspace "
                f"was left untouched. `{verify_command}` exited {verify.returncode}: {output}"
            ),
        )
