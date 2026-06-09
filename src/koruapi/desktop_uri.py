"""Bridge Koru MCP to nlp2uri — NL → URI → OS desktop actions."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

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


def _imgl_plan_payload(prompt: str) -> dict[str, Any]:
    return {
        "ok": True,
        "prompt": prompt,
        "suggested_transport": "imgl",
        "transport": "imgl",
        "plan": {
            "uri": f"imgl://ui/action?prompt={prompt}",
            "intent": "ui_action",
            "transport": "imgl",
        },
    }


def desktop_uri_plan(
    prompt: str,
    *,
    platform: str | None = None,
    locale: str | None = None,
    transport: str | None = None,
) -> dict[str, Any]:
    """Resolve NL prompt to abstract URI + compiled OS actions."""
    from koru.integrations.imgl_client import is_ui_prompt

    if (transport or "").strip().lower() == "imgl":
        return _imgl_plan_payload(prompt)

    if not _NLP2URI_AVAILABLE:
        if is_ui_prompt(prompt):
            return _imgl_plan_payload(prompt)
        return {"ok": False, "error": nlp2uri_missing_message()}

    host = _resolve_platform(platform)
    service = NLP2URIService.for_platform(host) if host else NLP2URIService.default()
    try:
        plan = service.from_prompt(prompt, locale=locale)
    except (ValueError, RuntimeError) as exc:
        if is_ui_prompt(prompt):
            return _imgl_plan_payload(prompt)
        return {"ok": False, "error": str(exc), "prompt": prompt}
    plan_dict = plan.to_dict()
    payload: dict[str, Any] = {
        "ok": True,
        "prompt": prompt,
        "platform": service._host().value,
        "plan": plan_dict,
    }
    control_plan = plan_dict.get("control_plan")
    if control_plan:
        payload["control_plan"] = control_plan
        payload["control_surface"] = _control_surface_hint(plan.uri)
    intent_ir = _intent_ir_metadata(prompt)
    if intent_ir:
        payload["nlp_bridge"] = intent_ir
    if is_ui_prompt(prompt):
        payload["suggested_transport"] = "imgl"
    return payload


def _control_surface_hint(uri: str) -> str | None:
    if uri.startswith("ide-chat://"):
        return "ide_chat"
    if uri.startswith("ide-command://"):
        return "ide_command"
    if uri.startswith("koru-control://"):
        return "koru_control"
    if uri.startswith("ide://"):
        return "ide"
    return None


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


def desktop_uri_control_plan(
    prompt: str,
    *,
    platform: str | None = None,
    locale: str | None = None,
) -> dict[str, Any]:
    """Resolve NL prompt to a Koru IDE control plan (koru.control.v1)."""
    payload = desktop_uri_plan(prompt, platform=platform, locale=locale)
    if not payload.get("ok"):
        return payload
    control_plan = payload.get("control_plan") or payload.get("plan", {}).get("control_plan")
    if not control_plan:
        payload["control_plan"] = None
        payload["control_error"] = "prompt did not resolve to an IDE control URI"
        return payload
    payload["control_plan"] = control_plan
    return payload


def desktop_uri_list_koru_ide_uris(
    status: dict[str, Any],
    *,
    socket_path: str | None = None,
) -> dict[str, Any]:
    """Build URI index from Koru autopilot status payload."""
    if not _NLP2URI_AVAILABLE:
        return {"ok": False, "error": nlp2uri_missing_message()}

    host = _resolve_platform(None)
    service = NLP2URIService.for_platform(host) if host else NLP2URIService.default()
    payload = service.list_koru_ide_uris(status, socket_path=socket_path or "")
    payload["ok"] = True
    return payload


def desktop_uri_direct_ide_chat_execute(
    message: str,
    *,
    ide: str,
    submit: bool = True,
    require_plugin: bool = False,
    workspace: str = "",
    dry_run: bool = True,
    client_factory: Any = None,
) -> dict[str, Any]:
    """Drive IDE chat without NL parsing (prompt is the message body)."""
    if not _NLP2URI_AVAILABLE:
        return {"ok": False, "error": nlp2uri_missing_message()}

    from nlp2uri.control_execute import compile_and_execute_control_uri
    from nlp2uri.schemes.util import abstract_url

    params: dict[str, str] = {
        "submit": "true" if submit else "false",
        "require_plugin": "true" if require_plugin else "false",
    }
    if workspace:
        params["workspace"] = workspace
    if submit and ide.strip().lower() == "cursor":
        params["strategy_hint"] = "submit_alt_glass_first"
    uri = abstract_url("ide-chat", ide, "/send", params=params)
    result = compile_and_execute_control_uri(
        uri,
        text=message,
        dry_run=dry_run,
        client_factory=client_factory,
    )
    return {
        "ok": bool(result.get("ok")),
        "prompt": message,
        "uri": uri,
        "control_plan": result.get("plan"),
        "execution": result,
        "drive_mode": "direct",
    }


def _control_uri_with_runtime_overrides(
    uri: str,
    *,
    ide: str | None = None,
    submit: bool = True,
    workspace: str = "",
    strategy_hint: str = "",
) -> str:
    """Apply explicit runtime lane overrides to an nlp2uri control URI."""
    parsed = urlsplit(uri)
    scheme = parsed.scheme.lower()
    if scheme not in {"ide-chat", "koru-control"}:
        return uri

    query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    netloc = parsed.netloc
    if ide:
        if scheme == "ide-chat":
            netloc = ide
        else:
            query["ide"] = ide
    if workspace:
        query["workspace"] = workspace
    if submit is False:
        query["submit"] = "false"
    lane = (ide or netloc or query.get("ide") or "").strip().lower()
    hint = strategy_hint or (
        "submit_alt_glass_first" if submit and lane == "cursor" else ""
    )
    if hint:
        query["strategy_hint"] = hint

    return urlunsplit((parsed.scheme, netloc, parsed.path, urlencode(query), parsed.fragment))


def desktop_uri_control_execute(
    prompt: str,
    *,
    platform: str | None = None,
    locale: str | None = None,
    dry_run: bool = True,
    text: str | None = None,
    ide: str | None = None,
    submit: bool = True,
    workspace: str = "",
    client_factory: Any = None,
) -> dict[str, Any]:
    """Plan + execute IDE control via nlp2uri koruide driver."""
    if not _NLP2URI_AVAILABLE:
        return {"ok": False, "error": nlp2uri_missing_message()}

    from nlp2uri.control_execute import compile_and_execute_control_uri

    plan_payload = desktop_uri_control_plan(prompt, platform=platform, locale=locale)
    if not plan_payload.get("ok"):
        if ide:
            message = (text or prompt).strip()
            if message:
                return desktop_uri_direct_ide_chat_execute(
                    message,
                    ide=ide,
                    submit=submit,
                    workspace=workspace,
                    dry_run=dry_run,
                    client_factory=client_factory,
                )
        return plan_payload
    control_plan = plan_payload.get("control_plan")
    if not control_plan:
        if ide:
            message = (text or prompt).strip()
            if message:
                return desktop_uri_direct_ide_chat_execute(
                    message,
                    ide=ide,
                    submit=submit,
                    workspace=workspace,
                    dry_run=dry_run,
                    client_factory=client_factory,
                )
        return {
            "ok": False,
            "error": plan_payload.get("control_error", "no control plan"),
            "plan": plan_payload.get("plan"),
        }
    uri = _control_uri_with_runtime_overrides(
        plan_payload["plan"]["uri"],
        ide=ide,
        submit=submit,
        workspace=workspace,
    )
    text_ref = text
    if not text_ref:
        meta = plan_payload.get("plan", {}).get("spec", {}).get("metadata", {})
        if isinstance(meta, dict):
            text_ref = meta.get("text")
        if not text_ref and control_plan.get("actions"):
            text_ref = control_plan["actions"][0].get("text_ref")
    result = compile_and_execute_control_uri(
        uri,
        text=text_ref,
        dry_run=dry_run,
        client_factory=client_factory,
    )
    return {
        "ok": bool(result.get("ok")),
        "prompt": prompt,
        "uri": uri,
        "control_plan": result.get("plan") or control_plan,
        "execution": result,
        "drive_mode": "nlp",
    }


def desktop_uri_imgl_execute(
    prompt: str,
    *,
    image: str | None = None,
    window: str | None = None,
    dry_run: bool = True,
    execute: bool = True,
    with_diagnostics: bool | None = None,
) -> dict[str, Any]:
    """Execute a UI action via imgl vision catalog (TYPE / KEY / CLICK)."""
    from koru.integrations.imgl_client import execute_nl, imgl_available, imgl_missing_message

    if not imgl_available():
        return {"ok": False, "error": imgl_missing_message(), "transport": "imgl"}

    do_execute = execute and not dry_run
    result = execute_nl(
        prompt,
        image=image,
        window=window,
        execute=do_execute,
        dry_run=dry_run,
        with_diagnostics=with_diagnostics,
    )
    payload: dict[str, Any] = {
        "ok": bool(result.get("ok")),
        "prompt": prompt,
        "transport": "imgl",
        "result": result,
        "dry_run": dry_run,
    }
    if result.get("diagnostics"):
        payload["diagnostics"] = result["diagnostics"]
        payload["verdict"] = result["diagnostics"].get("verdict")
    return payload


def _should_route_to_imgl(
    prompt: str,
    *,
    transport: str | None = None,
) -> bool:
    if (transport or "").strip().lower() == "imgl":
        return True
    from koru.integrations.imgl_client import imgl_desktop_transport_enabled, is_ui_prompt

    if not imgl_desktop_transport_enabled():
        return False
    return is_ui_prompt(prompt)


def desktop_uri_handle(
    prompt: str,
    *,
    platform: str | None = None,
    locale: str | None = None,
    dry_run: bool = True,
    use_portal_capture: bool | None = None,
    transport: str | None = None,
    image: str | None = None,
    window: str | None = None,
) -> dict[str, Any]:
    """Plan + execute desktop actions (dry-run by default)."""
    if _should_route_to_imgl(prompt, transport=transport):
        return desktop_uri_imgl_execute(
            prompt,
            image=image,
            window=window,
            dry_run=dry_run,
            execute=not dry_run,
        )

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
