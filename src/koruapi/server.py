"""stdlib HTTP API server for koru integrations."""

from __future__ import annotations

import json
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from .integrations import list_integrations
from .invoke import InvokeError, invoke_integration
from .openapi import build_openapi_document

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8790


def _json_response(handler: BaseHTTPRequestHandler, status: int, payload: dict[str, Any]) -> None:
    body = json.dumps(payload, indent=2, sort_keys=True).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def _read_json_body(handler: BaseHTTPRequestHandler) -> dict[str, Any]:
    length = int(handler.headers.get("Content-Length", "0") or "0")
    raw = handler.rfile.read(length) if length else b"{}"
    body = json.loads(raw.decode("utf-8") or "{}")
    if not isinstance(body, dict):
        raise ValueError("JSON body must be an object")
    return body


def _parse_invoke_request(
    body: dict[str, Any], default_project: Path
) -> tuple[str, str, Path, dict[str, Any]]:
    integration_id = str(body.get("integration_id") or body.get("id") or "")
    method = str(body.get("method") or "run")
    project_raw = body.get("project") or str(default_project)
    project = Path(str(project_raw)).resolve()
    payload = body.get("body") if isinstance(body.get("body"), dict) else body.get("payload")
    if not isinstance(payload, dict):
        payload = {
            k: v
            for k, v in body.items()
            if k not in {"integration_id", "id", "method", "project", "body", "payload"}
        }
    return integration_id, method, project, payload


def _handle_invoke_post(
    handler: BaseHTTPRequestHandler,
    *,
    default_project: Path,
) -> None:
    try:
        body = _read_json_body(handler)
    except json.JSONDecodeError as exc:
        _json_response(handler, 400, {"ok": False, "error": "invalid_json", "message": str(exc)})
        return
    except ValueError as exc:
        _json_response(handler, 400, {"ok": False, "error": "invalid_json", "message": str(exc)})
        return
    integration_id, method, project, payload = _parse_invoke_request(body, default_project)
    try:
        result = invoke_integration(
            integration_id,
            project=project,
            method=method,
            body=payload,
        )
        _json_response(
            handler,
            200,
            {"ok": True, "integration_id": integration_id, "method": method, "result": result},
        )
    except InvokeError as exc:
        _json_response(handler, 400, {"ok": False, "error": "invoke_error", "message": str(exc)})
    except Exception as exc:
        _json_response(
            handler,
            500,
            {
                "ok": False,
                "error": "internal",
                "message": str(exc),
                "traceback": traceback.format_exc(),
            },
        )


class KoruAPIHandler(BaseHTTPRequestHandler):
    project: Path
    server_version = "koruapi/0.1"

    def log_message(self, fmt: str, *args: object) -> None:
        print(f"koruapi: {self.address_string()} - {fmt % args}")

    def do_GET(self) -> None:  # noqa: N802
        from koru.activity_log import activity

        parsed = urlparse(self.path)
        activity("API", f"GET {parsed.path}")
        if parsed.path == "/health":
            _json_response(self, 200, {"ok": True, "service": "koruapi"})
            return
        if parsed.path in ("/api/v1/openapi.json", "/docs/openapi.json"):
            spec = build_openapi_document(
                host=self.server.server_address[0], port=self.server.server_address[1]
            )
            _json_response(self, 200, spec)
            return
        if parsed.path == "/api/v1/integrations":
            tag = parse_qs(parsed.query).get("tag", [None])[0]
            specs = list_integrations(tag=tag)
            _json_response(
                self,
                200,
                {
                    "ok": True,
                    "integrations": [
                        {
                            "id": s.id,
                            "title": s.title,
                            "description": s.description,
                            "transport": s.transport,
                            "methods": list(s.methods),
                            "cli_equivalent": s.cli_equivalent,
                            "mcp_tool": s.mcp_tool,
                            "tags": list(s.tags),
                        }
                        for s in specs
                    ],
                },
            )
            return
        if parsed.path == "/api/v1/ide/commands":
            from koruide.command_catalog import build_ide_command_catalog, command_catalog_for_llm

            query = parse_qs(parsed.query)
            ide_raw = query.get("ide", ["all"])[0]
            ide = None if ide_raw in ("", "all") else ide_raw
            for_llm = query.get("for_llm", ["0"])[0].lower() in {"1", "true", "yes"}
            payload = command_catalog_for_llm(ide) if for_llm else build_ide_command_catalog(ide)
            _json_response(self, 200, {"ok": True, "catalog": payload})
            return
        if parsed.path == "/api/v1/ide/scenario-schema":
            from koruide.command_scenario import ide_command_scenario_schema

            _json_response(self, 200, {"ok": True, "schema": ide_command_scenario_schema()})
            return
        _json_response(self, 404, {"ok": False, "error": "not_found", "path": parsed.path})

    def do_POST(self) -> None:  # noqa: N802
        from koru.activity_log import activity

        parsed = urlparse(self.path)
        activity("API", f"POST {parsed.path}")
        if parsed.path != "/api/v1/invoke":
            _json_response(self, 404, {"ok": False, "error": "not_found"})
            return
        _handle_invoke_post(self, default_project=self.project)


def serve(
    *,
    project: Path,
    host: str = DEFAULT_HOST,
    port: int = DEFAULT_PORT,
) -> None:
    """Run koruapi HTTP server until interrupted."""
    project = project.resolve()

    class _BoundHandler(KoruAPIHandler):
        pass

    _BoundHandler.project = project
    httpd = ThreadingHTTPServer((host, port), _BoundHandler)
    print(f"koruapi: listening on http://{host}:{port}/ (project={project})")
    print("koruapi: GET  /api/v1/openapi.json")
    print("koruapi: GET  /api/v1/integrations")
    print('koruapi: POST /api/v1/invoke  {"integration_id":"scan.apply","project":"."}')
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nkoruapi: stopped")
