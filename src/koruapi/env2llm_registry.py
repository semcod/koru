"""Bridge Koru MCP to env2llm live registry (REST/MQTT-backed service layer)."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

_ENV2LLM_IMPORT_ERROR: str | None = None

try:
    from env2llm.service.registry_service import RegistryService

    _ENV2LLM_AVAILABLE = True
except ImportError as exc:
    _ENV2LLM_AVAILABLE = False
    _ENV2LLM_IMPORT_ERROR = str(exc)
    RegistryService = None  # type: ignore[assignment,misc]

_SERVICE_CACHE: dict[tuple[str, str], Any] = {}


def env2llm_available() -> bool:
    return _ENV2LLM_AVAILABLE


def env2llm_missing_message() -> str:
    if _ENV2LLM_IMPORT_ERROR:
        return (
            f"env2llm is not installed ({_ENV2LLM_IMPORT_ERROR}). "
            "Install with: pip install 'koru[desktop]' or pip install 'env2llm>=0.1.5'"
        )
    return "env2llm is not installed. Install with: pip install 'koru[desktop]'"


def _resolve_project_dir(
    *,
    project_dir: str | None = None,
    project_root: str | None = None,
) -> Path:
    raw = (
        project_dir
        or project_root
        or os.environ.get("ENV2LLM_PROJECT_DIR")
        or os.environ.get("KORU_PROJECT_ROOT")
        or "."
    )
    return Path(raw).resolve()


def _desktop_probe_default(explicit: bool | None) -> bool | None:
    if explicit is not None:
        return explicit
    flag = os.environ.get("ENV2LLM_DESKTOP_PROBE", "").strip().lower()
    if flag in {"1", "true", "yes"}:
        return True
    if flag in {"0", "false", "no"}:
        return False
    return None


def _get_service(
    *,
    project_dir: str | None = None,
    project_root: str | None = None,
    project_id: str | None = None,
    probe_desktop: bool | None = None,
    mqtt: bool | None = None,
) -> Any:
    if not _ENV2LLM_AVAILABLE:
        raise RuntimeError(env2llm_missing_message())

    root = _resolve_project_dir(project_dir=project_dir, project_root=project_root)
    pid = project_id or root.name
    probe_desktop = _desktop_probe_default(probe_desktop)
    key = (str(root), pid)
    if key not in _SERVICE_CACHE:
        from env2llm.integrators._service_factory import build_registry_service

        _SERVICE_CACHE[key] = build_registry_service(
            root,
            project_id=pid,
            probe_desktop=probe_desktop,
            mqtt=mqtt,
        )
    service = _SERVICE_CACHE[key]
    if probe_desktop is not None:
        service.probe_desktop = probe_desktop
    return service


def env2llm_get_registry(
    *,
    project_dir: str | None = None,
    project_root: str | None = None,
    project_id: str | None = None,
    refresh: bool = False,
) -> dict[str, Any]:
    """Return live SystemMapIR as JSON."""
    if not _ENV2LLM_AVAILABLE:
        return {"ok": False, "error": env2llm_missing_message()}
    try:
        service = _get_service(
            project_dir=project_dir,
            project_root=project_root,
            project_id=project_id,
        )
        registry = service.to_dict(refresh=refresh)
        return {
            "ok": True,
            "project_id": service.project_id,
            "registry": registry,
        }
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def env2llm_render_registry(
    *,
    project_dir: str | None = None,
    project_root: str | None = None,
    project_id: str | None = None,
    fmt: str = "json",
    refresh: bool = False,
) -> dict[str, Any]:
    """Render registry as doql.less, yaml, json, or markdown."""
    if not _ENV2LLM_AVAILABLE:
        return {"ok": False, "error": env2llm_missing_message()}
    try:
        service = _get_service(
            project_dir=project_dir,
            project_root=project_root,
            project_id=project_id,
        )
        content = service.render(fmt, refresh=refresh)
        return {
            "ok": True,
            "project_id": service.project_id,
            "format": fmt,
            "content": content,
        }
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def env2llm_refresh_registry(
    *,
    project_dir: str | None = None,
    project_root: str | None = None,
    project_id: str | None = None,
    output_format: str = "doql.less",
    probe_desktop: bool | None = None,
    publish_mqtt: bool = True,
) -> dict[str, Any]:
    """Regenerate and persist environment.*; optional MQTT publish."""
    if not _ENV2LLM_AVAILABLE:
        return {"ok": False, "error": env2llm_missing_message()}
    try:
        service = _get_service(
            project_dir=project_dir,
            project_root=project_root,
            project_id=project_id,
            probe_desktop=probe_desktop,
            mqtt=publish_mqtt,
        )
        ir = service.refresh(
            publish_mqtt=publish_mqtt,
            output_format=output_format,
        )
        path = service.registry_path()
        return {
            "ok": True,
            "project_id": service.project_id,
            "example_id": ir.example_id,
            "path": str(path) if path else None,
            "command_count": len(ir.commands),
        }
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def env2llm_sync_after_calibration(
    *,
    project_dir: str | None = None,
    project_root: str | None = None,
    project_id: str | None = None,
) -> dict[str, Any]:
    """Refresh env2llm registry after OS-injector calibration (desktop + ide anchors)."""
    if not _ENV2LLM_AVAILABLE:
        return {"ok": False, "error": env2llm_missing_message()}
    try:
        service = _get_service(
            project_dir=project_dir,
            project_root=project_root,
            project_id=project_id,
            probe_desktop=True,
        )
        service.refresh(write=True, publish_mqtt=False)
        registry_path = service.registry_path()
        desktop = service.desktop_payload()
        calibrations = (desktop or {}).get("ide_calibrations") or []

        # Auto-validate calibrations after sync
        from koruapi.calibration_validator import validate_calibrations

        validation = validate_calibrations(desktop)

        result: dict[str, Any] = {
            "ok": True,
            "project_id": service.project_id,
            "registry_path": str(registry_path) if registry_path else None,
            "ide_calibration_count": len(calibrations),
            "ide_calibrations": calibrations,
        }
        if not validation.get("ok", True):
            result["validation"] = validation
        return result
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def env2llm_get_desktop(
    *,
    project_dir: str | None = None,
    project_root: str | None = None,
    project_id: str | None = None,
    refresh: bool = False,
) -> dict[str, Any]:
    """Live desktop probe slice (windows, session, displays)."""
    if not _ENV2LLM_AVAILABLE:
        return {"ok": False, "error": env2llm_missing_message()}
    try:
        service = _get_service(
            project_dir=project_dir,
            project_root=project_root,
            project_id=project_id,
        )
        return {
            "ok": True,
            "project_id": service.project_id,
            "desktop": service.desktop_payload(refresh=refresh),
        }
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def env2llm_validate_calibration(
    *,
    project_dir: str | None = None,
    project_root: str | None = None,
    project_id: str | None = None,
    ide: str | None = None,
    refresh: bool = False,
) -> dict[str, Any]:
    """Validate IDE calibrations against desktop display geometry.

    Checks each calibration for:
    - Position at extreme top of display (< 2% → error, < 5% → warning)
    - Position at extreme bottom (> 98% → warning)
    - Pointer–display mismatch (mouse on different screen)
    - Stale calibration (> 48h)
    """
    if not _ENV2LLM_AVAILABLE:
        return {"ok": False, "error": env2llm_missing_message()}
    try:
        service = _get_service(
            project_dir=project_dir,
            project_root=project_root,
            project_id=project_id,
        )
        desktop = service.desktop_payload(refresh=refresh)

        from koruapi.calibration_validator import validate_calibrations

        result = validate_calibrations(desktop, ide_filter=ide)
        result["project_id"] = service.project_id
        return result
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def env2llm_list_commands(
    *,
    project_dir: str | None = None,
    project_root: str | None = None,
    project_id: str | None = None,
    refresh: bool = False,
) -> dict[str, Any]:
    """List command schemas from the live registry."""
    if not _ENV2LLM_AVAILABLE:
        return {"ok": False, "error": env2llm_missing_message()}
    try:
        service = _get_service(
            project_dir=project_dir,
            project_root=project_root,
            project_id=project_id,
        )
        return {
            "ok": True,
            "project_id": service.project_id,
            "commands": service.commands_payload(refresh=refresh),
        }
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def env2llm_list_uris(
    *,
    project_dir: str | None = None,
    project_root: str | None = None,
    project_id: str | None = None,
    refresh: bool = False,
) -> dict[str, Any]:
    """nlp2uri URI index over registry (command://, desktop-window://, …)."""
    if not _ENV2LLM_AVAILABLE:
        return {"ok": False, "error": env2llm_missing_message()}
    try:
        service = _get_service(
            project_dir=project_dir,
            project_root=project_root,
            project_id=project_id,
        )
        payload = service.uris_payload(refresh=refresh)
        payload.setdefault("project_id", service.project_id)
        return payload
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def env2llm_mqtt_status(
    *,
    project_dir: str | None = None,
    project_root: str | None = None,
    project_id: str | None = None,
) -> dict[str, Any]:
    """MQTT bridge connection status for the registry service."""
    if not _ENV2LLM_AVAILABLE:
        return {"ok": False, "error": env2llm_missing_message()}
    try:
        service = _get_service(
            project_dir=project_dir,
            project_root=project_root,
            project_id=project_id,
        )
        return {"ok": True, **service.mqtt_status()}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}
