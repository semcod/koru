"""Choosing the gate a patch must pass, and running it.

Resolution is deliberately separate from execution: which command proves a
patch is good is a governance question with several fallbacks, while running it
is mechanical. Keeping them apart is what will let the fallback chain be
replaced by a named profile registry without touching the transaction.
"""

from __future__ import annotations

import os
from pathlib import Path

from koru.queue.types import CommandResult

_VERIFY_COMMAND_HEADS = frozenset({"node", "npm", "pytest", "python", "python3", "bash"})

#: How much of a failing gate's output travels back to the caller.
VERIFY_OUTPUT_LIMIT = 600
BASELINE_OUTPUT_LIMIT = 400


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

    from_criteria = _verify_command_from_criteria(ticket)
    if from_criteria:
        return from_criteria

    from_env = (os.environ.get("KORU_QUEUE_VERIFY_COMMAND") or "").strip()
    if from_env:
        return from_env

    return _verify_command_from_project(project)


def _verify_command_from_criteria(ticket: dict) -> str:
    """Read a gate out of acceptance criteria that were written as commands."""
    for item in ticket.get("acceptance_criteria") or []:
        cmd = str(item or "").strip()
        if cmd and cmd.split()[0] in _VERIFY_COMMAND_HEADS:
            return cmd
    return ""


def _verify_command_from_project(project: Path) -> str:
    """Fall back to the gate the project already declares in ``koru.yaml``."""
    try:
        import yaml
    except ImportError:
        return ""

    try:
        config = yaml.safe_load((project / "koru.yaml").read_text(encoding="utf-8"))
        commands = (((config or {}).get("when") or {}).get("before_complete_ticket") or {}).get(
            "commands",
        ) or []
    except (OSError, AttributeError, yaml.YAMLError):
        return ""
    return str(commands[0]).strip() if commands else ""


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
