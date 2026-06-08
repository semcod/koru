"""Thin Koru adapter for the external ``tillm`` shell-client plugin."""

from __future__ import annotations

import sys
from collections.abc import Iterable
from pathlib import Path
from typing import Any


def ensure_local_tillm_path() -> None:
    """Make sibling ``semcod/tillm`` importable in source checkouts."""
    candidate = Path(__file__).resolve().parents[3] / "tillm" / "src"
    if candidate.is_dir():
        value = str(candidate)
        if value not in sys.path:
            sys.path.insert(0, value)


def detect_shell_agent_rows(*, project_hint_ids: Iterable[str] = ()) -> list[dict[str, Any]]:
    ensure_local_tillm_path()
    try:
        from tillm.compat import detect_koru_agent_rows
    except ImportError:
        return []
    return detect_koru_agent_rows(project_hint_ids=project_hint_ids)


def autopilot_backend_for_shell_agent(agent_id: str) -> str | None:
    ensure_local_tillm_path()
    try:
        from tillm.compat import autopilot_backend_for_client
    except ImportError:
        return None
    return autopilot_backend_for_client(agent_id)


def is_shell_agent(agent_id: str) -> bool:
    ensure_local_tillm_path()
    try:
        from tillm.compat import is_shell_llm_client
    except ImportError:
        return False
    return is_shell_llm_client(agent_id)


def shell_agent_available(agent_id: str) -> bool:
    ensure_local_tillm_path()
    try:
        from tillm.compat import is_client_available
    except ImportError:
        return False
    return is_client_available(agent_id)


def shell_agent_process_patterns() -> tuple[tuple[str, str, tuple[str, ...]], ...]:
    ensure_local_tillm_path()
    try:
        from tillm.compat import shell_process_patterns
    except ImportError:
        return ()
    return shell_process_patterns()


def shell_tool_registry_entries() -> tuple[dict[str, object], ...]:
    ensure_local_tillm_path()
    try:
        from tillm.compat import tool_registry_entries
    except ImportError:
        return ()
    return tool_registry_entries()


def shell_agent_backend_profiles() -> tuple[dict[str, object], ...]:
    ensure_local_tillm_path()
    try:
        from tillm.compat import agent_backend_profiles
    except ImportError:
        return ()
    return agent_backend_profiles()


def shell_agent_backend_aliases() -> dict[str, str]:
    ensure_local_tillm_path()
    try:
        from tillm.compat import agent_backend_aliases
    except ImportError:
        return {}
    return agent_backend_aliases()


def launch_shell_agent(
    *,
    agent_id: str,
    project: Path,
    prompt: str,
    command: str | None = None,
) -> int:
    ensure_local_tillm_path()
    from tillm.compat import launch_koru_agent

    return launch_koru_agent(
        agent_id=agent_id,
        project=project,
        prompt=prompt,
        command=command,
    )


def drive_shell_chat(
    *,
    client_id: str,
    project: Path,
    prompt: str,
    execute: bool,
) -> dict[str, object]:
    ensure_local_tillm_path()
    from tillm.compat import drive_koru_chat

    return drive_koru_chat(
        client_id=client_id,
        project=project,
        prompt=prompt,
        execute=execute,
    )


def tillm_cli_main(argv: list[str]) -> int:
    ensure_local_tillm_path()
    from tillm.cli import main as main_impl

    return main_impl(argv)


__all__ = [
    "autopilot_backend_for_shell_agent",
    "detect_shell_agent_rows",
    "drive_shell_chat",
    "ensure_local_tillm_path",
    "is_shell_agent",
    "launch_shell_agent",
    "shell_agent_backend_aliases",
    "shell_agent_backend_profiles",
    "shell_agent_available",
    "shell_agent_process_patterns",
    "shell_tool_registry_entries",
    "tillm_cli_main",
]
