"""Experimental registry of IDE / LLM *agent backend* profiles.

This module does **not** perform injection — it documents which transports
exist today and which capabilities are realistic per backend.  Use it
from docs, tests, and future refactors that unify ``autopilot drive`` with
queue executors.

See: ``docs/agent-backends-architecture.md``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final


@dataclass(frozen=True)
class AgentBackendProfile:
    """Static description of one way koru can reach an IDE-side agent."""

    id: str
    transport: str
    can_push_chat: bool
    can_pull_chat_text: bool
    needs_gui_session: bool
    mcp_tools_only: bool
    primary_code: str


_PROFILES: Final[tuple[AgentBackendProfile, ...]] = (
    AgentBackendProfile(
        id="vscode_family_plugin_socket",
        transport="unix_socket + VS Code extension (VSIX)",
        can_push_chat=True,
        can_pull_chat_text=False,
        needs_gui_session=True,
        mcp_tools_only=False,
        primary_code="plugins/koru-autopilot-vscode/",
    ),
    AgentBackendProfile(
        id="jetbrains_plugin_socket",
        transport="unix_socket + IntelliJ plugin",
        can_push_chat=True,
        can_pull_chat_text=False,
        needs_gui_session=True,
        mcp_tools_only=False,
        primary_code="plugins/koru-autopilot-jetbrains/",
    ),
    AgentBackendProfile(
        id="mcp_stdio_server",
        transport="MCP stdio (IDE is client)",
        can_push_chat=False,
        can_pull_chat_text=False,
        needs_gui_session=False,
        mcp_tools_only=True,
        primary_code="src/koru/mcp_server.py",
    ),
    AgentBackendProfile(
        id="os_keyboard_injector",
        transport="xdotool / wtype / ydotool / clipboard",
        can_push_chat=True,
        can_pull_chat_text=False,
        needs_gui_session=True,
        mcp_tools_only=False,
        primary_code="src/koru/autopilot/injector.py",
    ),
    AgentBackendProfile(
        id="vendor_agent_cli",
        transport="subprocess (cursor agent, claude, …)",
        can_push_chat=True,
        can_pull_chat_text=False,
        needs_gui_session=False,
        mcp_tools_only=False,
        primary_code="src/koru/queue.py (run_process pattern)",
    ),
)


def list_agent_backend_ids() -> tuple[str, ...]:
    """Return stable backend profile ids (for config validation / docs)."""
    return tuple(p.id for p in _PROFILES)


def iter_agent_backend_profiles() -> tuple[AgentBackendProfile, ...]:
    """Return every registered profile (stable order)."""
    return _PROFILES


def get_agent_backend_profile(backend_id: str) -> AgentBackendProfile | None:
    """Return a profile or ``None`` if *backend_id* is unknown."""
    for p in _PROFILES:
        if p.id == backend_id:
            return p
    return None


__all__ = [
    "AgentBackendProfile",
    "get_agent_backend_profile",
    "iter_agent_backend_profiles",
    "list_agent_backend_ids",
]
