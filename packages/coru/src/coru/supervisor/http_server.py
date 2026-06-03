"""HTTP control plane for the coru supervisor."""

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Callable
from urllib.parse import unquote, urlparse

from coru.supervisor.models import LaneRecord, SupervisorRegistry
from coru.supervisor.registry import (
    load_registry,
    register_lane,
    remove_lane,
    save_registry,
    set_active_lane,
)
from coru.supervisor.service import SupervisorService


def _json_response(handler: BaseHTTPRequestHandler, status: int, payload: dict[str, Any]) -> None:
    body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def _read_json_body(handler: BaseHTTPRequestHandler) -> dict[str, Any]:
    length = int(handler.headers.get("Content-Length") or "0")
    if length <= 0:
        return {}
    raw = handler.rfile.read(length)
    if not raw:
        return {}
    payload = json.loads(raw.decode("utf-8"))
    return payload if isinstance(payload, dict) else {}


def _lanes_payload(registry: SupervisorRegistry) -> dict[str, Any]:
    return {
        "active_lane": registry.active_lane,
        "lanes": [lane.to_dict() for lane in registry.lanes.values()],
    }


def make_handler(service: SupervisorService) -> type[BaseHTTPRequestHandler]:
    class SupervisorHTTPHandler(BaseHTTPRequestHandler):
        server_version = "coru-supervisor/0.1"

        def log_message(self, format: str, *args: Any) -> None:  # noqa: A003
            if service.verbose:
                super().log_message(format, *args)

        def do_GET(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            path = parsed.path.rstrip("/") or "/"
            if path == "/api/health":
                _json_response(
                    self,
                    200,
                    {
                        "ok": True,
                        "pid": service.pid,
                        "url": service.url,
                        "active_lane": load_registry(path=service.registry_path).active_lane,
                    },
                )
                return
            if path == "/api/lanes":
                registry = load_registry(path=service.registry_path)
                _json_response(self, 200, _lanes_payload(registry))
                return
            if path == "/api/lanes/active":
                registry = load_registry(path=service.registry_path)
                record = registry.active_record()
                if record is None:
                    _json_response(self, 404, {"ok": False, "error": "no active lane"})
                    return
                _json_response(self, 200, {"ok": True, "lane": record.to_dict()})
                return
            if path.startswith("/api/lanes/") and path.endswith("/health"):
                instance = unquote(path.removeprefix("/api/lanes/").removesuffix("/health"))
                registry = load_registry(path=service.registry_path)
                record = registry.lanes.get(instance)
                if record is None:
                    _json_response(self, 404, {"ok": False, "error": f"unknown lane: {instance}"})
                    return
                health = service.refresh_lane_health(record)
                _json_response(self, 200, {"ok": True, "lane": instance, "health": health.to_dict()})
                return
            _json_response(self, 404, {"ok": False, "error": "not found"})

        def do_PUT(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            path = parsed.path.rstrip("/")
            if path == "/api/lanes/active":
                body = _read_json_body(self)
                instance = str(body.get("instance") or "").strip()
                if not instance:
                    _json_response(self, 400, {"ok": False, "error": "instance required"})
                    return
                try:
                    record = set_active_lane(instance, path=service.registry_path)
                except KeyError as exc:
                    _json_response(self, 404, {"ok": False, "error": str(exc)})
                    return
                _json_response(self, 200, {"ok": True, "lane": record.to_dict()})
                return
            _json_response(self, 404, {"ok": False, "error": "not found"})

        def do_POST(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            path = parsed.path.rstrip("/")
            if path == "/api/lanes":
                body = _read_json_body(self)
                ide = str(body.get("ide") or "").strip().lower()
                instance = str(body.get("instance") or "").strip()
                if not ide or not instance:
                    _json_response(self, 400, {"ok": False, "error": "ide and instance required"})
                    return
                record = register_lane(
                    ide=ide,
                    instance=instance,
                    project=str(body.get("project") or "").strip() or None,
                    set_active=bool(body.get("set_active", False)),
                    editor_cli=str(body.get("editor_cli") or "").strip() or None,
                    path=service.registry_path,
                )
                _json_response(self, 200, {"ok": True, "lane": record.to_dict()})
                return
            if path.startswith("/api/lanes/") and path.endswith("/daemon/start"):
                instance = unquote(path.removeprefix("/api/lanes/").removesuffix("/daemon/start"))
                ok, detail = service.start_lane_daemon(instance)
                status = 200 if ok else 500
                _json_response(self, status, {"ok": ok, "detail": detail, "instance": instance})
                return
            if path.startswith("/api/lanes/") and path.endswith("/daemon/stop"):
                instance = unquote(path.removeprefix("/api/lanes/").removesuffix("/daemon/stop"))
                ok, detail = service.stop_lane_daemon(instance)
                status = 200 if ok else 500
                _json_response(self, status, {"ok": ok, "detail": detail, "instance": instance})
                return
            if path.startswith("/api/lanes/") and path.endswith("/reconnect"):
                instance = unquote(path.removeprefix("/api/lanes/").removesuffix("/reconnect"))
                ok, detail = service.reconnect_lane(instance)
                status = 200 if ok else 500
                _json_response(self, status, {"ok": ok, "detail": detail, "instance": instance})
                return
            if path == "/api/refresh":
                service.refresh_all_health()
                registry = load_registry(path=service.registry_path)
                _json_response(self, 200, {"ok": True, **_lanes_payload(registry)})
                return
            _json_response(self, 404, {"ok": False, "error": "not found"})

        def do_DELETE(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            path = parsed.path.rstrip("/")
            if path.startswith("/api/lanes/"):
                instance = unquote(path.removeprefix("/api/lanes/"))
                if not instance or "/" in instance:
                    _json_response(self, 400, {"ok": False, "error": "invalid instance"})
                    return
                removed = remove_lane(instance, path=service.registry_path)
                if not removed:
                    _json_response(self, 404, {"ok": False, "error": f"unknown lane: {instance}"})
                    return
                _json_response(self, 200, {"ok": True, "removed": instance})
                return
            _json_response(self, 404, {"ok": False, "error": "not found"})

    return SupervisorHTTPHandler


class SupervisorHTTPServer:
    def __init__(
        self,
        service: SupervisorService,
        *,
        host: str,
        port: int,
    ) -> None:
        handler = make_handler(service)
        self._httpd = ThreadingHTTPServer((host, port), handler)
        self._thread: threading.Thread | None = None
        self.host = host
        self.port = self._httpd.server_address[1]

    @property
    def url(self) -> str:
        return f"http://{self.host}:{self.port}"

    def serve_forever(self) -> None:
        self._httpd.serve_forever(poll_interval=0.5)

    def start_background(self) -> None:
        if self._thread is not None:
            return
        self._thread = threading.Thread(target=self.serve_forever, name="coru-supervisor-http", daemon=True)
        self._thread.start()

    def shutdown(self) -> None:
        self._httpd.shutdown()
        self._httpd.server_close()
        if self._thread is not None:
            self._thread.join(timeout=2.0)
            self._thread = None
