"""Runtime *agent UI* backends — how ``autonomous`` reaches an IDE-side LLM.

Static capability profiles live in :mod:`koru.agent_backends`; this module holds
the :class:`AgentBackend` protocol and concrete implementations
(Unix socket, MCP, CLI, headless), so :mod:`koru.autonomous` does not call
:class:`~koru.autopilot.client.AutopilotClient` directly.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

from .autopilot.client import AutopilotClient


@runtime_checkable
class AgentBackend(Protocol):
    """Push a prompt toward the agent UI (chat / drive session) for this project."""

    def send_chat(
        self,
        project: Path,
        prompt: str,
        *,
        ide: str,
        submit: bool,
        ticket_id: str | None = None,
    ) -> dict[str, Any]:
        """Return the same shape as :meth:`AutopilotClient.drive` (``ok``, ``message``, …)."""
        ...

    def apply_edits(self, project: Path, edits: list[dict[str, Any]]) -> None:
        """Apply file edits directly to the project."""
        ...


@dataclass
class PluginSocketBackend:
    """Plugin + unix socket — maps ``send_chat`` to autopilot ``drive``."""

    client: AutopilotClient

    def send_chat(
        self,
        project: Path,
        prompt: str,
        *,
        ide: str,
        submit: bool,
        ticket_id: str | None = None,
    ) -> dict[str, Any]:
        del project, ticket_id  # reserved for future routing / logging
        return self.client.drive(prompt, submit=submit, ide=ide)

    def apply_edits(self, project: Path, edits: list[dict[str, Any]]) -> None:
        """Apply edits via autopilot daemon (if supported)."""
        # TODO: Implement apply_edits for plugin backend
        # This would require extending the autopilot protocol
        pass


@dataclass
class McpToolBackend:
    """Backend for MCP-based IDEs (Cursor, Windsurf, Claude)."""

    def send_chat(
        self,
        project: Path,
        prompt: str,
        *,
        ide: str,
        submit: bool,
        ticket_id: str | None = None,
    ) -> dict[str, Any]:
        """Send chat prompt via MCP tool invocation."""
        # TODO: Implement MCP tool invocation for send_chat
        # This would use the MCP server's chat capabilities
        return {"ok": False, "message": "MCP send_chat not yet implemented"}

    def apply_edits(self, project: Path, edits: list[dict[str, Any]]) -> None:
        """Apply edits via MCP koru_propose_edits tool."""
        # TODO: Implement MCP tool invocation for apply_edits
        pass


@dataclass
class CursorCliBackend:
    """Backend for Cursor CLI (cursor agent chat ...)."""

    def send_chat(
        self,
        project: Path,
        prompt: str,
        *,
        ide: str,
        submit: bool,
        ticket_id: str | None = None,
    ) -> dict[str, Any]:
        """Send chat prompt via cursor CLI."""
        cmd = ["cursor", "agent", "chat", prompt]
        if ticket_id:
            cmd.extend(["--ticket-id", ticket_id])
        result = subprocess.run(cmd, cwd=project, check=False, capture_output=True, text=True)
        return {
            "ok": result.returncode == 0,
            "message": result.stdout or result.stderr,
        }

    def apply_edits(self, project: Path, edits: list[dict[str, Any]]) -> None:
        """Cursor CLI doesn't support direct apply_edits."""
        raise NotImplementedError("CursorCliBackend does not support apply_edits")


@dataclass
class HeadlessBackend:
    """Headless backend with no IDE (only MCP/queue operations)."""

    def send_chat(
        self,
        project: Path,
        prompt: str,
        *,
        ide: str,
        submit: bool,
        ticket_id: str | None = None,
    ) -> dict[str, Any]:
        """Headless backend cannot send chat messages."""
        return {
            "ok": False,
            "message": "HeadlessBackend does not support send_chat",
        }

    def apply_edits(self, project: Path, edits: list[dict[str, Any]]) -> None:
        """Apply edits directly to files (no IDE)."""
        for edit in edits:
            path = project / edit.get("path", "")
            if not path.exists():
                continue
            content = path.read_text(encoding="utf-8")
            old_text = edit.get("old_text", "")
            new_text = edit.get("new_text", "")
            if old_text and old_text in content:
                content = content.replace(old_text, new_text)
                path.write_text(content, encoding="utf-8")


def get_backend(name: str, **kwargs: Any) -> AgentBackend:
    """Get a backend instance by name.

    Args:
        name: Backend name (plugin_socket, mcp_tool, cursor_cli, headless)
        **kwargs: Additional backend-specific arguments

    Returns:
        AgentBackend instance

    Raises:
        ValueError: If backend name is unknown
    """
    backends: dict[str, type[AgentBackend]] = {
        "plugin_socket": PluginSocketBackend,
        "mcp_tool": McpToolBackend,
        "cursor_cli": CursorCliBackend,
        "headless": HeadlessBackend,
    }
    if name not in backends:
        raise ValueError(f"Unknown backend: {name}. Available: {list(backends.keys())}")
    return backends[name](**kwargs)


__all__ = [
    "AgentBackend",
    "PluginSocketBackend",
    "McpToolBackend",
    "CursorCliBackend",
    "HeadlessBackend",
    "get_backend",
]
