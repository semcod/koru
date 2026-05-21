"""In-process state for the local koru manager service."""

from __future__ import annotations

import re
import threading
import uuid
from collections import deque
from datetime import UTC, datetime, timedelta
from importlib.metadata import PackageNotFoundError, version
from typing import Any

DEFAULT_LEASE_SECONDS = 300


def utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def koru_version() -> str:
    try:
        return version("koru")
    except PackageNotFoundError:
        return "0.0.0"


def normalize_capabilities(raw: Any) -> list[str]:
    if raw is None:
        return []
    if isinstance(raw, str):
        items = [raw]
    elif isinstance(raw, (list, tuple, set)):
        items = list(raw)
    else:
        items = [raw]
    return sorted({str(item).strip() for item in items if str(item).strip()})


def _action_type(payload: dict[str, Any]) -> str:
    for key in ("type", "action", "kind"):
        value = payload.get(key)
        if value:
            return str(value)
    return "generic"


def _required_capabilities(payload: dict[str, Any]) -> list[str]:
    for key in ("requires", "required_capabilities", "capability"):
        if key in payload:
            return normalize_capabilities(payload.get(key))
    return []


class EventBuffer:
    """Thread-safe ring of recent event records (oldest dropped at maxlen)."""

    def __init__(self, maxlen: int) -> None:
        self._lock = threading.Lock()
        self._items: deque[dict[str, Any]] = deque(maxlen=maxlen)

    def append(self, record: dict[str, Any]) -> None:
        with self._lock:
            self._items.append(record)

    def snapshot(self) -> list[dict[str, Any]]:
        with self._lock:
            return list(self._items)


class ActionQueue:
    """Single in-process queue for local koru actions with simple leases."""

    def __init__(self, maxlen: int) -> None:
        self._lock = threading.Lock()
        self._items: deque[dict[str, Any]] = deque(maxlen=maxlen)

    def enqueue(self, action_id: str, payload: dict[str, Any], received_at: str) -> dict[str, Any]:
        item = {
            "id": action_id,
            "type": _action_type(payload),
            "status": "queued",
            "received_at": received_at,
            "payload": payload,
            "required_capabilities": _required_capabilities(payload),
        }
        with self._lock:
            self._items.append(item)
            return dict(item)

    def claim(
        self,
        *,
        worker_id: str,
        capabilities: list[str],
        action_types: list[str] | None = None,
        lease_seconds: int = DEFAULT_LEASE_SECONDS,
    ) -> dict[str, Any] | None:
        now = utc_now()
        lease_seconds = max(1, min(int(lease_seconds), 86_400))
        expires_at = (datetime.now(UTC) + timedelta(seconds=lease_seconds)).isoformat().replace(
            "+00:00",
            "Z",
        )
        available = set(capabilities)
        wanted_types = set(normalize_capabilities(action_types))
        with self._lock:
            for item in self._items:
                if item.get("status") != "queued":
                    continue
                if wanted_types and str(item.get("type") or "") not in wanted_types:
                    continue
                required = set(normalize_capabilities(item.get("required_capabilities")))
                if required and not required.issubset(available):
                    continue
                item.update(
                    {
                        "status": "leased",
                        "claimed_by": worker_id,
                        "claimed_at": now,
                        "lease_expires_at": expires_at,
                    },
                )
                return dict(item)
        return None

    def complete(
        self,
        *,
        action_id: str,
        worker_id: str | None,
        status: str,
        result: dict[str, Any] | None,
    ) -> dict[str, Any] | None:
        completed_at = utc_now()
        with self._lock:
            for item in self._items:
                if item.get("id") != action_id:
                    continue
                item.update(
                    {
                        "status": status,
                        "completed_by": worker_id,
                        "completed_at": completed_at,
                        "result": result or {},
                    },
                )
                return dict(item)
        return None

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            items = [dict(item) for item in self._items]
        counts: dict[str, int] = {}
        for item in items:
            status = str(item.get("status") or "unknown")
            counts[status] = counts.get(status, 0) + 1
        return {"items": items, "counts": counts}


def _version_key(raw: Any) -> tuple[int, ...]:
    numbers = [int(part) for part in re.findall(r"\d+", str(raw or ""))]
    return tuple(numbers) or (0,)


