"""Deterministic patch transaction: apply, verify, promote or refuse.

The phases live in :mod:`koru.queue.transaction`; this module is the import
site callers have always used. It keeps the ``(result, outcome)`` pair the
queue runner and retry policy expect, so the split stayed invisible to them.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from koru.queue.patch_mode import PatchOutcome
from koru.queue.transaction import execute_patch_transaction, resolve_verify_command
from koru.queue.types import CommandResult

__all__ = ["apply_proposed_patch", "resolve_verify_command"]


def apply_proposed_patch(
    project: Path,
    result: CommandResult,
    ticket: dict,
    shell_runner: Callable[[str, Path], CommandResult],
    manifest: dict | None = None,
) -> tuple[CommandResult, PatchOutcome | None]:
    """Apply the diff an agent proposed, then verify it, rolling back on failure.

    ``None`` for the outcome means the patch landed; anything else says why it
    did not, as data rather than prose.
    """
    return execute_patch_transaction(
        project, result, ticket, shell_runner, manifest,
    ).as_tuple()
