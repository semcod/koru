"""Route handlers for the coru supervisor HTTP control plane."""

from __future__ import annotations

from http.server import BaseHTTPRequestHandler
from urllib.parse import unquote

from coru.supervisor.http_util import json_response, lanes_payload, read_json_body
from coru.supervisor.registry import load_registry, register_lane, remove_lane, set_active_lane
from coru.supervisor.service import SupervisorService


def _normalize_path(path: str) -> str:
    return path.rstrip("/") or "/"


def _lane_instance_from_suffix(path: str, suffix: str) -> str:
    return unquote(path.removeprefix("/api/lanes/").removesuffix(suffix))


def handle_get_health(handler: BaseHTTPRequestHandler, service: SupervisorService) -> None:
    json_response(
        handler,
        200,
        {
            "ok": True,
            "pid": service.pid,
            "url": service.url,
            "active_lane": load_registry(path=service.registry_path).active_lane,
        },
    )


def handle_get_lanes(handler: BaseHTTPRequestHandler, service: SupervisorService) -> None:
    registry = load_registry(path=service.registry_path)
    json_response(handler, 200, lanes_payload(registry))


def handle_get_active_lane(handler: BaseHTTPRequestHandler, service: SupervisorService) -> None:
    registry = load_registry(path=service.registry_path)
    record = registry.active_record()
    if record is None:
        json_response(handler, 404, {"ok": False, "error": "no active lane"})
        return
    json_response(handler, 200, {"ok": True, "lane": record.to_dict()})


def handle_get_lane_health(
    handler: BaseHTTPRequestHandler,
    service: SupervisorService,
    *,
    instance: str,
) -> None:
    registry = load_registry(path=service.registry_path)
    record = registry.lanes.get(instance)
    if record is None:
        json_response(handler, 404, {"ok": False, "error": f"unknown lane: {instance}"})
        return
    health = service.refresh_lane_health(record)
    json_response(handler, 200, {"ok": True, "lane": instance, "health": health.to_dict()})


def handle_put_active_lane(handler: BaseHTTPRequestHandler, service: SupervisorService) -> None:
    body = read_json_body(handler)
    instance = str(body.get("instance") or "").strip()
    if not instance:
        json_response(handler, 400, {"ok": False, "error": "instance required"})
        return
    try:
        record = set_active_lane(instance, path=service.registry_path)
    except KeyError as exc:
        json_response(handler, 404, {"ok": False, "error": str(exc)})
        return
    json_response(handler, 200, {"ok": True, "lane": record.to_dict()})


def handle_post_register_lane(handler: BaseHTTPRequestHandler, service: SupervisorService) -> None:
    body = read_json_body(handler)
    ide = str(body.get("ide") or "").strip().lower()
    instance = str(body.get("instance") or "").strip()
    if not ide or not instance:
        json_response(handler, 400, {"ok": False, "error": "ide and instance required"})
        return
    record = register_lane(
        ide=ide,
        instance=instance,
        project=str(body.get("project") or "").strip() or None,
        set_active=bool(body.get("set_active", False)),
        editor_cli=str(body.get("editor_cli") or "").strip() or None,
        path=service.registry_path,
    )
    json_response(handler, 200, {"ok": True, "lane": record.to_dict()})


def handle_post_lane_daemon(
    handler: BaseHTTPRequestHandler,
    service: SupervisorService,
    *,
    instance: str,
    start: bool,
) -> None:
    ok, detail = (
        service.start_lane_daemon(instance)
        if start
        else service.stop_lane_daemon(instance)
    )
    status = 200 if ok else 500
    json_response(handler, status, {"ok": ok, "detail": detail, "instance": instance})


def handle_post_lane_reconnect(
    handler: BaseHTTPRequestHandler,
    service: SupervisorService,
    *,
    instance: str,
) -> None:
    ok, detail = service.reconnect_lane(instance)
    status = 200 if ok else 500
    json_response(handler, status, {"ok": ok, "detail": detail, "instance": instance})


def handle_post_refresh(handler: BaseHTTPRequestHandler, service: SupervisorService) -> None:
    service.refresh_all_health()
    registry = load_registry(path=service.registry_path)
    json_response(handler, 200, {"ok": True, **lanes_payload(registry)})


def handle_delete_lane(
    handler: BaseHTTPRequestHandler,
    service: SupervisorService,
    *,
    instance: str,
) -> None:
    if not instance or "/" in instance:
        json_response(handler, 400, {"ok": False, "error": "invalid instance"})
        return
    removed = remove_lane(instance, path=service.registry_path)
    if not removed:
        json_response(handler, 404, {"ok": False, "error": f"unknown lane: {instance}"})
        return
    json_response(handler, 200, {"ok": True, "removed": instance})


def dispatch_get(handler: BaseHTTPRequestHandler, service: SupervisorService, path: str) -> bool:
    normalized = _normalize_path(path)
    if normalized == "/api/health":
        handle_get_health(handler, service)
        return True
    if normalized == "/api/lanes":
        handle_get_lanes(handler, service)
        return True
    if normalized == "/api/lanes/active":
        handle_get_active_lane(handler, service)
        return True
    if normalized.startswith("/api/lanes/") and normalized.endswith("/health"):
        instance = _lane_instance_from_suffix(normalized, "/health")
        handle_get_lane_health(handler, service, instance=instance)
        return True
    return False


def dispatch_put(handler: BaseHTTPRequestHandler, service: SupervisorService, path: str) -> bool:
    normalized = _normalize_path(path)
    if normalized == "/api/lanes/active":
        handle_put_active_lane(handler, service)
        return True
    return False


def dispatch_post(handler: BaseHTTPRequestHandler, service: SupervisorService, path: str) -> bool:
    normalized = _normalize_path(path)
    if normalized == "/api/lanes":
        handle_post_register_lane(handler, service)
        return True
    if normalized.startswith("/api/lanes/") and normalized.endswith("/daemon/start"):
        instance = _lane_instance_from_suffix(normalized, "/daemon/start")
        handle_post_lane_daemon(handler, service, instance=instance, start=True)
        return True
    if normalized.startswith("/api/lanes/") and normalized.endswith("/daemon/stop"):
        instance = _lane_instance_from_suffix(normalized, "/daemon/stop")
        handle_post_lane_daemon(handler, service, instance=instance, start=False)
        return True
    if normalized.startswith("/api/lanes/") and normalized.endswith("/reconnect"):
        instance = _lane_instance_from_suffix(normalized, "/reconnect")
        handle_post_lane_reconnect(handler, service, instance=instance)
        return True
    if normalized == "/api/refresh":
        handle_post_refresh(handler, service)
        return True
    return False


def dispatch_delete(handler: BaseHTTPRequestHandler, service: SupervisorService, path: str) -> bool:
    normalized = _normalize_path(path)
    if normalized.startswith("/api/lanes/"):
        instance = unquote(normalized.removeprefix("/api/lanes/"))
        handle_delete_lane(handler, service, instance=instance)
        return True
    return False
