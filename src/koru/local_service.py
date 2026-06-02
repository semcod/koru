"""Small localhost-only HTTP surface for structured work/events.

Complements the autopilot Unix socket: that channel is for IDE ↔ koru RPC;
this server is for HTTP clients on the same host (curl, scripts, future
bridges). Stdlib-only (``ThreadingHTTPServer``).
"""

from __future__ import annotations

import json
import os
import sys
import threading
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from koru.bounded_contexts.local_manager import LocalManagerCommandService, LocalManagerQueryService
from koru.bounded_contexts.local_manager.commands import (
    ClaimActionCommand,
    CompleteActionCommand,
    EnqueueActionCommand,
    HeartbeatWorkerCommand,
    RegisterWorkerCommand,
)
from koru.bounded_contexts.local_manager.queries import (
    HealthSnapshotQuery,
    QueueSnapshotQuery,
    StateSnapshotQuery,
    WorkersSnapshotQuery,
)
from koru.local_manager_state import DEFAULT_LEASE_SECONDS
from koru.local_manager_state import EventBuffer as _EventBuffer
from koru.local_manager_state import ServiceState as _ServiceState
from koru.local_manager_state import koru_version as _koru_version
from koru.local_manager_state import normalize_capabilities as _normalize_capabilities
from koru.local_manager_state import utc_now as _utc_now

DEFAULT_HOST = "127.0.0.1"
# When no CLI port and no KORU_LOCAL_SERVICE_PORT, avoid clashing with ``koru serve`` (8765).
DEFAULT_PORT = 18766
DEFAULT_MAX_EVENTS = 256
MAX_BODY_BYTES = 65_536


from koru.env_flags import env_int as _env_int


@dataclass
class LocalServiceConfig:
    """Configuration for ``koru local-serve``."""

    host: str = DEFAULT_HOST
    port: int = DEFAULT_PORT
    max_events: int = DEFAULT_MAX_EVENTS


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


def _append_event(state: _ServiceState, payload: dict[str, Any]) -> tuple[str, str]:
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


def _handle_get(
    handler: Any,
    *,
    path: str,
    state: _ServiceState,
    query_service: LocalManagerQueryService,
    koru_version: str,
) -> None:
    if path == "/health":
        handler._send_json(query_service.health(HealthSnapshotQuery(koru_version=koru_version)))
        return
    if path == "/events":
        lines = [json.dumps(rec, sort_keys=True) for rec in state.events.snapshot()]
        nd = ("\n".join(lines) + ("\n" if lines else "")).encode("utf-8")
        handler._send(200, nd, "application/x-ndjson; charset=utf-8")
        return
    if path == "/queue":
        handler._send_json(query_service.queue_snapshot(QueueSnapshotQuery()))
        return
    if path == "/workers":
        handler._send_json(query_service.workers_snapshot(WorkersSnapshotQuery()))
        return
    if path == "/state":
        handler._send_json(query_service.state_snapshot(StateSnapshotQuery()))
        return
    handler._send_json({"error": "not found"}, 404)


def _post_event(
    handler: Any,
    data: dict[str, Any],
    state: _ServiceState,
    _command_service: LocalManagerCommandService,
) -> None:
    eid, _received_at = _append_event(state, data)
    handler._send_json({"id": eid})


def _post_enqueue(
    handler: Any,
    data: dict[str, Any],
    state: _ServiceState,
    command_service: LocalManagerCommandService,
) -> None:
    eid, received_at = _append_event(state, data)
    item = command_service.enqueue(
        EnqueueActionCommand(action_id=eid, payload=data, received_at=received_at),
    )
    handler._send_json({"id": eid, "status": item["status"], "item": item})


def _post_queue_claim(
    handler: Any,
    data: dict[str, Any],
    state: _ServiceState,
    command_service: LocalManagerCommandService,
) -> None:
    worker_id = str(data.get("worker_id") or data.get("id") or "").strip()
    if not worker_id:
        handler._send_json({"error": "worker_id is required"}, 400)
        return
    try:
        lease_seconds = int(data.get("lease_seconds") or DEFAULT_LEASE_SECONDS)
    except (TypeError, ValueError):
        handler._send_json({"error": "lease_seconds must be an integer"}, 400)
        return
    item = command_service.claim(
        ClaimActionCommand(
            worker_id=worker_id,
            capabilities=_normalize_capabilities(data.get("capabilities")),
            action_types=_normalize_capabilities(data.get("action_types", data.get("types"))),
            lease_seconds=lease_seconds,
        ),
    )
    if item is None:
        handler._send_json({"status": "idle", "item": None})
        return
    _append_event(state, {"type": "queue.claimed", "action_id": item["id"], "worker_id": worker_id})
    handler._send_json({"status": "leased", "item": item})


