"""Everything decided before a single byte of the workspace changes.

Preflight answers two questions: is this diff even usable, and is the workspace
in a state where the requested promotion is safe? Both are answered from data
that already exists, so a refusal here costs nothing and leaves nothing to undo.
"""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from koru.queue.patch_mode import (
    NO_PATCH_EMITTED,
    PATCH_INTRODUCES_SYMLINK,
    PROMOTION_COMMIT,
    PROMOTION_REFUSED_DIRTY_REPO,
    UNSAFE_DIRTY_WORKSPACE,
    PatchOutcome,
    build_manifest,
    diff_target_files,
    dirty_paths,
    extract_unified_diff,
    persist_manifest,
    promotion_mode,
    repository_is_clean,
    symlink_creations,
    symlinks_allowed,
    worktree_enabled,
)
from koru.queue.transaction.result import PatchPlan
from koru.queue.transaction.verification import resolve_verify_command
from koru.queue.types import CommandResult


def extract_patch(result: CommandResult) -> tuple[str | None, PatchOutcome | None]:
    """Pull the unified diff out of an agent reply, or explain what came instead.

    The agent's exit code only says it produced *an answer*; whether that answer
    contained an applicable patch is a separate question.
    """
    diff = extract_unified_diff(result.stdout)
    if diff is not None:
        return diff, None
    head = (result.stdout or "").strip().splitlines()
    summary = head[0][:200] if head else "(empty reply)"
    return None, PatchOutcome(
        code=NO_PATCH_EMITTED,
        message=(
            "agent returned no unified diff, so nothing could be applied. "
            f"First line of the reply: {summary}"
        ),
        retryable=True,
    )


def screen_diff_contents(diff: str) -> PatchOutcome | None:
    """Refuse diffs whose content is unsafe regardless of where they apply.

    ``git apply`` blocks ``../`` traversal but not a link pointing anywhere on
    the filesystem, which would let a scoped patch reach outside its workspace.
    """
    if not symlink_creations(diff) or symlinks_allowed():
        return None
    return PatchOutcome(
        code=PATCH_INTRODUCES_SYMLINK,
        message=(
            "the patch creates a symlink, which would let it point outside the "
            "workspace it is scoped to. Set KORU_QUEUE_ALLOW_SYMLINKS=1 if this "
            "project legitimately needs agent-authored symlinks."
        ),
    )


def build_patch_plan(
    project: Path,
    ticket: dict,
    diff: str,
    manifest: dict | None = None,
) -> PatchPlan:
    """Resolve, once, every fact the later phases decide on."""
    verify_command = resolve_verify_command(project, ticket)
    return PatchPlan(
        project=project,
        ticket=ticket,
        diff=diff,
        targets=diff_target_files(project, diff),
        verify_command=verify_command,
        mode=promotion_mode(ticket),
        run_id=manifest["run_id"] if manifest else uuid4().hex[:12],
        isolated=bool(verify_command) and worktree_enabled(project),
    )


def screen_promotion_preconditions(plan: PatchPlan) -> PatchOutcome | None:
    """Refuse a promotion the workspace cannot honour cleanly."""
    if plan.mode != PROMOTION_COMMIT or repository_is_clean(plan.project):
        return None
    return PatchOutcome(
        code=PROMOTION_REFUSED_DIRTY_REPO,
        message=(
            "promotion_mode=commit requires a clean repository so the commit "
            "contains only this patch, but the working tree has uncommitted "
            "changes. Commit or stash them, or use promotion_mode=branch."
        ),
    )


def screen_direct_apply(plan: PatchPlan) -> PatchOutcome | None:
    """Refuse to patch dirty files in place, where rollback would lose work.

    Without isolation the only rollback is ``git checkout --``, which restores
    from the index and would destroy any pre-existing unstaged edit. Refusing
    beats promising a rollback that silently discards the user's work.
    """
    dirty = dirty_paths(plan.project, plan.targets)
    if not dirty:
        return None
    return PatchOutcome(
        code=UNSAFE_DIRTY_WORKSPACE,
        message=(
            "refusing to apply the patch directly: "
            f"{', '.join(dirty)} already carry uncommitted changes, and a "
            "rollback would discard them. Commit or stash them, or enable "
            "worktree isolation (KORU_QUEUE_WORKTREE=1)."
        ),
    )


class ManifestFreeze:
    """The plan pinned to disk, built once and re-persisted on demand.

    The manifest records the base commit and the exact content of every target,
    so promotion can prove the world did not move underneath a verification that
    took minutes. It is built lazily because some modes never need one, and only
    ever built *once* — a second build would pin a workspace that has since been
    patched, which is precisely the drift it exists to detect.
    """

    def __init__(self, plan: PatchPlan, manifest: dict | None = None) -> None:
        self._plan = plan
        self._manifest = manifest

    @property
    def manifest(self) -> dict | None:
        return self._manifest

    def freeze(self, *, attempt: int = 1, max_attempts: int = 1) -> dict:
        """Pin the plan if it is not pinned yet, then write it out."""
        if self._manifest is None:
            self._manifest = build_manifest(
                self._plan.project,
                run_id=self._plan.run_id,
                ticket=self._plan.ticket,
                diff=self._plan.diff,
                targets=self._plan.targets,
                verify_command=self._plan.verify_command,
                mode=self._plan.mode,
                attempt=attempt,
                max_attempts=max_attempts,
            )
        persist_manifest(self._plan.project, self._manifest)
        return self._manifest
