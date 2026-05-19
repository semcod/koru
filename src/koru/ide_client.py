"""IDE control client abstraction for `koru` runtime paths.

This module is the anti-corruption boundary between orchestration code
(`autonomous`, agent backends, future queue runners) and the concrete
legacy autopilot socket client.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    from .autopilot.client import AutopilotClient


class IDEControlClient(Protocol):
    """Minimal interface `koru` runtime code expects from an IDE client."""

    def is_running(self) -> bool:
        ...

    def drive(
        self,
        text: str,
        *,
        submit: bool = True,
        ide: str = "auto",
        require_plugin: bool = False,
    ) -> dict[str, Any]:
        ...

    def status(self) -> dict[str, Any]:
        ...

    def shutdown(self) -> dict[str, Any]:
        ...


@dataclass
class LegacyAutopilotClientAdapter:
    """Expose legacy :class:`AutopilotClient` through :class:`IDEControlClient`."""

    client: AutopilotClient

    def is_running(self) -> bool:
        return bool(self.client.is_running())

    def drive(
        self,
        text: str,
        *,
        submit: bool = True,
        ide: str = "auto",
        require_plugin: bool = False,
    ) -> dict[str, Any]:
        from .activity_log import activity

        activity(
            "CHAT",
            f"drive → ide={ide} submit={submit} require_plugin={require_plugin} "
            f"({len(text)} znaków)",
            preview=text,
        )
        reply = self.client.drive(
            text, submit=submit, ide=ide, require_plugin=require_plugin,
        )
        backend = reply.get("backend", "?")
        ok = bool(reply.get("ok", True))
        activity(
            "CHAT",
            f"drive wynik: ok={ok} backend={backend} tool_id={reply.get('tool_id', '-')}",
        )
        return reply

    def status(self) -> dict[str, Any]:
        return self.client.status()

    def shutdown(self) -> dict[str, Any]:
        return self.client.shutdown()


def adapt_legacy_autopilot_client(client: AutopilotClient) -> IDEControlClient:
    """Wrap an existing legacy autopilot client as :class:`IDEControlClient`."""

    return LegacyAutopilotClientAdapter(client=client)


def build_legacy_ide_client(
    *,
    socket_path: Path | None = None,
    timeout: float = 5.0,
) -> IDEControlClient:
    """Construct :class:`IDEControlClient` backed by legacy autopilot socket client."""

    from .autopilot.client import AutopilotClient

    return adapt_legacy_autopilot_client(
        AutopilotClient(socket_path=socket_path, timeout=timeout),
    )


def build_koruide_client(
    *,
    socket_path: Path | None = None,
    timeout: float = 5.0,
) -> IDEControlClient:
    """Construct :class:`IDEControlClient` backed by the `koruide` package client."""

    from koruide.client import build_client as build_koruide_package_client

    return build_koruide_package_client(socket_path=socket_path, timeout=timeout)


def build_ide_client(
    *,
    socket_path: Path | None = None,
    timeout: float = 5.0,
    backend: str | None = None,
) -> IDEControlClient:
    """Construct an IDE client for the selected backend.

    Selection order:

    1. Explicit ``backend`` argument.
    2. ``KORU_IDE_BACKEND`` environment variable.
    3. Fallback to ``legacy``.
    """

    choice = (backend or os.environ.get("KORU_IDE_BACKEND", "legacy")).strip().lower()
    if choice == "koruide":
        return build_koruide_client(socket_path=socket_path, timeout=timeout)
    return build_legacy_ide_client(socket_path=socket_path, timeout=timeout)


__all__ = [
    "IDEControlClient",
    "LegacyAutopilotClientAdapter",
    "adapt_legacy_autopilot_client",
    "build_legacy_ide_client",
    "build_koruide_client",
    "build_ide_client",
]
