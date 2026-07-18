"""Phases of the deterministic patch transaction.

The pipeline reads ``preflight → staging → verification → promotion``, with
``rollback`` for the one path that can leave a half-applied workspace. Each
phase is importable and testable on its own; ``service`` only sequences them.
"""

from __future__ import annotations

from koru.queue.transaction.preflight import (
    ManifestFreeze,
    build_patch_plan,
    extract_patch,
    screen_diff_contents,
    screen_direct_apply,
    screen_promotion_preconditions,
)
from koru.queue.transaction.promotion import (
    commit_if_requested,
    commit_on_run_branch,
    deliver_patch_artifact,
    guard_promotion,
)
from koru.queue.transaction.result import PatchPlan, PatchTransactionResult, StagingResult
from koru.queue.transaction.rollback import roll_back_failed_verify
from koru.queue.transaction.service import execute_patch_transaction
from koru.queue.transaction.staging import stage_patch
from koru.queue.transaction.verification import (
    resolve_verify_command,
    skip_verify_baseline,
    verify_output,
)

__all__ = [
    "ManifestFreeze",
    "PatchPlan",
    "PatchTransactionResult",
    "StagingResult",
    "build_patch_plan",
    "commit_if_requested",
    "commit_on_run_branch",
    "deliver_patch_artifact",
    "execute_patch_transaction",
    "extract_patch",
    "guard_promotion",
    "resolve_verify_command",
    "roll_back_failed_verify",
    "screen_diff_contents",
    "screen_direct_apply",
    "screen_promotion_preconditions",
    "skip_verify_baseline",
    "stage_patch",
    "verify_output",
]