def _post_queue_complete(
    handler: Any,
    data: dict[str, Any],
    state: _ServiceState,
    command_service: LocalManagerCommandService,
) -> None:
    action_id = str(data.get("action_id") or data.get("id") or "").strip()
    if not action_id:
        handler._send_json({"error": "action_id is required"}, 400)
        return
    final_status = str(data.get("status") or "completed")
    if final_status not in {"completed", "failed", "canceled"}:
        handler._send_json({"error": "status must be completed, failed, or canceled"}, 400)
        return
    item = command_service.complete(
        CompleteActionCommand(
            action_id=action_id,
            worker_id=str(data.get("worker_id") or "") or None,
            status=final_status,
            result=data.get("result") if isinstance(data.get("result"), dict) else None,
        ),
    )
    if item is None:
        handler._send_json({"error": "action not found"}, 404)
        return
    _append_event(
        state,
        {"type": "queue.completed", "action_id": action_id, "status": final_status},
    )
    handler._send_json({"status": final_status, "item": item})


def _post_workers_register(
    handler: Any,
    data: dict[str, Any],
    state: _ServiceState,
    command_service: LocalManagerCommandService,
) -> None:
    reply = command_service.register_worker(RegisterWorkerCommand(payload=data))
    _append_event(
        state,
        {
            "type": "worker.registered",
            "worker_id": reply["worker"]["worker_id"],
            "version": reply["worker"]["version"],
            "decision": reply["decision"],
        },
    )
    handler._send_json(reply)


def _post_worker_heartbeat(
    handler: Any,
    data: dict[str, Any],
    state: _ServiceState,
    command_service: LocalManagerCommandService,
) -> None:
    reply = command_service.heartbeat_worker(HeartbeatWorkerCommand(payload=data))
    _append_event(
        state,
        {
            "type": "worker.heartbeat",
            "worker_id": reply["worker"]["worker_id"],
            "version": reply["worker"]["version"],
            "decision": reply["decision"],
        },
    )
    handler._send_json(reply)


_PostHandler = Callable[[Any, dict[str, Any], _ServiceState, LocalManagerCommandService], None]
_POST_HANDLERS: dict[str, _PostHandler] = {
    "/event": _post_event,
    "/enqueue": _post_enqueue,
    "/queue/claim": _post_queue_claim,
    "/queue/complete": _post_queue_complete,
    "/workers/register": _post_workers_register,
    "/workers/heartbeat": _post_worker_heartbeat,
    "/lifecycle/decision": _post_worker_heartbeat,
}


def _build_handler(state: _ServiceState, koru_version: str) -> type[BaseHTTPRequestHandler]:
    command_service = LocalManagerCommandService(state)
    query_service = LocalManagerQueryService(state)

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

        def do_GET(self) -> None:  # noqa: N802
            path = self.path.split("?", 1)[0]
            _handle_get(
                self,
                path=path,
                state=state,
                query_service=query_service,
                koru_version=koru_version,
            )

        def do_POST(self) -> None:  # noqa: N802
            path = self.path.split("?", 1)[0]
            post_handler = _POST_HANDLERS.get(path)
            if post_handler is None:
                self._send_json({"error": "not found"}, 404)
                return
            data, err, status = _read_bounded_json_object(self)
            if err is not None:
                self._send_json(err, status=status)
                return
            post_handler(self, data, state, command_service)

    return _Handler


def build_local_service_server(
    config: LocalServiceConfig,
) -> tuple[ThreadingHTTPServer, _EventBuffer]:
    state = _ServiceState(max_events=config.max_events)
    handler = _build_handler(state, _koru_version())
    return ThreadingHTTPServer((config.host, config.port), handler), state.events


def _bound_port(server: ThreadingHTTPServer) -> int:
    """Return the OS-assigned port from a bound server socket."""
    return int(server.server_address[1])


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
    actual = _bound_port(server)
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
    actual = _bound_port(server)
    config.port = actual
    thread = threading.Thread(
        target=server.serve_forever,
        name="koru-local-serve-bg",
        daemon=True,
    )
    thread.start()
    return server, thread, actual
