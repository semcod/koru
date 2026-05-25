"""HTTP request handler for dashboard server.

Internal module containing the DashboardRequestHandler subclass with
route implementations for the dashboard API.
"""

from __future__ import annotations

from collections.abc import Callable
from functools import lru_cache
from http.server import BaseHTTPRequestHandler
from importlib.resources import files
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlencode, urlparse

from koru.env_config import apply_env_updates, env_config_payload, write_env_config
from koru.environment_profile import environment_profile_payload
from koru.interface_registry import blocker_interface_payload, interface_registry_payload
from koruapi.dashboard_config import (
    DashboardConfigDefaults,
    dashboard_config_payload,
    save_dashboard_config,
)
from koruapi.dashboard_context import dashboard_context_payload, dashboard_handoff_markdown
from koruapi.dashboard_html import (
    PROJECT_DISCOVERY_PROMPT_QUERY,
    PROJECT_DISCOVERY_TICKET_FIELDS,
    render_action_error_html,
    render_create_ticket_success_html,
)
from koruapi.dashboard_http import DashboardRequestHandler
from koruapi.dashboard_observability import dashboard_observability_trace_payload
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


def _get_dashboard(handler: Any, config: ServeConfig) -> None:
    handler._safe_respond_json(lambda: _state_payload(config))


def _get_config(handler: Any, config: ServeConfig) -> None:
    handler._safe_respond_json(
        lambda: dashboard_config_payload(handler._selected_project(), _config_defaults(config))
    )


def _get_env_config(handler: Any, _config: ServeConfig) -> None:
    handler._safe_respond_json(lambda: env_config_payload(handler._selected_project()))


def _get_context(handler: Any, config: ServeConfig) -> None:
    handler._safe_respond_json(
        lambda: dashboard_context_payload(handler._selected_project(), config.queue_name)
    )


def _get_topology(handler: Any, _config: ServeConfig) -> None:
    handler._safe_respond_json(lambda: dashboard_topology_payload(handler._selected_project()))


def _get_runtime_context(handler: Any, config: ServeConfig) -> None:
    project = config.project
    try:
        project = handler._selected_project()
        runtime = runtime_context_payload(project)
    except ValueError as exc:
        handler._send_json({"error": str(exc)}, status=400)
        return
    except Exception as exc:  # pragma: no cover — optional planfile integration
        runtime = runtime_context_error_payload(project, exc)
    handler._send_json(runtime)


def _get_ide_commands(handler: Any, _config: ServeConfig) -> None:
    from koruide.command_catalog import build_ide_command_catalog, command_catalog_for_llm

    parsed = urlparse(handler.path)
    query = parse_qs(parsed.query)
    ide_raw = query.get("ide", ["all"])[0]
    ide = None if ide_raw in ("", "all") else ide_raw
    for_llm = query.get("for_llm", ["0"])[0].lower() in {"1", "true", "yes"}

    def _payload() -> dict[str, Any]:
        return command_catalog_for_llm(ide) if for_llm else build_ide_command_catalog(ide)

    handler._safe_respond_json(_payload)


def _get_ide_scenario_schema(handler: Any, _config: ServeConfig) -> None:
    from koruide.command_scenario import ide_command_scenario_schema

    handler._safe_respond_json(ide_command_scenario_schema)


def _get_ide_strategy_prompt(handler: Any, _config: ServeConfig) -> None:
    from koruide.strategy_prompt import build_strategy_prompt

    parsed = urlparse(handler.path)
    query = parse_qs(parsed.query)
    ide_raw = query.get("ide", ["all"])[0]
    ide = None if ide_raw in ("", "all") else ide_raw
    for_llm_raw = query.get("for_llm", ["1"])[0].lower()
    for_llm = for_llm_raw in {"1", "true", "yes"}
    include_text_raw = query.get("include_text", ["1"])[0].lower()
    include_text = include_text_raw in {"1", "true", "yes"}

    def _payload() -> dict[str, Any]:
        try:
            return build_strategy_prompt(ide, for_llm=for_llm, include_text=include_text)
        except ValueError as exc:
            return {"ok": False, "error": str(exc)}

    handler._safe_respond_json(_payload)


