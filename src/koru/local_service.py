"""Small localhost-only HTTP surface for structured work/events.

Complements the autopilot Unix socket: that channel is for IDE ↔ koru RPC;
this server is for HTTP clients on the same host (curl, scripts, future
bridges). Stdlib-only (``ThreadingHTTPServer``).
"""

from __future__ import annotations

import json
import os
import re
import sys
import threading
import uuid
from collections import deque
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib.metadata import PackageNotFoundError, version
from typing import Any

DEFAULT_HOST = "127.0.0.1"
# When no CLI port and no KORU_LOCAL_SERVICE_PORT, avoid clashing with ``koru serve`` (8765).
DEFAULT_PORT = 18766
DEFAULT_MAX_EVENTS = 256
MAX_BODY_BYTES = 65_536
DEFAULT_LEASE_SECONDS = 300


def _utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _koru_version() -> str:
    try:
        return version("koru")
    except PackageNotFoundError:
        return "0.0.0"


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


@dataclass
class LocalServiceConfig:
    """Configuration for ``koru local-serve``."""

    host: str = DEFAULT_HOST
    port: int = DEFAULT_PORT
    max_events: int = DEFAULT_MAX_EVENTS


class _EventBuffer:
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


def _normalize_capabilities(raw: Any) -> list[str]:
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
            return _normalize_capabilities(payload.get(key))
    return []


class _ActionQueue:
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
        now = _utc_now()
        lease_seconds = max(1, min(int(lease_seconds), 86_400))
        expires_at = (datetime.now(UTC) + timedelta(seconds=lease_seconds)).isoformat().replace(
            "+00:00",
            "Z",
        )
        available = set(capabilities)
        wanted_types = set(_normalize_capabilities(action_types))
        with self._lock:
            for item in self._items:
                if item.get("status") != "queued":
                    continue
                if wanted_types and str(item.get("type") or "") not in wanted_types:
                    continue
                required = set(_normalize_capabilities(item.get("required_capabilities")))
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
        completed_at = _utc_now()
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


