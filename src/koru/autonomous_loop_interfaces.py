"""Blocked-interface hints and dashboard action URLs for ``koru autonomous``."""

from __future__ import annotations

from typing import Any

from koru.autonomy.autopilot_status import parse_autopilot_status


def _blocked_by_from_autopilot_status(autopilot_status: str) -> str:
    return parse_autopilot_status(autopilot_status).blocker_code


def _is_plugin_blocker(blocked_by: str) -> bool:
    key = (blocked_by or "").strip().lower()
    return key.startswith("plugin_")


def _interface_matches_ide(interface_id: str, target_ide: str) -> bool:
    ide = (target_ide or "").strip().lower()
    if not ide or ide == "auto":
        return True
    if ide == "jetbrains":
        return "jetbrains" in interface_id
    if ide == "antigravity":
        return interface_id in {"plugin_socket_vscode_family", "antigravity_native_send"}
    if ide in {"cursor", "vscode", "vscodium", "windsurf"}:
        return interface_id == "plugin_socket_vscode_family"
    return True


def _blocked_interface_action_lines(
    blocked_by: str,
    *,
    autopilot_ide: str = "",
) -> list[str]:
    key = (blocked_by or "").strip()
    if not key:
        return []
    try:
        from koru.interface_registry import blocker_interface_payload

        payload = blocker_interface_payload(key)
    except Exception:
        return []
    items = _blocked_interface_items(payload)
    if not items:
        return []
    selected = _select_blocked_interface_items(items, autopilot_ide)
    return [_format_blocked_interface_line(item) for item in selected if item.get("id")]


def _blocked_interface_items(payload: dict[str, Any]) -> list[dict[str, Any]]:
    items = payload.get("interfaces")
    if not isinstance(items, list):
        return []
    return [item for item in items if isinstance(item, dict)]


def _select_blocked_interface_items(
    items: list[dict[str, Any]],
    autopilot_ide: str,
) -> list[dict[str, Any]]:
    matching_items = [
        item
        for item in items
        if _interface_matches_ide(str(item.get("id") or "").strip(), autopilot_ide)
    ]
    return (matching_items or items)[:2]


def _format_blocked_interface_line(item: dict[str, Any]) -> str:
    interface_id = str(item.get("id") or "").strip()
    return (
        f"[blocked interface] {interface_id}"
        f"{_blocked_interface_detail_suffix(item)}"
        f"{_blocked_interface_recovery_suffix(item)}"
    )


def _blocked_interface_detail_suffix(item: dict[str, Any]) -> str:
    details = [
        f"{key}={value}"
        for key in ("family", "transport")
        if (value := str(item.get(key) or "").strip())
    ]
    return f" ({', '.join(details)})" if details else ""


def _blocked_interface_recovery_suffix(item: dict[str, Any]) -> str:
    recovery = item.get("operator_recovery")
    if not isinstance(recovery, list):
        return ""
    steps = [str(step).strip() for step in recovery if str(step).strip()]
    return " ; recovery: " + " | ".join(steps[:2]) if steps else ""


def _dashboard_action_urls(project: Any) -> dict[str, str]:
    base = "http://127.0.0.1:8765"
    try:
        from pathlib import Path
        from urllib.parse import urlencode

        from koruapi.dashboard_serve import read_serve_endpoint

        endpoint = read_serve_endpoint(Path(project))
        if isinstance(endpoint, dict):
            raw_base = str(endpoint.get("http_base") or "").strip()
            if raw_base:
                base = raw_base.rstrip("/")
        query = urlencode({"project": str(Path(project).resolve())})
    except Exception:
        query = ""
    suffix = f"?{query}" if query else ""
    return {
        "dashboard": f"{base}/{suffix}",
        "create_project_ticket": f"{base}/llm/prompt/create-ticket-for-project{suffix}",
        "create_project_ticket_action": f"{base}/llm/action/create-ticket-for-project{suffix}",
        "tickets": f"{base}/?tab=tickets{('&' + query) if query else ''}",
    }


def _default_dashboard_action_urls() -> dict[str, str]:
    return {
        "dashboard": "http://127.0.0.1:8765/",
        "create_project_ticket": "http://127.0.0.1:8765/llm/prompt/create-ticket-for-project",
        "create_project_ticket_action": "http://127.0.0.1:8765/llm/action/create-ticket-for-project",
        "tickets": "http://127.0.0.1:8765/?tab=tickets",
    }


def _safe_dashboard_action_urls(project: Any | None) -> dict[str, str]:
    if project is None:
        return _default_dashboard_action_urls()
    try:
        # Late-bind through the runner facade so tests patching
        # ``autonomous_loop_runner._dashboard_action_urls`` still take effect.
        from koru import autonomous_loop_runner as _runner_mod

        return _runner_mod._dashboard_action_urls(project)
    except Exception:
        return _default_dashboard_action_urls()