def _get_autonomy_trace(handler: Any, _config: ServeConfig) -> None:
    """Return the structured ``DecisionRecord`` ring buffer."""
    from koru.autonomy.decision_trace import (
        SKIP_CODE_DESCRIPTIONS,
        load_recent_decisions,
    )

    try:
        project = handler._selected_project()
    except ValueError as exc:
        handler._send_json({"error": str(exc)}, status=400)
        return
    try:
        history = load_recent_decisions(project)
    except Exception as exc:  # pragma: no cover — defensive
        handler._send_json(
            {"error": str(exc), "type": type(exc).__name__},
            status=500,
        )
        return
    handler._send_json(
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


def _get_observe_trace(handler: Any, _config: ServeConfig) -> None:
    qs = handler._query_params()
    corr = _first_query_value(qs, "corr")
    ticket = _first_query_value(qs, "ticket")
    limit = _int_query_value(qs, "limit", default=50)
    handler._safe_respond_json(
        lambda: dashboard_observability_trace_payload(
            handler._selected_project(),
            corr=corr,
            ticket=ticket,
            limit=limit,
        )
    )


def _first_query_value(qs: dict[str, list[str]], key: str) -> str | None:
    values = qs.get(key) or []
    value = str(values[0]).strip() if values else ""
    return value or None


def _int_query_value(qs: dict[str, list[str]], key: str, *, default: int) -> int:
    value = _first_query_value(qs, key)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _get_interfaces(handler: Any, _config: ServeConfig) -> None:
    handler._safe_respond_json(interface_registry_payload)


def _get_environment(handler: Any, _config: ServeConfig) -> None:
    handler._safe_respond_json(lambda: environment_profile_payload(handler._selected_project()))


def _get_handoff(handler: Any, config: ServeConfig) -> None:
    try:
        project = handler._selected_project()
        md = dashboard_handoff_markdown(project, config.queue_name)
    except ValueError as exc:
        handler._send(400, str(exc).encode("utf-8"))
        return
    except Exception as exc:  # pragma: no cover
        handler._send(500, str(exc).encode("utf-8"))
        return
    handler._send(200, md.encode("utf-8"), "text/markdown; charset=utf-8")


def _get_plugin_logs(handler: Any, _config: ServeConfig) -> None:
    handler._safe_respond_json(dashboard_plugin_logs_payload)


def _redirect_create_project_ticket_prompt(handler: Any, _config: ServeConfig) -> None:
    qs = parse_qs(urlparse(handler.path).query)
    query = dict(PROJECT_DISCOVERY_PROMPT_QUERY)
    raw_project = qs.get("project", [""])[0].strip()
    if raw_project:
        query["project"] = raw_project
    location = "/?" + urlencode(query)
    handler.send_response(303)
    handler.send_header("Location", location)
    handler.end_headers()


def _get_create_project_ticket_action(handler: Any, _config: ServeConfig) -> None:
    try:
        project = handler._selected_project()
        result = create_ticket_from_dashboard(project, dict(PROJECT_DISCOVERY_TICKET_FIELDS))
        handler._send(
            200,
            render_create_ticket_success_html(str(project), result),
            "text/html; charset=utf-8",
        )
    except Exception as exc:
        handler._send(500, render_action_error_html(exc), "text/html; charset=utf-8")


def _post_topology(handler: Any, _config: ServeConfig, body: dict[str, Any]) -> None:
    try:
        project = handler._selected_project(body)
    except ValueError as exc:
        handler._send_json({"error": str(exc)}, status=400)
        return
    merged, err, status = apply_dashboard_topology_update(project, body)
    if err is not None:
        handler._send_json(err, status=status)
        return
    handler._send_json(merged)


def _post_runtime_context_config(handler: Any, _config: ServeConfig, body: dict[str, Any]) -> None:
    try:
        project = handler._selected_project(body)
        saved_config = save_runtime_context_config(project, body)
    except ValueError as exc:
        handler._send_json({"error": str(exc)}, status=400)
        return
    except Exception as exc:  # pragma: no cover — optional planfile integration
        handler._send_json({"error": str(exc), "type": type(exc).__name__}, status=500)
        return
    handler._send_json(saved_config)


def _post_env_config(handler: Any, _config: ServeConfig, body: dict[str, Any]) -> None:
    try:
        project = handler._selected_project(body)
    except ValueError as exc:
        handler._send_json({"error": str(exc)}, status=400)
        return
    raw = body.get("values")
    if not isinstance(raw, dict):
        handler._send_json({"error": "values must be an object"}, status=400)
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
        handler._send_json({"error": str(exc), "type": type(exc).__name__}, status=500)
        return
    handler._send_json(
        {
            **env_config_payload(project),
            "saved": True,
            "path": str(path),
            "applied": sorted(updates.keys()),
        }
    )


def _post_config(handler: Any, config: ServeConfig, body: dict[str, Any]) -> None:
    try:
        project = handler._selected_project(body)
        defaults = _config_defaults(config)
        result = save_dashboard_config(project, body, defaults)
    except ValueError as exc:
        handler._send_json({"error": str(exc)}, status=400)
        return
    except Exception as exc:
        handler._send_json({"error": str(exc), "type": type(exc).__name__}, status=500)
        return
    handler._send_json(
        {
            **dashboard_config_payload(project, defaults),
            "saved": True,
            "path": str(result.path),
        }
    )


def _post_waiting_input_bulk(handler: Any, _config: ServeConfig, body: dict[str, Any]) -> None:
    action = str(body.get("action") or "").strip().lower()
    if action not in {"approve", "reject"}:
        handler._send_json({"error": "action must be approve|reject"}, status=400)
        return
    ticket_ids_raw = body.get("ticket_ids")
    if not isinstance(ticket_ids_raw, list):
        handler._send_json({"error": "ticket_ids must be an array"}, status=400)
        return
    ticket_ids = [str(x).strip() for x in ticket_ids_raw if str(x).strip()]
    reason = str(body.get("reason") or "").strip()
    try:
        project = handler._selected_project(body)
    except ValueError as exc:
        handler._send_json({"error": str(exc)}, status=400)
        return
    result = bulk_waiting_input_action(
        project,
        ticket_ids=ticket_ids,
        action=action,
        reason=reason,
    )
    if not result.get("ok"):
        handler._send_json(result, status=400)
        return
    handler._send_json(result)


def _post_ticket_create(handler: Any, _config: ServeConfig, body: dict[str, Any]) -> None:
    try:
        project = handler._selected_project(body)
        handler._send_json(create_ticket_from_dashboard(project, body))
    except ValueError as exc:
        handler._send_json({"error": str(exc)}, status=400)
    except Exception as exc:
        handler._send_json(
            {"error": str(exc), "type": type(exc).__name__},
            status=500,
        )


def _post_ticket_update(handler: Any, _config: ServeConfig, body: dict[str, Any]) -> None:
    ticket_id = str(body.get("ticket_id") or "").strip()
    if not ticket_id:
        handler._send_json({"error": "ticket_id is required"}, status=400)
        return
    try:
        project = handler._selected_project(body)
        result = update_ticket_from_dashboard(
            project,
            ticket_id=ticket_id,
            priority=str(body["priority"]).strip() if "priority" in body else None,
            queue_name=str(body["queue_name"]).strip() if "queue_name" in body else None,
        )
    except ValueError as exc:
        handler._send_json({"error": str(exc)}, status=400)
        return
    except Exception as exc:
        handler._send_json({"error": str(exc), "type": type(exc).__name__}, status=500)
        return
    handler._send_json(result)


def _post_remote_drive(handler: Any, _config: ServeConfig, body: dict[str, Any]) -> None:
    ide = str(body.get("ide") or "").strip()
    text = str(body.get("text") or "").strip()
    require_plugin = bool(body.get("require_plugin", False))
    if not ide or not text:
        handler._send_json({"error": "ide and text are required"}, status=400)
        return
    try:
        project = handler._selected_project(body)
    except ValueError as exc:
        handler._send_json({"error": str(exc)}, status=400)
        return
    corr = str(body.get("corr") or body.get("ticket") or "dashboard-remote-drive").strip()
    try:
        from koru.autopilot.client import AutopilotClient
        from koru.control_commands import api_command
        from koruide.socket import default_socket_path

        api_command(
            project,
            corr=corr,
            method="POST",
            path="/api/remote/drive",
            body={
                "ide": ide,
                "text": text,
                "require_plugin": require_plugin,
                "corr": corr,
            },
            actor="dashboard",
        )
        socket_path = default_socket_path()
        client = AutopilotClient(socket_path=socket_path, timeout=5.0)
        res = client.drive(ide=ide, text=text, require_plugin=require_plugin)
        handler._send_json({"ok": True, "result": res})
    except Exception as exc:
        handler._send_json({"error": str(exc), "type": type(exc).__name__}, status=500)


def _post_ticket_reorder(handler: Any, _config: ServeConfig, body: dict[str, Any]) -> None:
    ticket_id = str(body.get("ticket_id") or "").strip()
    direction = str(body.get("direction") or "").strip().lower()
    if not ticket_id:
        handler._send_json({"error": "ticket_id is required"}, status=400)
        return
    try:
        project = handler._selected_project(body)
        result = reorder_ticket_from_dashboard(
            project,
            ticket_id=ticket_id,
            direction=direction,
        )
    except ValueError as exc:
        handler._send_json({"error": str(exc)}, status=400)
        return
    except Exception as exc:
        handler._send_json({"error": str(exc), "type": type(exc).__name__}, status=500)
        return
    handler._send_json(result)


_GetHandler = Callable[[Any, ServeConfig], None]
_PostHandler = Callable[[Any, ServeConfig, dict[str, Any]], None]

_GET_ROUTES: dict[str, _GetHandler] = {
    "/api/dashboard": _get_dashboard,
    "/api/config": _get_config,
    "/api/env-config": _get_env_config,
    "/api/context": _get_context,
    "/api/topology": _get_topology,
    "/api/runtime-context": _get_runtime_context,
    "/api/ide/commands": _get_ide_commands,
    "/api/ide/scenario-schema": _get_ide_scenario_schema,
    "/api/ide/strategy-prompt": _get_ide_strategy_prompt,
    "/api/handoff": _get_handoff,
    "/api/plugin-logs": _get_plugin_logs,
    "/api/autonomy/trace": _get_autonomy_trace,
    "/api/observe/trace": _get_observe_trace,
    "/api/interfaces": _get_interfaces,
    "/api/environment": _get_environment,
    "/llm/prompt/create-ticket-for-project": _redirect_create_project_ticket_prompt,
    "/llm/action/create-ticket-for-project": _get_create_project_ticket_action,
}

_POST_ROUTES: dict[str, _PostHandler] = {
    "/api/topology": _post_topology,
    "/api/runtime-context/config": _post_runtime_context_config,
    "/api/config": _post_config,
    "/api/env-config": _post_env_config,
    "/api/tickets/waiting-input/bulk": _post_waiting_input_bulk,
    "/api/tickets/create": _post_ticket_create,
    "/api/tickets/update": _post_ticket_update,
    "/api/tickets/reorder": _post_ticket_reorder,
    "/api/remote/drive": _post_remote_drive,
}


def _handle_dashboard_get(handler: Any, config: ServeConfig) -> None:
    path = urlparse(handler.path).path
    if path in ("/", "/index.html"):
        handler._send(200, _load_dashboard_html().encode("utf-8"), "text/html; charset=utf-8")
        return
    if path == "/health":
        handler._send_json({"ok": True})
        return
    if path in ("/grid", "/api/mesh/frames", "/api/mesh/diagnostics"):
        from korumesh.dashboard import serve_mesh_http

        if serve_mesh_http(handler, path, project=config.project):
            return
    if path == "/capture/host":
        from korumesh.browser_capture import serve_browser_capture_http

        if serve_browser_capture_http(handler, path, project=config.project, method="GET"):
            return
    route = _GET_ROUTES.get(path)
    if route is not None:
        route(handler, config)
        return
    handler._send(404, b"not found")


def _handle_dashboard_post(handler: Any, config: ServeConfig) -> None:
    path = urlparse(handler.path).path
    try:
        body = handler._read_json_body()
    except Exception as exc:
        handler._send_json({"error": str(exc)}, status=400)
        return

    if path == "/api/mesh/browser-upload":
        from korumesh.browser_capture import serve_browser_capture_http

        if serve_browser_capture_http(
            handler,
            path,
            project=config.project,
            method="POST",
            body=body,
        ):
            return

    route = _POST_ROUTES.get(path)
    if route is not None:
        route(handler, config, body)
        return
    handler._send(404, b"not found")


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

        def do_GET(self) -> None:  # noqa: N802 — stdlib API
            _handle_dashboard_get(self, config)

        def do_POST(self) -> None:  # noqa: N802 — stdlib API
            _handle_dashboard_post(self, config)

    return _Handler


def build_dashboard_handler(config: ServeConfig) -> type[BaseHTTPRequestHandler]:
    """Build and return a DashboardRequestHandler subclass for the dashboard."""
    return _build_dashboard_handler_impl(config)