class WorkerRegistry:
    """Registry and lifecycle policy for versioned koru workers."""

    _healthy = {"ok", "healthy", "ready"}

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._workers: dict[str, dict[str, Any]] = {}
        self._active_worker_id: str | None = None

    def register(self, payload: dict[str, Any]) -> dict[str, Any]:
        now = utc_now()
        version_value = str(payload.get("version") or koru_version())
        worker_id = str(payload.get("worker_id") or payload.get("id") or uuid.uuid4().hex)
        with self._lock:
            existing = self._workers.get(worker_id, {})
            worker = {
                "worker_id": worker_id,
                "kind": str(payload.get("kind") or existing.get("kind") or "koru-worker"),
                "version": version_value,
                "path": str(payload.get("path") or existing.get("path") or ""),
                "project": str(payload.get("project") or existing.get("project") or ""),
                "pid": payload.get("pid", existing.get("pid")),
                "capabilities": normalize_capabilities(
                    payload.get("capabilities", existing.get("capabilities")),
                ),
                "metadata": payload.get("metadata")
                if isinstance(payload.get("metadata"), dict)
                else existing.get("metadata", {}),
                "health": str(payload.get("health") or existing.get("health") or "ok"),
                "conflict": bool(payload.get("conflict", existing.get("conflict", False))),
                "registered_at": str(existing.get("registered_at") or now),
                "last_seen_at": now,
            }
            self._workers[worker_id] = worker
            self._reconcile_locked()
            return self._reply_locked(worker_id)

    def heartbeat(self, payload: dict[str, Any]) -> dict[str, Any]:
        worker_id = str(payload.get("worker_id") or payload.get("id") or "")
        if not worker_id:
            return self.register(payload)
        with self._lock:
            worker = self._workers.get(worker_id)
        if worker is None:
            payload = dict(payload)
            payload["worker_id"] = worker_id
            return self.register(payload)
        with self._lock:
            if "health" in payload:
                worker["health"] = str(payload.get("health") or "unknown")
            if "pid" in payload:
                worker["pid"] = payload.get("pid")
            if "capabilities" in payload:
                worker["capabilities"] = normalize_capabilities(payload.get("capabilities"))
            if "conflict" in payload:
                worker["conflict"] = bool(payload.get("conflict"))
            if isinstance(payload.get("metadata"), dict):
                worker["metadata"] = payload.get("metadata")
            worker["last_seen_at"] = utc_now()
            self._reconcile_locked()
            return self._reply_locked(worker_id)

    def _reconcile_locked(self) -> None:
        candidates = [
            worker
            for worker in self._workers.values()
            if str(worker.get("health") or "").lower() in self._healthy
        ]
        if candidates:
            active = max(
                candidates,
                key=lambda worker: (
                    _version_key(worker.get("version")),
                    worker.get("registered_at"),
                ),
            )
            self._active_worker_id = str(active["worker_id"])
        else:
            self._active_worker_id = None

        for worker in self._workers.values():
            health = str(worker.get("health") or "").lower()
            if health not in self._healthy:
                worker["state"] = "quarantine"
                worker["decision"] = "quarantine"
            elif worker.get("worker_id") == self._active_worker_id:
                worker["state"] = "active"
                worker["decision"] = "continue"
            else:
                worker["state"] = "draining"
                worker["decision"] = "drain-and-exit"

    def _reply_locked(self, worker_id: str) -> dict[str, Any]:
        worker = dict(self._workers[worker_id])
        return {
            "worker": worker,
            "decision": {
                "worker_id": worker_id,
                "action": worker.get("decision"),
                "state": worker.get("state"),
                "active_worker_id": self._active_worker_id,
            },
        }

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            workers = [dict(worker) for worker in self._workers.values()]
            return {"active_worker_id": self._active_worker_id, "workers": workers}


class ServiceState:
    def __init__(self, max_events: int) -> None:
        self.events = EventBuffer(maxlen=max_events)
        self.queue = ActionQueue(maxlen=max_events)
        self.workers = WorkerRegistry()


__all__ = [
    "DEFAULT_LEASE_SECONDS",
    "ActionQueue",
    "EventBuffer",
    "ServiceState",
    "WorkerRegistry",
    "koru_version",
    "normalize_capabilities",
    "utc_now",
]