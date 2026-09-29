from pathlib import Path
from typing import Any, Protocol


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
        """Return the same shape as :meth:`IDEControlClient.drive` (``ok``, ``message``, …)."""
        ...
