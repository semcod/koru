"""What the transaction itself still knows about verification: policy, not commands.

Command resolution lives entirely in :mod:`koru.queue.verify` — the registry,
its resolver and the legacy compatibility chain. This module keeps only the
judgements the transaction makes around a gate it was handed: whether the
baseline may be skipped, and how a gate's output is quoted back.

``resolve_verify_command`` remains importable here for compatibility, but it is
the legacy chain, re-exported: the profile-aware path is
``koru.queue.verify.resolver.resolve_verify``.
"""

from __future__ import annotations

from koru.queue.types import CommandResult
from koru.queue.verify.legacy import resolve_legacy_verify_command as resolve_verify_command

__all__ = [
    "BASELINE_OUTPUT_LIMIT",
    "VERIFY_OUTPUT_LIMIT",
    "resolve_verify_command",
    "skip_verify_baseline",
    "verify_output",
]

#: How much of a failing gate's output travels back to the caller.
VERIFY_OUTPUT_LIMIT = 600
BASELINE_OUTPUT_LIMIT = 400


def skip_verify_baseline(ticket: dict | None) -> bool:
    """Repair tickets may legitimately fail verify before the patch lands."""
    if not ticket:
        return False
    labels = {str(label).lower() for label in (ticket.get("labels") or []) if label}
    if "type:development-defect" in labels:
        return True
    inputs = ticket.get("inputs") or {}
    return bool(inputs.get("skip_verify_baseline") or inputs.get("expect_broken_baseline"))


def verify_output(result: CommandResult, *, limit: int = VERIFY_OUTPUT_LIMIT) -> str:
    """The tail of a failing gate's output, preferring stderr."""
    return (result.stderr or result.stdout or "").strip()[-limit:]