class _WorkerRegistry:
    """Registry and lifecycle policy for versioned koru workers."""

    _healthy = {"ok", "healthy", "ready"}

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._workers: dict[str, dict[str, Any]] = {}
        self._active_worker_id: str | None = None

    def register(self, payload: dict[str, Any]) -> dict[str, Any]:
        now = _utc_now()
        version_value = str(payload.get("version") or _koru_version())
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
                "capabilities": _normalize_capabilities(
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
                worker["capabilities"] = _normalize_capabilities(payload.get("capabilities"))
            if "conflict" in payload:
                worker["conflict"] = bool(payload.get("conflict"))
            if isinstance(payload.get("metadata"), dict):
                worker["metadata"] = payload.get("metadata")
            worker["last_seen_at"] = _utc_now()
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


class _ServiceState:
    def __init__(self, max_events: int) -> None:
        self.events = _EventBuffer(maxlen=max_events)
        self.queue = _ActionQueue(maxlen=max_events)
        self.workers = _WorkerRegistry()


def _read_bounded_json_object(
    handler: BaseHTTPRequestHandler,
    *,
    max_bytes: int = MAX_BODY_BYTES,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None, int]:
    """Parse POST JSON body; return ``(data, error_payload, http_status)``."""
    try:
        length = int(handler.headers.get("Content-Length", "0") or "0")
    except ValueError:
        return None, {"error": "invalid Content-Length"}, 400
    if length > max_bytes:
        return None, {"error": "body too large"}, 413
    if length <= 0:
        return None, {"error": "expected JSON object body"}, 400
    raw = handler.rfile.read(length)
    try:
        data = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        return None, {"error": f"invalid JSON: {exc}"}, 400
    if not isinstance(data, dict):
        return None, {"error": "JSON body must be an object"}, 400
    return data, None, 200


def default_local_service_config() -> LocalServiceConfig:
    """Defaults from env ``KORU_LOCAL_SERVICE_*`` (see docs/local-service.md)."""
    host = os.environ.get("KORU_LOCAL_SERVICE_HOST", DEFAULT_HOST).strip() or DEFAULT_HOST
    port = _env_int("KORU_LOCAL_SERVICE_PORT", DEFAULT_PORT)
    max_ev = _env_int("KORU_LOCAL_SERVICE_MAX_EVENTS", DEFAULT_MAX_EVENTS)
    return LocalServiceConfig(host=host, port=port, max_events=max(1, min(max_ev, 10_000)))


def _build_handler(state: _ServiceState, koru_version: str) -> type[BaseHTTPRequestHandler]:
    class _Handler(BaseHTTPRequestHandler):
        def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
            return

        def _send(
            self,
            status: int,
            body: bytes,
            content_type: str = "application/json; charset=utf-8",
        ) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            try:
                self.wfile.write(body)
            except (BrokenPipeError, ConnectionResetError):
                return

        def _send_json(self, payload: Any, status: int = 200) -> None:
            raw = json.dumps(payload, sort_keys=True).encode("utf-8")
            self._send(status, raw)

        def _append_event(self, payload: dict[str, Any]) -> tuple[str, str]:
            eid = uuid.uuid4().hex
            received_at = _utc_now()
            state.events.append(
                {
                    "id": eid,
                    "received_at": received_at,
                    "payload": payload,
                },
            )
            return eid, received_at

        def do_GET(self) -> None:  # noqa: N802
            path = self.path.split("?", 1)[0]
            if path == "/health":
                queue_snapshot = state.queue.snapshot()
                workers_snapshot = state.workers.snapshot()
                self._send_json(
                    {
                        "ok": True,
                        "version": koru_version,
                        "service": "koru-local-manager",
                        "active_worker_id": workers_snapshot["active_worker_id"],
                        "queue_counts": queue_snapshot["counts"],
                    },
                )
                return
            if path == "/events":
                lines = []
                for rec in state.events.snapshot():
                    lines.append(json.dumps(rec, sort_keys=True))
                nd = ("\n".join(lines) + ("\n" if lines else "")).encode("utf-8")
                self._send(200, nd, "application/x-ndjson; charset=utf-8")
                return
            if path == "/queue":
                self._send_json(state.queue.snapshot())
                return
            if path == "/workers":
                self._send_json(state.workers.snapshot())
                return
            if path == "/state":
                self._send_json(
                    {
                        "queue": state.queue.snapshot(),
                        "workers": state.workers.snapshot(),
                    },
                )
                return
            self._send_json({"error": "not found"}, 404)

        def do_POST(self) -> None:  # noqa: N802
            path = self.path.split("?", 1)[0]
            if path not in (
                "/event",
                "/enqueue",
                "/queue/claim",
                "/queue/complete",
                "/workers/register",
                "/workers/heartbeat",
                "/lifecycle/decision",
            ):
                self._send_json({"error": "not found"}, 404)
                return
            data, err, status = _read_bounded_json_object(self)
            if err is not None:
                self._send_json(err, status=status)
                return
            if path == "/event":
                eid, _received_at = self._append_event(data)
                self._send_json({"id": eid})
                return
            if path == "/enqueue":
                eid, received_at = self._append_event(data)
                item = state.queue.enqueue(eid, data, received_at)
                self._send_json({"id": eid, "status": item["status"], "item": item})
                return
            if path == "/queue/claim":
                worker_id = str(data.get("worker_id") or data.get("id") or "").strip()
                if not worker_id:
                    self._send_json({"error": "worker_id is required"}, 400)
                    return
                try:
                    lease_seconds = int(data.get("lease_seconds") or DEFAULT_LEASE_SECONDS)
                except (TypeError, ValueError):
                    self._send_json({"error": "lease_seconds must be an integer"}, 400)
                    return
                item = state.queue.claim(
                    worker_id=worker_id,
                    capabilities=_normalize_capabilities(data.get("capabilities")),
                    action_types=_normalize_capabilities(
                        data.get("action_types", data.get("types")),
                    ),
                    lease_seconds=lease_seconds,
                )
                if item is None:
                    self._send_json({"status": "idle", "item": None})
                    return
                self._append_event(
                    {"type": "queue.claimed", "action_id": item["id"], "worker_id": worker_id},
                )
                self._send_json({"status": "leased", "item": item})
                return
            if path == "/queue/complete":
                action_id = str(data.get("action_id") or data.get("id") or "").strip()
                if not action_id:
                    self._send_json({"error": "action_id is required"}, 400)
                    return
                final_status = str(data.get("status") or "completed")
                if final_status not in {"completed", "failed", "canceled"}:
                    self._send_json({"error": "status must be completed, failed, or canceled"}, 400)
                    return
                item = state.queue.complete(
                    action_id=action_id,
                    worker_id=str(data.get("worker_id") or "") or None,
                    status=final_status,
                    result=data.get("result") if isinstance(data.get("result"), dict) else None,
                )
                if item is None:
                    self._send_json({"error": "action not found"}, 404)
                    return
                self._append_event(
                    {"type": "queue.completed", "action_id": action_id, "status": final_status},
                )
                self._send_json({"status": final_status, "item": item})
                return
            if path == "/workers/register":
                reply = state.workers.register(data)
                self._append_event(
                    {
                        "type": "worker.registered",
                        "worker_id": reply["worker"]["worker_id"],
                        "version": reply["worker"]["version"],
                        "decision": reply["decision"],
                    },
                )
                self._send_json(reply)
                return
            reply = state.workers.heartbeat(data)
            self._append_event(
                {
                    "type": "worker.heartbeat",
                    "worker_id": reply["worker"]["worker_id"],
                    "version": reply["worker"]["version"],
                    "decision": reply["decision"],
                },
            )
            self._send_json(reply)

    return _Handler


def build_local_service_server(
    config: LocalServiceConfig,
) -> tuple[ThreadingHTTPServer, _EventBuffer]:
    state = _ServiceState(max_events=config.max_events)
    handler = _build_handler(state, _koru_version())
    return ThreadingHTTPServer((config.host, config.port), handler), state.events


def run_local_service(config: LocalServiceConfig) -> int:
    """Bind and block until Ctrl-C; returns 0 on clean shutdown."""
    try:
        server, _buf = build_local_service_server(config)
    except OSError as exc:
        print(
            f"koru local-serve: cannot bind {config.host}:{config.port} — {exc}",
            file=sys.stderr,
        )
        return 1
    actual = int(server.server_address[1])
    config.port = actual
    url = f"http://{config.host}:{config.port}/"
    print(f"koru local-serve: listening on {url}")
    print(
        "koru local-serve: POST /event, /enqueue, /queue/claim, /queue/complete, "
        "/workers/register, /workers/heartbeat",
    )
    print("koru local-serve: GET /health, /events (NDJSON), /queue, /workers, /state")
    print("koru local-serve: Ctrl-C to stop")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print()
        print("koru local-serve: stopping")
    finally:
        server.shutdown()
        server.server_close()
    return 0


def start_local_service_background(
    config: LocalServiceConfig,
) -> tuple[ThreadingHTTPServer, threading.Thread, int]:
    """Run ``serve_forever`` on a daemon thread; caller must ``shutdown()`` + ``server_close()``."""
    server, _buf = build_local_service_server(config)
    actual = int(server.server_address[1])
    config.port = actual
    thread = threading.Thread(
        target=server.serve_forever,
        name="koru-local-serve-bg",
        daemon=True,
    )
    thread.start()
    return server, thread, actual
