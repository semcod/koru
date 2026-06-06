"""HTTP control plane for the coru supervisor."""

from __future__ import annotations

import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import urlparse

from coru.supervisor.http_handlers import (
    dispatch_delete,
    dispatch_get,
    dispatch_post,
    dispatch_put,
)
from coru.supervisor.http_util import json_response
from coru.supervisor.service import SupervisorService


def make_handler(service: SupervisorService) -> type[BaseHTTPRequestHandler]:
    class SupervisorHTTPHandler(BaseHTTPRequestHandler):
        server_version = "coru-supervisor/0.1"

        def log_message(self, format: str, *args: Any) -> None:  # noqa: A003
            if service.verbose:
                super().log_message(format, *args)

        def do_GET(self) -> None:  # noqa: N802
            if dispatch_get(self, service, urlparse(self.path).path):
                return
            json_response(self, 404, {"ok": False, "error": "not found"})

        def do_PUT(self) -> None:  # noqa: N802
            if dispatch_put(self, service, urlparse(self.path).path):
                return
            json_response(self, 404, {"ok": False, "error": "not found"})

        def do_POST(self) -> None:  # noqa: N802
            if dispatch_post(self, service, urlparse(self.path).path):
                return
            json_response(self, 404, {"ok": False, "error": "not found"})

        def do_DELETE(self) -> None:  # noqa: N802
            if dispatch_delete(self, service, urlparse(self.path).path):
                return
            json_response(self, 404, {"ok": False, "error": "not found"})

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
