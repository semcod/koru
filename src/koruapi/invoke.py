"""Invoke koru integrations by id (used by HTTP API and CLI)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .integrations import get_integration
from .invoke_handlers import INTEGRATION_HANDLERS, InvokeError


def invoke_integration(
    integration_id: str,
    *,
    project: Path,
    method: str = "run",
    body: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Run an integration and return a JSON-serializable result."""
    spec = get_integration(integration_id)
    if spec is None:
        raise InvokeError(f"unknown integration: {integration_id!r}")

    handler = INTEGRATION_HANDLERS.get(integration_id)
    if handler is None:
        raise InvokeError(
            f"integration {integration_id!r} is catalogued but not wired for method={method!r}",
        )

    payload = body or {}
    return handler(project.resolve(), method, payload)
