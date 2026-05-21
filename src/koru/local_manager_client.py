"""Best-effort client for the local koru manager service."""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any

DEFAULT_LOCAL_MANAGER_TIMEOUT = 0.4
LIFECYCLE_STOP_ACTIONS = frozenset({"drain-and-exit", "quarantine", "shutdown", "replace"})


def _truthy(raw: str | None) -> bool:
    return (raw or "").strip().lower() in {"1", "true", "yes", "on"}


def _koru_version() -> str:
    try:
        return version("koru")
    except PackageNotFoundError:
        return "0.0.0"


def default_local_manager_url() -> str | None:
    """Return the configured local manager URL, or ``None`` when disabled.

    The client is intentionally opt-in. Plain ``koru --queue`` must keep working
    without a local manager process and without paying a connection timeout on
    every test or short CLI invocation.
    """
    explicit = (
        os.environ.get("KORU_LOCAL_MANAGER_URL")
        or os.environ.get("KORU_LOCAL_SERVICE_URL")
        or ""
    ).strip()
    if explicit:
        return explicit.rstrip("/")
    if not _truthy(os.environ.get("KORU_LOCAL_MANAGER_ENABLED")):
        return None
    host = os.environ.get("KORU_LOCAL_SERVICE_HOST", "127.0.0.1").strip() or "127.0.0.1"
    port = os.environ.get("KORU_LOCAL_SERVICE_PORT", "18766").strip() or "18766"
    return f"http://{host}:{port}"


def lifecycle_decision_action(reply: dict[str, Any] | None) -> str:
    if not isinstance(reply, dict):
        return "continue"
    decision = reply.get("decision")
    if not isinstance(decision, dict):
        return "continue"
    return str(decision.get("action") or "continue")


def lifecycle_should_stop(reply: dict[str, Any] | None) -> bool:
    return lifecycle_decision_action(reply) in LIFECYCLE_STOP_ACTIONS


@dataclass
class LocalManagerClient:
    """Tiny JSON-over-HTTP client for ``koru local-serve``."""

    url: str | None = None
    timeout: float = DEFAULT_LOCAL_MANAGER_TIMEOUT

    @classmethod
    def from_env(cls) -> LocalManagerClient:
        return cls(default_local_manager_url())

    @property
    def enabled(self) -> bool:
        return bool(self.url)

    def post(self, path: str, payload: dict[str, Any]) -> dict[str, Any] | None:
        if not self.url:
            return None
        request = urllib.request.Request(
            f"{self.url}{path}",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                data = json.loads(response.read().decode("utf-8"))
        except (OSError, urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError):
            return None
        return data if isinstance(data, dict) else None

    def register_worker(
        self,
        *,
        worker_id: str,
        worker_kind: str,
        capabilities: list[str],
        project: Path | None = None,
        health: str = "ok",
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        payload = {
            "worker_id": worker_id,
            "kind": worker_kind,
            "version": _koru_version(),
            "capabilities": capabilities,
            "health": health,
            "pid": os.getpid(),
            "path": sys.executable,
            "project": str(project) if project is not None else None,
            "metadata": metadata or {},
        }
        return self.post("/workers/register", payload)

    def heartbeat_worker(
        self,
        *,
        worker_id: str,
        capabilities: list[str],
        health: str = "ok",
        conflict: bool = False,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        return self.post(
            "/workers/heartbeat",
            {
                "worker_id": worker_id,
                "capabilities": capabilities,
                "health": health,
                "conflict": conflict,
                "metadata": metadata or {},
            },
        )

    def claim_action(
        self,
        *,
        worker_id: str,
        capabilities: list[str],
        action_types: list[str] | None = None,
        lease_seconds: int = 300,
    ) -> dict[str, Any] | None:
        return self.post(
            "/queue/claim",
            {
                "worker_id": worker_id,
                "capabilities": capabilities,
                "action_types": action_types or [],
                "lease_seconds": lease_seconds,
            },
        )

    def complete_action(
        self,
        *,
        action_id: str,
        worker_id: str,
        status: str,
        result: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        return self.post(
            "/queue/complete",
            {
                "action_id": action_id,
                "worker_id": worker_id,
                "status": status,
                "result": result or {},
            },
        )


@dataclass
class LocalManagerSession:
    """Small lifecycle session for one CLI worker invocation."""

    client: LocalManagerClient
    worker_id: str
    worker_kind: str
    capabilities: list[str]
    action_types: list[str] = field(default_factory=list)
    action_id: str | None = None
    last_reply: dict[str, Any] | None = None

    @property
    def enabled(self) -> bool:
        return self.client.enabled

    def start(
        self,
        *,
        project: Path | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        self.last_reply = self.client.register_worker(
            worker_id=self.worker_id,
            worker_kind=self.worker_kind,
            capabilities=self.capabilities,
            project=project,
            metadata=metadata,
        )
        if lifecycle_should_stop(self.last_reply):
            return self.last_reply
        claim = self.client.claim_action(
            worker_id=self.worker_id,
            capabilities=self.capabilities,
            action_types=self.action_types,
        )
        item = claim.get("item") if isinstance(claim, dict) else None
        if isinstance(item, dict):
            self.action_id = str(item.get("id") or "") or None
        return self.last_reply

    def heartbeat(
        self,
        *,
        health: str = "ok",
        conflict: bool = False,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        self.last_reply = self.client.heartbeat_worker(
            worker_id=self.worker_id,
            capabilities=self.capabilities,
            health=health,
            conflict=conflict,
            metadata=metadata,
        )
        return self.last_reply

    def should_stop(self) -> bool:
        return lifecycle_should_stop(self.last_reply)

    def complete(self, *, status: str, result: dict[str, Any] | None = None) -> None:
        if not self.action_id:
            return
        self.client.complete_action(
            action_id=self.action_id,
            worker_id=self.worker_id,
            status=status,
            result=result,
        )


__all__ = [
    "LocalManagerClient",
    "LocalManagerSession",
    "default_local_manager_url",
    "lifecycle_decision_action",
    "lifecycle_should_stop",
]