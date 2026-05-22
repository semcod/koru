"""HTTP request/response primitives for the koru dashboard."""

from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler
from typing import Any
from urllib.parse import parse_qs, urlparse


class DashboardRequestHandler(BaseHTTPRequestHandler):
  def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
    return

  def _send(
    self,
    status: int,
    body: bytes,
    content_type: str = "text/plain; charset=utf-8",
  ) -> None:
    try:
      self.send_response(status)
      self.send_header("Content-Type", content_type)
      self.send_header("Content-Length", str(len(body)))
      self.send_header("Cache-Control", "no-store, no-cache, must-revalidate")
      self.send_header("Pragma", "no-cache")
      self.send_header("Expires", "0")
      self.end_headers()
      self.wfile.write(body)
    except (BrokenPipeError, ConnectionResetError):
      return

  def _send_json(self, payload: Any, status: int = 200) -> None:
    body = json.dumps(payload, indent=2, sort_keys=True).encode("utf-8")
    self._send(status, body, "application/json; charset=utf-8")

  def _read_json_body(self) -> dict[str, Any]:
    length = int(self.headers.get("Content-Length", "0") or "0")
    if length <= 0:
      return {}
    raw = self.rfile.read(length).decode("utf-8")
    data = json.loads(raw)
    return data if isinstance(data, dict) else {}

  def _query_params(self) -> dict[str, list[str]]:
    return parse_qs(urlparse(self.path).query)