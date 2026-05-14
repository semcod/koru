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
from collections import deque
from dataclasses import dataclass
from datetime import UTC, datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib.metadata import PackageNotFoundError, version
from typing import Any

DEFAULT_HOST = "127.0.0.1"
# When no CLI port and no KORU_LOCAL_SERVICE_PORT, avoid clashing with ``koru serve`` (8765).
DEFAULT_PORT = 18766
DEFAULT_MAX_EVENTS = 256
MAX_BODY_BYTES = 65_536


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


def default_local_service_config() -> LocalServiceConfig:
    """Defaults from env ``KORU_LOCAL_SERVICE_*`` (see docs/local-service.md)."""
    host = os.environ.get("KORU_LOCAL_SERVICE_HOST", DEFAULT_HOST).strip() or DEFAULT_HOST
    port = _env_int("KORU_LOCAL_SERVICE_PORT", DEFAULT_PORT)
    max_ev = _env_int("KORU_LOCAL_SERVICE_MAX_EVENTS", DEFAULT_MAX_EVENTS)
    return LocalServiceConfig(host=host, port=port, max_events=max(1, min(max_ev, 10_000)))


def _build_handler(buffer: _EventBuffer, koru_version: str) -> type[BaseHTTPRequestHandler]:
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
            if path == "/health":
                self._send_json({"ok": True, "version": koru_version})
                return
            if path == "/events":
                lines = []
                for rec in buffer.snapshot():
                    lines.append(json.dumps(rec, sort_keys=True))
                nd = ("\n".join(lines) + ("\n" if lines else "")).encode("utf-8")
                self._send(200, nd, "application/x-ndjson; charset=utf-8")
                return
            self._send_json({"error": "not found"}, 404)

        def do_POST(self) -> None:  # noqa: N802
            path = self.path.split("?", 1)[0]
            if path not in ("/event", "/enqueue"):
                self._send_json({"error": "not found"}, 404)
                return
            try:
                length = int(self.headers.get("Content-Length", "0") or "0")
            except ValueError:
                self._send_json({"error": "invalid Content-Length"}, status=400)
                return
            if length > MAX_BODY_BYTES:
                self._send_json({"error": "body too large"}, status=413)
                return
            if length <= 0:
                self._send_json({"error": "expected JSON object body"}, status=400)
                return
            raw = self.rfile.read(length)
            try:
                data = json.loads(raw.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                self._send_json({"error": f"invalid JSON: {exc}"}, status=400)
                return
            if not isinstance(data, dict):
                self._send_json({"error": "JSON body must be an object"}, status=400)
                return
            eid = uuid.uuid4().hex
            record = {
                "id": eid,
                "received_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
                "payload": data,
            }
            buffer.append(record)
            self._send_json({"id": eid})

    return _Handler


def build_local_service_server(
    config: LocalServiceConfig,
) -> tuple[ThreadingHTTPServer, _EventBuffer]:
    buf = _EventBuffer(maxlen=config.max_events)
    handler = _build_handler(buf, _koru_version())
    return ThreadingHTTPServer((config.host, config.port), handler), buf


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
    print("koru local-serve: POST /event or /enqueue, GET /health, GET /events (NDJSON)")
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
