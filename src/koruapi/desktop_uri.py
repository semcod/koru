"""Bridge Koru MCP to nlp2uri — NL → URI → OS desktop actions."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

_NLP2URI_IMPORT_ERROR: str | None = None

try:
    from nlp2uri.models import HostPlatform
    from nlp2uri.service import NLP2URIService

    _NLP2URI_AVAILABLE = True
except ImportError as exc:
    _NLP2URI_AVAILABLE = False
    _NLP2URI_IMPORT_ERROR = str(exc)
    HostPlatform = None  # type: ignore[assignment,misc]
    NLP2URIService = None  # type: ignore[assignment,misc]


def nlp2uri_available() -> bool:
    return _NLP2URI_AVAILABLE


def nlp2uri_missing_message() -> str:
    if _NLP2URI_IMPORT_ERROR:
        return (
            "nlp2uri is not installed "
            f"({_NLP2URI_IMPORT_ERROR}). "
            "Install with: pip install 'koru[desktop]' or pip install 'nlp2uri>=0.3'"
        )
    return "nlp2uri is not installed. Install with: pip install 'koru[desktop]'"


def _resolve_platform(name: str | None) -> Any:
    if not name:
        return None
    return HostPlatform(name)


def _intent_ir_metadata(prompt: str) -> dict[str, Any] | None:
    if os.getenv("NLP2CMD_INTEGRATION", "0") != "1":
        return None
    try:
        from nlpshim.client import analyze_text_structure
    except ImportError:
        return None
    structure = analyze_text_structure(prompt, include_plan=False)
    if not structure:
        return None
    return {"intent_ir": structure.get("intent_ir"), "source": "nlp2cmd-intent"}


def desktop_uri_plan(
    prompt: str,
    *,
    platform: str | None = None,
    locale: str | None = None,
) -> dict[str, Any]:
    """Resolve NL prompt to abstract URI + compiled OS actions."""
    if not _NLP2URI_AVAILABLE:
        return {"ok": False, "error": nlp2uri_missing_message()}

    host = _resolve_platform(platform)
    service = NLP2URIService.for_platform(host) if host else NLP2URIService.default()
    plan = service.from_prompt(prompt, locale=locale)
    payload: dict[str, Any] = {
        "ok": True,
        "prompt": prompt,
        "platform": service._host().value,
        "plan": plan.to_dict(),
    }
    intent_ir = _intent_ir_metadata(prompt)
    if intent_ir:
        payload["nlp_bridge"] = intent_ir
    return payload


def _portal_capture_enabled(explicit: bool | None) -> bool:
    if explicit is not None:
        return explicit
    return os.getenv("KORU_PORTAL_CAPTURE", "1").strip().lower() not in {"0", "false", "no"}


def _is_screen_capture_uri(uri: str) -> bool:
    return uri.startswith("desktop-screenshot://screen")


def _capture_via_portal(uri: str) -> dict[str, Any] | None:
    try:
        from koruvision.capture_mss import is_wayland
        from koruvision.portal_capture import PortalCaptureError, capture_portal_png
    except ImportError:
        return None

    if not is_wayland():
        return None

    out_dir = Path(os.environ.get("NLP2URI_CAPTURE_DIR", "/tmp/nlp2uri-captures"))
    out_dir.mkdir(parents=True, exist_ok=True)
    outfile = out_dir / "capture-screen-portal.png"
    try:
        png = capture_portal_png()
    except PortalCaptureError as exc:
        return {"ok": False, "uri": uri, "error": str(exc), "method": "xdg-portal"}

    outfile.write_bytes(png)
    return {
        "ok": True,
        "uri": uri,
        "output": str(outfile),
        "returncode": 0,
        "method": "xdg-portal",
        "capture_path": str(outfile),
        "bytes": len(png),
    }


def desktop_uri_handle(
    prompt: str,
    *,
    platform: str | None = None,
    locale: str | None = None,
    dry_run: bool = True,
    use_portal_capture: bool | None = None,
) -> dict[str, Any]:
    """Plan + execute desktop actions (dry-run by default)."""
    if not _NLP2URI_AVAILABLE:
        return {"ok": False, "error": nlp2uri_missing_message()}

    host = _resolve_platform(platform)
    service = NLP2URIService.for_platform(host) if host else NLP2URIService.default()
    plan = service.from_prompt(prompt, locale=locale)

    if (
        not dry_run
        and _portal_capture_enabled(use_portal_capture)
        and _is_screen_capture_uri(plan.uri)
    ):
        portal_result = _capture_via_portal(plan.uri)
        if portal_result is not None:
            payload: dict[str, Any] = {
                "prompt": prompt,
                "platform": service._host().value,
                "plan": plan.to_dict(),
                "result": portal_result,
            }
            intent_ir = _intent_ir_metadata(prompt)
            if intent_ir:
                payload["nlp_bridge"] = intent_ir
            return payload

    result = service.execute(plan.uri, dry_run=dry_run)
    payload = {
        "prompt": prompt,
        "platform": service._host().value,
        "plan": plan.to_dict(),
        "result": result.to_dict(),
    }
    intent_ir = _intent_ir_metadata(prompt)
    if intent_ir:
        payload["nlp_bridge"] = intent_ir
    return payload


def _service() -> Any:
    if not _NLP2URI_AVAILABLE:
        raise RuntimeError(nlp2uri_missing_message())
    return NLP2URIService.default()


def desktop_uri_list_getv(*, getv_home: str | None = None) -> dict[str, Any]:
    """List getv:// URIs from ~/.getv profiles."""
    if not _NLP2URI_AVAILABLE:
        return {"ok": False, "error": nlp2uri_missing_message()}
    try:
        payload = _service().list_getv_uris(getv_home=getv_home)
        return {"ok": True, **payload}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def desktop_uri_resolve_getv(prompt: str, *, getv_home: str | None = None) -> dict[str, Any]:
    """Resolve NL prompt to getv:// env var URI."""
    if not _NLP2URI_AVAILABLE:
        return {"ok": False, "error": nlp2uri_missing_message()}
    try:
        payload = _service().resolve_getv(prompt, getv_home=getv_home)
        return {"ok": payload.get("uri") is not None, **payload}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def desktop_uri_get_getv_var(uri: str) -> dict[str, Any]:
    """Read masked metadata for getv://category/profile/VAR."""
    if not _NLP2URI_AVAILABLE:
        return {"ok": False, "error": nlp2uri_missing_message()}
    try:
        payload = _service().read_getv_var(uri)
        return {"ok": bool(payload.get("found")), **payload}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def desktop_uri_resolve_system_map(
    prompt: str,
    *,
    doql_path: str | None = None,
    example_dir: str | None = None,
    example_id: str | None = None,
    system_map: dict[str, Any] | None = None,
    fallback_desktop: bool = True,
    platform: str | None = None,
) -> dict[str, Any]:
    """Resolve NL against env2llm SystemMap URIs (command://, runtime://, …)."""
    if not _NLP2URI_AVAILABLE:
        return {"ok": False, "error": nlp2uri_missing_message()}
    try:
        from nlp2uri.systemmap.context import load_ir_from_arguments

        ir = load_ir_from_arguments({
            "doql_path": doql_path,
            "example_dir": example_dir,
            "example_id": example_id,
            "system_map": system_map,
        })
        host = _resolve_platform(platform)
        service = NLP2URIService.for_platform(host) if host else NLP2URIService.default()
        payload = service.resolve_system_map(
            prompt,
            ir,
            fallback_desktop=fallback_desktop,
        )
        return {"ok": payload.get("uri") is not None, **payload}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def desktop_uri_list_system_uris(
    *,
    doql_path: str | None = None,
    example_dir: str | None = None,
    example_id: str | None = None,
    system_map: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """List command:// / runtime:// URIs from env2llm SystemMapIR."""
    if not _NLP2URI_AVAILABLE:
        return {"ok": False, "error": nlp2uri_missing_message()}
    try:
        from nlp2uri.systemmap.context import load_ir_from_arguments

        ir = load_ir_from_arguments({
            "doql_path": doql_path,
            "example_dir": example_dir,
            "example_id": example_id,
            "system_map": system_map,
        })
        payload = _service().list_system_uris(ir)
        return {"ok": True, **payload}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}
