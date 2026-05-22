"""HTTP request handler for dashboard server.

Internal module containing the DashboardRequestHandler subclass with
route implementations for the dashboard API.
"""

from __future__ import annotations

from functools import lru_cache
from http.server import BaseHTTPRequestHandler
from importlib.resources import files
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from koru.env_config import apply_env_updates, env_config_payload, write_env_config
from koruapi.dashboard_config import (
  DashboardConfigDefaults,
  dashboard_config_payload,
  save_dashboard_config,
)
from koruapi.dashboard_context import dashboard_context_payload, dashboard_handoff_markdown
from koruapi.dashboard_http import DashboardRequestHandler
from koruapi.dashboard_projects import (
  dashboard_workspace,
  resolve_dashboard_project,
)
from koruapi.dashboard_state import dashboard_state
from koruapi.dashboard_tickets import (
  bulk_waiting_input_action,
  create_ticket_from_dashboard,
  reorder_ticket_from_dashboard,
  update_ticket_from_dashboard,
)
from koruapi.dashboard_topology import (
  apply_dashboard_topology_update,
  dashboard_topology_payload,
)
from koruapi.dashboard_runtime import (
  runtime_context_error_payload,
  runtime_context_payload,
  save_runtime_context_config,
)
from koruapi.dashboard_serve_utils import ServeConfig


@lru_cache(maxsize=1)
def _load_dashboard_html() -> str:
    """Load and cache the dashboard HTML template from the package."""
    return (files("koruapi") / "dashboard_template.html").read_text(encoding="utf-8")


def _config_defaults(config: ServeConfig) -> DashboardConfigDefaults:
    return DashboardConfigDefaults(
        workspace=dashboard_workspace(config.project, config.workspace),
        host=config.host,
        port=config.port,
        lan=bool(config.lan),
        auto_port=bool(config.auto_port),
        queue_name=config.queue_name,
    )


def _state_payload(config: ServeConfig) -> dict[str, Any]:
    return dashboard_state(
        project=config.project,
        host=config.host,
        port=config.port,
        lan=bool(config.lan),
        configured_workspace=config.workspace,
        queue_name=config.queue_name,
    )


