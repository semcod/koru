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

#: Command heads that make an acceptance criterion look like a runnable gate.
#: Public: ticket templating consults the same set — one notion of
#: "command-shaped", not two drifting copies.
VERIFY_COMMAND_HEADS = frozenset({"node", "npm", "pytest", "python", "python3", "bash"})


def resolve_legacy_verify_command(project: Path, ticket: dict) -> str:
    """Find the command that proves a patch is good, the pre-profile way.

    Ticket-level config is preferred but cannot be relied on: planfile's schema
    keeps a closed set of ``inputs`` keys and silently drops unknown ones. So
    fall back to the project's own declared gate: ``koru.yaml`` first, then
    ``.planfile/.koru/policy.yaml``'s ``ci.command``. Named-profile enforcement
    remains the resolver's responsibility; this fallback never bypasses it.
    """
    explicit = str((ticket.get("inputs") or {}).get("verify_command") or "").strip()
    if explicit:
        return explicit

    from_criteria = verify_command_from_criteria(ticket)
    if from_criteria:
        return from_criteria

    from_env = (os.environ.get("KORU_QUEUE_VERIFY_COMMAND") or "").strip()
    if from_env:
        return from_env

    return _verify_command_from_project(project)


def verify_command_from_criteria(ticket: dict) -> str:
    """Read a gate out of acceptance criteria that were written as commands."""
    for item in ticket.get("acceptance_criteria") or []:
        cmd = str(item or "").strip()
        if cmd and cmd.split()[0] in VERIFY_COMMAND_HEADS:
            return cmd
    return ""


_TASKFILE_NAMES = ("Taskfile.yml", "Taskfile.yaml", "Taskfile.dist.yml", "Taskfile.dist.yaml")


def is_runnable_project_gate_command(project: Path, command: str) -> bool:
    """Return False when a declared ``task <target>`` gate lacks a Taskfile or target."""
    parts = command.strip().split()
    if not parts or parts[0] != "task":
        return True
    taskfile = next((project / name for name in _TASKFILE_NAMES if (project / name).is_file()), None)
    if taskfile is None:
        return False
    target = next((token for token in parts[1:] if not token.startswith("-")), "")
    if not target:
        return True
    try:
        text = taskfile.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return False
    return f"{target}:" in text


def _verify_command_from_project(project: Path) -> str:
    """Use the existing project gate before the declared Planfile CI gate."""
    try:
        import yaml
    except ImportError:
        return ""

    try:
        config = yaml.safe_load((project / "koru.yaml").read_text(encoding="utf-8"))
        commands = (((config or {}).get("when") or {}).get("before_complete_ticket") or {}).get(
            "commands",
        ) or []
    except FileNotFoundError:
        commands = []
    except (OSError, AttributeError, yaml.YAMLError):
        return ""
    for raw_command in commands:
        candidate = str(raw_command or "").strip()
        if candidate and is_runnable_project_gate_command(project, candidate):
            return candidate

    policy_path = project / ".planfile" / ".koru" / "policy.yaml"
    if policy_path.exists():
        try:
            policy = yaml.safe_load(policy_path.read_text(encoding="utf-8"))
        except (OSError, yaml.YAMLError):
            return ""
        if not isinstance(policy, dict) or not isinstance(policy.get("ci"), dict):
            return ""
        command = policy["ci"].get("command")
        if not isinstance(command, str):
            return ""
        if command.strip():
            return command.strip()

    return _auto_detect_verify_command(project)


def _auto_detect_verify_command(project: Path) -> str:
    """Auto-detect a sensible default verification gate from project markers."""
    if (
        (project / "pyproject.toml").is_file()
        or (project / "pytest.ini").is_file()
        or (project / "tests").is_dir()
    ):
        venv_pytest = project / ".venv" / "bin" / "pytest"
        if venv_pytest.is_file():
            return f"{venv_pytest} -q"
        return "pytest -q"
    if (project / "Cargo.toml").is_file():
        return "cargo test --locked"
    if (project / "package.json").is_file():
        return "npm test"
    return ""

