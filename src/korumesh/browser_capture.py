"""HTTP routes for browser-based screen capture (``getDisplayMedia``)."""

from __future__ import annotations

from functools import lru_cache
from importlib.resources import files
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from koruvision.providers.browser_getdisplay import (
    browser_capture_interval_seconds,
    ingest_browser_upload,
)

_TEMPLATE_NAME = "capture_host.html"


@lru_cache(maxsize=1)
def capture_host_html() -> str:
    return (files(__package__) / _TEMPLATE_NAME).read_text(encoding="utf-8")


def capture_host_context(path: str) -> dict[str, str]:
    qs = parse_qs(urlparse(path).query)
    peer = (qs.get("peer") or [""])[0].strip()
    interval = str(browser_capture_interval_seconds())
    return {"peer": peer, "interval": interval}


def _render_capture_host(path: str) -> bytes:
    html = capture_host_html()
    ctx = capture_host_context(path)
    for key, value in ctx.items():
        html = html.replace(f"{{{{{key}}}}}", value)
    return html.encode("utf-8")


def browser_upload_payload(project: Path, body: dict[str, Any]) -> dict[str, Any]:
    return ingest_browser_upload(project, body)


_BROWSER_ROUTES = {
    "/capture/host": "host",
    "/api/mesh/browser-upload": "upload",
}


def serve_browser_capture_http(
    handler: object,
    path: str,
    *,
    project: Path | None,
    method: str = "GET",
    body: dict[str, Any] | None = None,
) -> bool:
    route = _BROWSER_ROUTES.get(path)
    if route is None:
        return False
    send = handler._send
    send_json = handler._send_json
    if route == "host":
        if method != "GET":
            send_json({"error": "method not allowed"}, status=405)
            return True
        full_path = getattr(handler, "path", path)
        send(200, _render_capture_host(full_path), "text/html; charset=utf-8")
        return True
    if route == "upload":
        if method != "POST":
            send_json({"error": "method not allowed"}, status=405)
            return True
        if project is None:
            send_json({"error": "project not configured"}, status=500)
            return True
        try:
            payload = browser_upload_payload(project, body or {})
        except ValueError as exc:
            send_json({"error": str(exc)}, status=400)
            return True
        except Exception as exc:  # pragma: no cover
            send_json({"error": str(exc), "type": type(exc).__name__}, status=500)
            return True
        send_json(payload)
        return True
    return False