def build_dashboard_handler(config: ServeConfig) -> type[BaseHTTPRequestHandler]:
    """Build and return a DashboardRequestHandler subclass for the dashboard."""

    def _resolve_dashboard_project(raw: object | None) -> Path:
        return resolve_dashboard_project(config.project, config.workspace, raw)

    class _Handler(DashboardRequestHandler):
        def _selected_project(self, body: dict[str, Any] | None = None) -> Path:
            """Resolve project from query string or request body."""
            if body is not None:
                values = body.get("project")
                if isinstance(values, list):
                    raw = values[0] if values else None
                else:
                    raw = values
            else:
                qs = parse_qs(urlparse(self.path).query)
                values = qs.get("project")
                raw = values[0] if values else None
            return _resolve_dashboard_project(raw)

        def _get_dashboard(self) -> None:
            try:
                self._send_json(_state_payload(config))
            except Exception as exc:  # pragma: no cover — surface discovery errors
                self._send_json({"error": str(exc), "type": type(exc).__name__}, status=500)

        def _get_config(self) -> None:
            try:
                project = self._selected_project()
                self._send_json(
                    dashboard_config_payload(project, _config_defaults(config))
                )
            except ValueError as exc:
                self._send_json({"error": str(exc)}, status=400)
            except Exception as exc:  # pragma: no cover — surface config errors
                self._send_json({"error": str(exc), "type": type(exc).__name__}, status=500)

        def _get_env_config(self) -> None:
            try:
                project = self._selected_project()
                self._send_json(env_config_payload(project))
            except ValueError as exc:
                self._send_json({"error": str(exc)}, status=400)
            except Exception as exc:  # pragma: no cover — surface env-config errors
                self._send_json({"error": str(exc), "type": type(exc).__name__}, status=500)

        def _get_context(self) -> None:
            try:
                project = self._selected_project()
                ctx = dashboard_context_payload(project, config.queue_name)
            except ValueError as exc:
                self._send_json({"error": str(exc)}, status=400)
                return
            except Exception as exc:  # pragma: no cover — surface errors
                self._send_json(
                    {"error": str(exc), "type": type(exc).__name__},
                    status=500,
                )
                return
            self._send_json(ctx)

        def _get_topology(self) -> None:
            try:
                project = self._selected_project()
                topo = dashboard_topology_payload(project)
            except ValueError as exc:
                self._send_json({"error": str(exc)}, status=400)
                return
            except Exception as exc:  # pragma: no cover — surface errors
                self._send_json(
                    {"error": str(exc), "type": type(exc).__name__},
                    status=500,
                )
                return
            self._send_json(topo)

        def _get_runtime_context(self) -> None:
            project = config.project
            try:
                project = self._selected_project()
                runtime = runtime_context_payload(project)
            except ValueError as exc:
                self._send_json({"error": str(exc)}, status=400)
                return
            except Exception as exc:  # pragma: no cover — optional planfile integration
                runtime = runtime_context_error_payload(project, exc)
            self._send_json(runtime)

        def _get_handoff(self) -> None:
            try:
                project = self._selected_project()
                md = dashboard_handoff_markdown(project, config.queue_name)
            except ValueError as exc:
                self._send(400, str(exc).encode("utf-8"))
                return
            except Exception as exc:  # pragma: no cover
                self._send(500, str(exc).encode("utf-8"))
                return
            self._send(
                200,
                md.encode("utf-8"),
                "text/markdown; charset=utf-8",
            )

        def do_GET(self) -> None:  # noqa: N802 — stdlib API
            path = urlparse(self.path).path
            if path in ("/", "/index.html"):
                self._send(
                    200,
                    _load_dashboard_html().encode("utf-8"),
                    "text/html; charset=utf-8",
                )
                return
            if path == "/health":
                self._send_json({"ok": True})
                return
            if path in ("/grid", "/api/mesh/frames", "/api/mesh/diagnostics"):
                from korumesh.dashboard import serve_mesh_http

                if serve_mesh_http(self, path, project=config.project):
                    return
            route = {
                "/api/dashboard": self._get_dashboard,
                "/api/config": self._get_config,
                "/api/env-config": self._get_env_config,
                "/api/context": self._get_context,
                "/api/topology": self._get_topology,
                "/api/runtime-context": self._get_runtime_context,
                "/api/handoff": self._get_handoff,
            }.get(path)
            if route is not None:
                route()
                return
            self._send(404, b"not found")

        def _post_topology(self, body: dict[str, Any]) -> None:
            try:
                project = self._selected_project(body)
            except ValueError as exc:
                self._send_json({"error": str(exc)}, status=400)
                return
            merged, err, status = apply_dashboard_topology_update(project, body)
            if err is not None:
                self._send_json(err, status=status)
                return
            self._send_json(merged)

        def _post_runtime_context_config(self, body: dict[str, Any]) -> None:
            try:
                project = self._selected_project(body)
                saved_config = save_runtime_context_config(project, body)
            except ValueError as exc:
                self._send_json({"error": str(exc)}, status=400)
                return
            except Exception as exc:  # pragma: no cover — optional planfile integration
                self._send_json({"error": str(exc), "type": type(exc).__name__}, status=500)
                return
            self._send_json(saved_config)

        def _post_env_config(self, body: dict[str, Any]) -> None:
            try:
                project = self._selected_project(body)
            except ValueError as exc:
                self._send_json({"error": str(exc)}, status=400)
                return
            raw = body.get("values")
            if not isinstance(raw, dict):
                self._send_json({"error": "values must be an object"}, status=400)
                return
            from koru.env_config import KORU_ENV_KEYS

            allowed = {spec.name for spec in KORU_ENV_KEYS}
            updates: dict[str, str] = {}
            for key, value in raw.items():
                if not isinstance(key, str) or key not in allowed:
                    continue
                updates[key] = "" if value is None else str(value).strip()
            try:
                path = write_env_config(project, updates)
                apply_env_updates(updates)
            except Exception as exc:  # pragma: no cover — write errors
                self._send_json({"error": str(exc), "type": type(exc).__name__}, status=500)
                return
            self._send_json({
                **env_config_payload(project),
                "saved": True,
                "path": str(path),
                "applied": sorted(updates.keys()),
            })

        def _post_config(self, body: dict[str, Any]) -> None:
            try:
                project = self._selected_project(body)
                defaults = _config_defaults(config)
                result = save_dashboard_config(project, body, defaults)
            except ValueError as exc:
                self._send_json({"error": str(exc)}, status=400)
                return
            except Exception as exc:
                self._send_json({"error": str(exc), "type": type(exc).__name__}, status=500)
                return
            self._send_json({**dashboard_config_payload(project, defaults), "saved": True, "path": str(result.path)})

        def _post_waiting_input_bulk(self, body: dict[str, Any]) -> None:
            action = str(body.get("action") or "").strip().lower()
            if action not in {"approve", "reject"}:
                self._send_json({"error": "action must be approve|reject"}, status=400)
                return
            ticket_ids_raw = body.get("ticket_ids")
            if not isinstance(ticket_ids_raw, list):
                self._send_json({"error": "ticket_ids must be an array"}, status=400)
                return
            ticket_ids = [str(x).strip() for x in ticket_ids_raw if str(x).strip()]
            reason = str(body.get("reason") or "").strip()
            try:
                project = self._selected_project(body)
            except ValueError as exc:
                self._send_json({"error": str(exc)}, status=400)
                return
            result = bulk_waiting_input_action(
                project,
                ticket_ids=ticket_ids,
                action=action,
                reason=reason,
            )
            if not result.get("ok"):
                self._send_json(result, status=400)
                return
            self._send_json(result)

        def _post_ticket_create(self, body: dict[str, Any]) -> None:
            try:
                project = self._selected_project(body)
                self._send_json(create_ticket_from_dashboard(project, body))
            except ValueError as exc:
                self._send_json({"error": str(exc)}, status=400)
            except Exception as exc:
                self._send_json(
                    {"error": str(exc), "type": type(exc).__name__},
                    status=500,
                )

        def _post_ticket_update(self, body: dict[str, Any]) -> None:
            ticket_id = str(body.get("ticket_id") or "").strip()
            if not ticket_id:
                self._send_json({"error": "ticket_id is required"}, status=400)
                return
            try:
                project = self._selected_project(body)
                result = update_ticket_from_dashboard(
                    project,
                    ticket_id=ticket_id,
                    priority=str(body["priority"]).strip() if "priority" in body else None,
                    queue_name=str(body["queue_name"]).strip() if "queue_name" in body else None,
                )
            except ValueError as exc:
                self._send_json({"error": str(exc)}, status=400)
                return
            except Exception as exc:
                self._send_json({"error": str(exc), "type": type(exc).__name__}, status=500)
                return
            self._send_json(result)

        def _post_ticket_reorder(self, body: dict[str, Any]) -> None:
            ticket_id = str(body.get("ticket_id") or "").strip()
            direction = str(body.get("direction") or "").strip().lower()
            if not ticket_id:
                self._send_json({"error": "ticket_id is required"}, status=400)
                return
            try:
                project = self._selected_project(body)
                result = reorder_ticket_from_dashboard(project, ticket_id=ticket_id, direction=direction)
            except ValueError as exc:
                self._send_json({"error": str(exc)}, status=400)
                return
            except Exception as exc:
                self._send_json({"error": str(exc), "type": type(exc).__name__}, status=500)
                return
            self._send_json(result)

        def do_POST(self) -> None:  # noqa: N802 — stdlib API
            path = urlparse(self.path).path
            try:
                body = self._read_json_body()
            except Exception as exc:
                self._send_json({"error": str(exc)}, status=400)
                return

            route = {
                "/api/topology": self._post_topology,
                "/api/runtime-context/config": self._post_runtime_context_config,
                "/api/config": self._post_config,
                "/api/env-config": self._post_env_config,
                "/api/tickets/waiting-input/bulk": self._post_waiting_input_bulk,
                "/api/tickets/create": self._post_ticket_create,
                "/api/tickets/update": self._post_ticket_update,
                "/api/tickets/reorder": self._post_ticket_reorder,
            }.get(path)
            if route is not None:
                route(body)
                return
            self._send(404, b"not found")

    return _Handler
