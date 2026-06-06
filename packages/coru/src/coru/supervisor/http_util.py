"""Shared HTTP helpers for the coru supervisor control plane."""

from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler
from typing import Any

from coru.supervisor.models import SupervisorRegistry


def json_response(handler: BaseHTTPRequestHandler, status: int, payload: dict[str, Any]) -> None:
    body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def read_json_body(handler: BaseHTTPRequestHandler) -> dict[str, Any]:
    length = int(handler.headers.get("Content-Length") or "0")
    if length <= 0:
        return {}
    raw = handler.rfile.read(length)
    if not raw:
        return {}
    payload = json.loads(raw.decode("utf-8"))
    return payload if isinstance(payload, dict) else {}


def lanes_payload(registry: SupervisorRegistry) -> dict[str, Any]:
    return {
        "active_lane": registry.active_lane,
        "lanes": [lane.to_dict() for lane in registry.lanes.values()],
    }
