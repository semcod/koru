"""Thin Koru adapter for the external ``tillm`` shell-client plugin."""

from __future__ import annotations

import os
import sys
from collections.abc import Iterable
from pathlib import Path
from typing import Any


def ensure_local_tillm_path() -> None:
    """Make a local ``tillm`` checkout importable.

    Candidates, in order: ``KORU_TILLM_PATH`` (explicit override for installed
    koru packages running outside the semcod tree), then the sibling
    ``semcod/tillm/src`` of a source checkout.
    """
    candidates: list[Path] = []
    env_path = (os.environ.get("KORU_TILLM_PATH") or "").strip()
    if env_path:
        candidates.append(Path(env_path).expanduser())
    candidates.append(Path(__file__).resolve().parents[3] / "tillm" / "src")
    for candidate in candidates:
        if candidate.is_dir():
            value = str(candidate)
            if value not in sys.path:
                sys.path.insert(0, value)
            return


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


def shell_drive_client_id(agent_id: str) -> str | None:
    """Canonical tillm client id when ``agent_id`` names a shell client, else None."""
    ensure_local_tillm_path()
    try:
        from tillm.registry import get_client_spec, normalize_client_id
    except ImportError:
        return None
    spec = get_client_spec(normalize_client_id(agent_id))
    return spec.id if spec is not None else None


# Tokens the autonomous CLI accepts as shell-client targets. Used only to
# recognize *intent* when the tillm package itself cannot be imported, so the
# caller can fail loudly instead of silently routing a shell-client target to
# the IDE plugin lane. Keep in sync with tillm's registry ids.
_FALLBACK_SHELL_CLIENT_TOKENS = frozenset(
    {
        "aider",
        "claude",
        "claude-code",
        "codex",
        "devin",
        "gemini-cli",
        "opencode",
        "qwen-code",
    }
)


def tillm_available() -> bool:
    """True when the tillm package is importable (bundled sibling or installed)."""
    ensure_local_tillm_path()
    try:
        import tillm  # noqa: F401
    except ImportError:
        return False
    return True


def looks_like_shell_client(agent_id: str) -> bool:
    """True when ``agent_id`` names a shell LLM client, even if tillm is missing."""
    token = (agent_id or "").strip().lower()
    if not token:
        return False
    if shell_drive_client_id(token):
        return True
    return token in _FALLBACK_SHELL_CLIENT_TOKENS


def detect_available_shell_client() -> str | None:
    """Canonical id of the first shell client whose CLI is on PATH, else None."""
    for row in detect_shell_agent_rows():
        if row.get("launchable"):
            return str(row["id"])
    return None


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
    model: str | None = None,
    execute_profile: str = "default",
) -> dict[str, object]:
    ensure_local_tillm_path()
    from tillm.compat import drive_koru_chat

    return drive_koru_chat(
        client_id=client_id,
        project=project,
        prompt=prompt,
        execute=execute,
        model=model,
        execute_profile=execute_profile,
    )


def tillm_cli_main(argv: list[str]) -> int:
    ensure_local_tillm_path()
    from tillm.cli import main as main_impl

    return main_impl(argv)


__all__ = [
    "autopilot_backend_for_shell_agent",
    "detect_available_shell_client",
    "detect_shell_agent_rows",
    "drive_shell_chat",
    "ensure_local_tillm_path",
    "is_shell_agent",
    "launch_shell_agent",
    "looks_like_shell_client",
    "shell_agent_backend_aliases",
    "shell_agent_backend_profiles",
    "shell_agent_available",
    "shell_agent_process_patterns",
    "shell_drive_client_id",
    "shell_tool_registry_entries",
    "tillm_available",
    "tillm_cli_main",
]
