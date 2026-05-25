"""HTTP request handler for dashboard server.

Internal module containing the DashboardRequestHandler subclass with
route implementations for the dashboard API.
"""

from __future__ import annotations

from functools import lru_cache
from html import escape
from http.server import BaseHTTPRequestHandler
from importlib.resources import files
from pathlib import Path
from typing import Any
from urllib.parse import urlencode, parse_qs, urlparse

from koru.env_config import apply_env_updates, env_config_payload, write_env_config
from koru.interface_registry import blocker_interface_payload, interface_registry_payload
from koru.environment_profile import environment_profile_payload
from koruapi.dashboard_config import (
    DashboardConfigDefaults,
    dashboard_config_payload,
    save_dashboard_config,
)
from koruapi.dashboard_context import dashboard_context_payload, dashboard_handoff_markdown
from koruapi.dashboard_http import DashboardRequestHandler
from koruapi.dashboard_plugin_logs import dashboard_plugin_logs_payload
from koruapi.dashboard_projects import (
    dashboard_workspace,
    resolve_dashboard_project,
)
from koruapi.dashboard_runtime import (
    runtime_context_error_payload,
    runtime_context_payload,
    save_runtime_context_config,
)
from koruapi.dashboard_serve_utils import ServeConfig
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


def _build_dashboard_handler_impl(config: ServeConfig) -> type[BaseHTTPRequestHandler]:
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
            self._safe_respond_json(lambda: _state_payload(config))

        def _get_config(self) -> None:
            self._safe_respond_json(
                lambda: dashboard_config_payload(
                    self._selected_project(), _config_defaults(config)
                )
            )

        def _get_env_config(self) -> None:
            self._safe_respond_json(
                lambda: env_config_payload(self._selected_project())
            )

        def _get_context(self) -> None:
            self._safe_respond_json(
                lambda: dashboard_context_payload(
                    self._selected_project(), config.queue_name
                )
            )

        def _get_topology(self) -> None:
            self._safe_respond_json(
                lambda: dashboard_topology_payload(self._selected_project())
            )

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

        def _get_autonomy_trace(self) -> None:
            """Return the structured ``DecisionRecord`` ring buffer.

            Same data the operator sees on each cycle as ``  decision:
            observed=… → decided=… → action=…``. Exposed so the dashboard
            and CLI tooling can answer "why is Koru not doing anything?"
            without grepping shell scrollback.
            """
            from koru.autonomy.decision_trace import (
                SKIP_CODE_DESCRIPTIONS,
                load_recent_decisions,
            )

            try:
                project = self._selected_project()
            except ValueError as exc:
                self._send_json({"error": str(exc)}, status=400)
                return
            try:
                history = load_recent_decisions(project)
            except Exception as exc:  # pragma: no cover — defensive
                self._send_json(
                    {"error": str(exc), "type": type(exc).__name__},
                    status=500,
                )
                return
            self._send_json(
                {
                    "project": str(project),
                    "decisions": history,
                    "skip_code_descriptions": dict(SKIP_CODE_DESCRIPTIONS),
                    "blocked_interfaces": {
                        blocker: blocker_interface_payload(blocker)
                        for blocker in {
                            str(item.get("blocked_by") or "").strip()
                            for item in history
                            if str(item.get("blocked_by") or "").strip()
                        }
                    },
                }
            )

        def _get_interfaces(self) -> None:
            self._safe_respond_json(interface_registry_payload)

        def _get_environment(self) -> None:
            self._safe_respond_json(
                lambda: environment_profile_payload(self._selected_project())
            )

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

        def _get_plugin_logs(self) -> None:
            self._safe_respond_json(dashboard_plugin_logs_payload)

        def _redirect_create_project_ticket_prompt(self) -> None:
            qs = parse_qs(urlparse(self.path).query)
            query: dict[str, str] = {
                "tab": "tickets",
                "focus": "create-ticket",
                "change": "llm.prompt.create-ticket-for-project",
                "title": "Project discovery: generate code2llm analysis and tickets",
                "priority": "high",
                "executor_kind": "human",
                "queue_name": "operator",
                "description": (
                    "Run a broad project discovery pass because the planfile queue is idle.\n\n"
                    "1. Refresh project/code2llm artifacts when stale.\n"
                    "2. Review findings and create focused planfile tickets for concrete work.\n"
                    "3. Keep broad discovery scoped: stop when runnable tickets exist."
                ),
            }
            raw_project = qs.get("project", [""])[0].strip()
            if raw_project:
                query["project"] = raw_project
            location = "/?" + urlencode(query)
            self.send_response(303)
            self.send_header("Location", location)
            self.end_headers()

        def _get_create_project_ticket_action(self) -> None:
            try:
                project = self._selected_project()
                result = create_ticket_from_dashboard(
                    project,
                    {
                        "title": "Project discovery: generate code2llm analysis and tickets",
                        "description": (
                            "Run a broad project discovery pass because the planfile queue is idle.\n\n"
                            "1. Refresh project/code2llm artifacts when stale.\n"
                            "2. Review findings and create focused planfile tickets for concrete work.\n"
                            "3. Keep broad discovery scoped: stop when runnable tickets exist."
                        ),
                        "priority": "high",
                        "executor_kind": "human",
                        "queue_name": "operator",
                        "dedupe_key": "koru:quick-action:create-ticket-for-project",
                        "signal": "project_discovery_quick_action",
                    },
                )
                status = "reused" if result.get("reused") else "created"
                title = f"Ticket {status}: {result.get('ticket_id')}"
                body = (
                    "<!doctype html><meta charset='utf-8'>"
                    "<meta name='viewport' content='width=device-width, initial-scale=1'>"
                    "<title>koru action result</title>"
                    "<style>"
                    "body{font-family:system-ui,sans-serif;max-width:760px;margin:48px auto;padding:0 20px;"
                    "line-height:1.45;color:#17202a} .ok{color:#147a3d;font-weight:700}"
                    "code{background:#eef2f7;padding:2px 5px;border-radius:4px}"
                    "a{color:#0b5fff}"
                    "</style>"
                    f"<h1 class='ok'>{escape(title)}</h1>"
                    f"<p>Project: <code>{escape(str(project))}</code></p>"
                    f"<p>Ticket: <code>{escape(str(result.get('ticket_id') or ''))}</code></p>"
                    f"<p>Name: {escape(str(result.get('name') or ''))}</p>"
                    "<p>This quick action is idempotent: repeated clicks reuse the same active ticket.</p>"
                    "<p><a href='/?tab=tickets'>Open tickets</a> · "
                    "<a href='/api/context'>Context JSON</a></p>"
                )
                self._send(200, body.encode("utf-8"), "text/html; charset=utf-8")
            except Exception as exc:
                body = (
                    "<!doctype html><meta charset='utf-8'>"
                    "<meta name='viewport' content='width=device-width, initial-scale=1'>"
                    "<title>koru action failed</title>"
                    "<style>body{font-family:system-ui,sans-serif;max-width:760px;margin:48px auto;padding:0 20px;"
                    "line-height:1.45;color:#17202a}.err{color:#b42318;font-weight:700}"
                    "pre{white-space:pre-wrap;background:#fff1f0;padding:12px;border-radius:6px}</style>"
                    "<h1 class='err'>Action failed</h1>"
                    f"<pre>{escape(type(exc).__name__ + ': ' + str(exc))}</pre>"
                    "<p><a href='/?tab=tickets'>Open tickets</a></p>"
                )
                self._send(500, body.encode("utf-8"), "text/html; charset=utf-8")

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
            if path == "/capture/host":
                from korumesh.browser_capture import serve_browser_capture_http

                if serve_browser_capture_http(
                    self,
                    path,
                    project=config.project,
                    method="GET",
                ):
                    return
            if path == "/llm/prompt/create-ticket-for-project":
                self._redirect_create_project_ticket_prompt()
                return
            if path == "/llm/action/create-ticket-for-project":
                self._get_create_project_ticket_action()
                return
            route = {
                "/api/dashboard": self._get_dashboard,
                "/api/config": self._get_config,
                "/api/env-config": self._get_env_config,
                "/api/context": self._get_context,
                "/api/topology": self._get_topology,
                "/api/runtime-context": self._get_runtime_context,
                "/api/handoff": self._get_handoff,
                "/api/plugin-logs": self._get_plugin_logs,
                "/api/autonomy/trace": self._get_autonomy_trace,
                "/api/interfaces": self._get_interfaces,
                "/api/environment": self._get_environment,
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
            self._send_json(
                {
                    **dashboard_config_payload(project, defaults),
                    "saved": True,
                    "path": str(result.path),
                }
            )

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

        def _post_remote_drive(self, body: dict[str, Any]) -> None:
            ide = str(body.get("ide") or "").strip()
            text = str(body.get("text") or "").strip()
            require_plugin = bool(body.get("require_plugin", False))
            if not ide or not text:
                self._send_json({"error": "ide and text are required"}, status=400)
                return
            try:
                from koruide.socket import default_socket_path
                from koru.autopilot.client import AutopilotClient
                
                socket_path = default_socket_path()
                client = AutopilotClient(socket_path=socket_path, timeout=5.0)
                res = client.drive(ide=ide, text=text, require_plugin=require_plugin)
                self._send_json({"ok": True, "result": res})
            except Exception as exc:
                self._send_json({"error": str(exc), "type": type(exc).__name__}, status=500)

        def _post_ticket_reorder(self, body: dict[str, Any]) -> None:
            ticket_id = str(body.get("ticket_id") or "").strip()
            direction = str(body.get("direction") or "").strip().lower()
            if not ticket_id:
                self._send_json({"error": "ticket_id is required"}, status=400)
                return
            try:
                project = self._selected_project(body)
                result = reorder_ticket_from_dashboard(
                    project,
                    ticket_id=ticket_id,
                    direction=direction,
                )
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

            if path == "/api/mesh/browser-upload":
                from korumesh.browser_capture import serve_browser_capture_http

                if serve_browser_capture_http(
                    self,
                    path,
                    project=config.project,
                    method="POST",
                    body=body,
                ):
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
                "/api/remote/drive": self._post_remote_drive,
            }.get(path)
            if route is not None:
                route(body)
                return
            self._send(404, b"not found")

    return _Handler


def build_dashboard_handler(config: ServeConfig) -> type[BaseHTTPRequestHandler]:
    """Build and return a DashboardRequestHandler subclass for the dashboard."""
    return _build_dashboard_handler_impl(config)
