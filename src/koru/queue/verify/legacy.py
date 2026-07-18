"""The pre-profile ways a ticket used to name its gate. Compatibility only.

Every rung here hands the run an arbitrary shell string, which is exactly what
profiles exist to end. The chain survives so old tickets keep working, but it
lives inside the verify package: the resolver is its only caller, so there is
one place to watch it and one flag (``queue.verify_require_profile``) that
closes it. New tickets should say ``verify_profile``.
"""

from __future__ import annotations

import os
from pathlib import Path

_VERIFY_COMMAND_HEADS = frozenset({"node", "npm", "pytest", "python", "python3", "bash"})


def resolve_legacy_verify_command(project: Path, ticket: dict) -> str:
    """Find the command that proves a patch is good, the pre-profile way.

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
