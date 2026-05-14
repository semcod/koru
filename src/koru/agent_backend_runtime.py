"""Runtime *agent UI* backends — how ``autonomous`` reaches an IDE-side LLM.

Static capability profiles live in :mod:`koru.agent_backends`; this module holds
the small :class:`AgentBackend` protocol and the first concrete implementation
(Unix socket + autopilot ``drive``), so :mod:`koru.autonomous` does not call
:class:`~koru.autopilot.client.AutopilotClient` directly.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from .autopilot.client import AutopilotClient


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


__all__ = ["AgentBackend", "PluginSocketBackend"]
