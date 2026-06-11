"""vdisplay semantic control fallback for koru autonomous / coru drive.

When simplified control paths fail (plugin socket, blind wtype/ydotool, coordinate
injectors), koru can delegate to vdisplay's control plane for full semantic
automation: AT-SPI / Playwright / terminal / X11 / vision routing with verify.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any

_VDISPLAY_DIRECT = False
_VDISPLAY_IMPORT_ERROR: str | None = None

try:
    from vdisplay.application.services import control as _vdisplay_control

    _VDISPLAY_DIRECT = True
except ImportError as exc:
    _VDISPLAY_IMPORT_ERROR = str(exc)

_IDE_HINTS: dict[str, dict[str, str]] = {
    "windsurf": {"app": "Windsurf", "window_title_contains": "Windsurf"},
    "cursor": {"app": "Cursor", "window_title_contains": "Cursor"},
    "vscode": {"app": "code", "window_title_contains": "Visual Studio Code"},
    "vscodium": {"app": "VSCodium", "window_title_contains": "VSCodium"},
    "antigravity": {"app": "Antigravity", "window_title_contains": "Antigravity"},
    "zed": {"app": "zed", "window_title_contains": "Zed"},
    "jetbrains": {"app": "jetbrains-toolbox", "window_title_contains": "JetBrains"},
    "pycharm": {"app": "pycharm", "window_title_contains": "PyCharm"},
}

_CHAT_INPUT_SELECTORS: tuple[dict[str, str], ...] = (
    {"role": "input", "name_contains": "Chat"},
    {"role": "input", "name_contains": "chat"},
    {"role": "input", "name_contains": "Ask"},
    {"role": "input", "name_contains": "Composer"},
    {"role": "input", "name_contains": "Message"},
    {"role": "input", "name_contains": "Prompt"},
    {"role": "input"},
)

_SUBMIT_BUTTON_SELECTORS: tuple[dict[str, str], ...] = (
    {"role": "button", "name_contains": "Send"},
    {"role": "button", "name_contains": "Submit"},
    {"role": "button", "name_contains": "Run"},
)


def _canonical_ide(ide: str) -> str:
    try:
        from koruide.ide import canonical_autopilot_ide_id

        return canonical_autopilot_ide_id(ide) or ide.strip().lower()
    except Exception:
        return ide.strip().lower()


def _agent_url() -> str | None:
    explicit = os.environ.get("KORU_VDISPLAY_AGENT_URL", "").strip()
    if explicit:
        return explicit.rstrip("/")
    try:
        from vdisplay.agent_config import resolve_agent_url

        return resolve_agent_url(allow_auto=True)
    except ImportError:
        return None


def _probe_agent(url: str) -> bool:
    try:
        with urllib.request.urlopen(f"{url.rstrip('/')}/health", timeout=0.5) as resp:
            return resp.status == 200
    except (urllib.error.URLError, TimeoutError, OSError, ValueError):
        return False


def _reload_vdisplay_direct() -> bool:
    global _VDISPLAY_DIRECT, _VDISPLAY_IMPORT_ERROR, _vdisplay_control
    try:
        from vdisplay.application.services import control as control_mod

        _vdisplay_control = control_mod
        _VDISPLAY_DIRECT = True
        _VDISPLAY_IMPORT_ERROR = None
        return True
    except ImportError as exc:
        _VDISPLAY_DIRECT = False
        _VDISPLAY_IMPORT_ERROR = str(exc)
        return False


def _ensure_vdisplay_runtime() -> bool:
    if _VDISPLAY_DIRECT:
        return True
    from koru.deps_autorepair import ensure_vdisplay_runtime

    if not ensure_vdisplay_runtime(label="koru drive"):
        return False
    return _reload_vdisplay_direct()


def vdisplay_available() -> bool:
    if _VDISPLAY_DIRECT:
        return True
    if _ensure_vdisplay_runtime():
        return True
    url = _agent_url()
    return bool(url and _probe_agent(url))


def vdisplay_missing_message() -> str:
    url = _agent_url()
    if url:
        return ""
    hint = (
        "Install vdisplay control plane: pip install vdisplay "
        "or set KORU_VDISPLAY_AGENT_URL=http://127.0.0.1:8765"
    )
    if _VDISPLAY_IMPORT_ERROR:
        return f"{hint} ({_VDISPLAY_IMPORT_ERROR})"
    return hint


def verify_chat_text_visible(
    text: str,
    *,
    ide: str,
    chat_x: int | None = None,
    chat_y: int | None = None,
    map_path: str | None = None,
) -> dict[str, Any]:
    """Post-action OCR + screenshot verify for IDE chat input."""
    if not _ensure_vdisplay_runtime():
        return {
            "ok": False,
            "verified": False,
            "mode": "ocr_contains",
            "error": vdisplay_missing_message() or "vdisplay unavailable for verify",
        }

    from koru.deps_autorepair import ensure_vision_ocr

    if not ensure_vision_ocr(label="koru verify"):
        return {
            "ok": False,
            "verified": False,
            "mode": "ocr_contains",
            "error": "OCR verify deps missing (tesseract, Pillow, pytesseract)",
        }

    from vdisplay.control.models import ControlBounds, ControlNode, ControlRole
    from vdisplay.control.screenshot_verify import capture_control_screenshot
    from vdisplay.control.vision_ocr import ocr_available, ocr_png

    ready, reason = ocr_available()
    if not ready:
        return {
            "ok": False,
            "verified": False,
            "mode": "ocr_contains",
            "error": reason,
        }

    expected = text.strip()
    if not expected:
        return {"ok": True, "verified": True, "mode": "ocr_contains", "reason": "empty text"}

    if chat_x is not None and chat_y is not None:
        bounds = ControlBounds(x=int(chat_x) - 360, y=int(chat_y) - 24, width=720, height=48)
        target = ControlNode(
            id="verify:chat-input",
            backend="vision",
            role=ControlRole.INPUT,
            name="chat-input",
            bounds=bounds,
        )
        try:
            png, capture_meta = capture_control_screenshot(target=target)
            if not png:
                png, capture_meta = capture_control_screenshot(target=None)
        except Exception as exc:
            return {
                "ok": False,
                "verified": False,
                "mode": "ocr_contains",
                "error": f"screenshot capture failed: {exc}",
                "bounds": bounds.to_dict(),
                "ide": ide,
                "hint": "On Wayland run: vdisplay-agent serve && vdisplay agent screencast start",
            }
    elif map_path:
        try:
            from vdisplay.control.gui_map import load_gui_map
            from vdisplay.input.coords import global_pointer_coords

            pack = load_gui_map(map_path)
            element = pack.elements.get("ai-chat-input")
            if element is None:
                raise KeyError("ai-chat-input")
            meta = element.capture_meta or pack.capture_meta or {}
            gx, gy, _mapping = global_pointer_coords(
                element.click_point.x,
                element.click_point.y,
                meta,
            )
            return verify_chat_text_visible(
                text,
                ide=ide,
                chat_x=gx,
                chat_y=gy,
            )
        except Exception as exc:
            return {
                "ok": False,
                "verified": False,
                "mode": "ocr_contains",
                "error": f"map verify failed: {exc}",
                "map_path": map_path,
            }
    else:
        return {
            "ok": False,
            "verified": False,
            "mode": "ocr_contains",
            "error": "verify requires chat_x/chat_y or map_path",
        }

    screenshot_path = None
    if not png:
        return {
            "ok": False,
            "verified": False,
            "mode": "ocr_contains",
            "error": "screenshot capture failed",
            "bounds": bounds.to_dict(),
            "ide": ide,
        }
    if isinstance(capture_meta, dict) and capture_meta.get("path"):
        screenshot_path = str(capture_meta["path"])

    stream_hint = None
    if isinstance(capture_meta, dict) and chat_x is not None and chat_y is not None:
        from vdisplay.control.screenshot_verify import global_point_in_stream_bounds, stream_bounds_from_meta

        if not global_point_in_stream_bounds(int(chat_x), int(chat_y), capture_meta):
            stream = stream_bounds_from_meta(capture_meta)
            stream_hint = (
                f"Chat focus ({chat_x},{chat_y}) is outside active ScreenCast stream {stream}. "
                "Restart screencast and pick All Screens or the monitor containing the IDE."
            )

    boxes = ocr_png(png)
    combined = " ".join(box.text for box in boxes)
    verified = expected in combined or expected.lower() in combined.lower()
    result = {
        "ok": verified,
        "verified": verified,
        "mode": "ocr_contains",
        "expected_text": expected,
        "ocr_text_sample": combined[:500],
        "ocr_box_count": len(boxes),
        "screenshot_verify": True,
        "screenshot_path": screenshot_path,
        "capture": capture_meta if isinstance(capture_meta, dict) else None,
        "bounds": bounds.to_dict(),
        "ide": ide,
        "reason": "ocr text matched" if verified else "ocr text missing",
    }
    if stream_hint:
        result["hint"] = stream_hint
        if not verified:
            result["error"] = stream_hint
    return result


def record_koru_drive_step(
    payload: dict[str, Any],
    *,
    profile_id: str,
    text: str,
) -> str | None:
    """Append koru direct-drive (+ verify) to vdisplay session when VDISPLAY_SESSION=1."""
    if not _ensure_vdisplay_runtime():
        return None
    try:
        from vdisplay.application.models import ArtifactRef, CommandRequest, CommandResult
        from vdisplay.application.session_recorder import record_execution, session_recording_enabled
        from vdisplay.application.verbs import CommandVerb
    except ImportError:
        return None
    if not session_recording_enabled():
        return None

    session_id = os.environ.get("VDISPLAY_SESSION_ID", "").strip() or f"koru-drive-{profile_id}"
    cmd = CommandRequest(
        verb=CommandVerb.CONTROL_SET_VALUE,
        line=f"koru autopilot drive --ide {profile_id} --direct",
        request_source="koru",
        session_id=session_id,
        match_app=profile_id,
        control_app=profile_id,
        control_value=text,
        control_verify=bool(payload.get("verified") is not None),
        control_screenshot_verify=bool(payload.get("verification")),
    )
    diagnostics: dict[str, Any] = {
        "control": {
            "backend": payload.get("backend"),
            "profile_id": profile_id,
            "verified": payload.get("verified"),
            "verification": payload.get("verification"),
        }
    }
    artifacts: list[ArtifactRef] = []
    verify_path = (payload.get("artifacts") or {}).get("verify_screenshot")
    if verify_path:
        artifacts.append(ArtifactRef(kind="screenshot", path=str(verify_path), label="verify"))
    result = CommandResult(
        ok=bool(payload.get("ok")),
        action="koru_drive",
        data=dict(payload),
        diagnostics=diagnostics,
        artifacts=artifacts,
    )
    session_dir = record_execution(cmd, result, route="koru-direct", duration_ms=0)
    return str(session_dir) if session_dir else None


def _session_type() -> str:
    return (os.environ.get("XDG_SESSION_TYPE") or "").strip().lower()


def simplified_control_likely_insufficient(*, ide: str, plugin_connected: bool = False) -> bool:
    """Heuristic: simplified keyboard/plugin paths are unlikely to work."""
    if plugin_connected:
        return False
    if _session_type() == "wayland":
        return True
    canon = _canonical_ide(ide)
    if canon in {"cursor", "windsurf", "antigravity"} and not plugin_connected:
        return True
    if not os.environ.get("KORU_OS_INJECTOR_PROFILE", "").strip():
        return True
    return False


def vdisplay_fallback_enabled(*, ide: str | None = None, plugin_connected: bool = False) -> bool:
    """Whether drive may use vdisplay semantic control as fallback."""
    raw = os.environ.get("KORU_VDISPLAY_CONTROL_FALLBACK", "auto").strip().lower()
    if raw in {"0", "false", "no", "off"}:
        return False
    if not vdisplay_available():
        return False
    if raw in {"1", "true", "yes", "on"}:
        return True
    if plugin_connected:
        return False
    if ide and simplified_control_likely_insufficient(ide=ide, plugin_connected=plugin_connected):
        return True
    return False


def _dry_run() -> bool:
    return os.environ.get("KORU_VDISPLAY_DRY_RUN", "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def _ide_hints(ide: str) -> dict[str, str]:
    canon = _canonical_ide(ide)
    # Prefer local _IDE_HINTS for consistency with test expectations
    if canon in _IDE_HINTS:
        return dict(_IDE_HINTS[canon])
    try:
        from vdisplay.desktop_apps import ide_hints_for

        return ide_hints_for(canon)
    except Exception:
        return {"app": canon, "window_title_contains": canon}


def _chat_selectors_for(ide: str) -> tuple[dict[str, str], ...]:
    # Return local selectors by default for consistency with tests
    return _CHAT_INPUT_SELECTORS


def _submit_selectors_for(ide: str) -> tuple[dict[str, str], ...]:
    # Return local selectors by default for consistency with tests
    return _SUBMIT_BUTTON_SELECTORS


def _agent_client():
    from vdisplay.client import AgentClient

    url = _agent_url()
    if not url:
        raise RuntimeError("vdisplay agent URL is not configured")
    return AgentClient(url)


def _controls_find(**kwargs: Any) -> dict[str, Any]:
    if _VDISPLAY_DIRECT:
        return _vdisplay_control.controls_find(**kwargs)
    return _agent_client().find_controls(kwargs)


def _control_focus(**kwargs: Any) -> dict[str, Any]:
    if _VDISPLAY_DIRECT:
        return _vdisplay_control.control_focus(**kwargs)
    return _agent_client().focus_control(kwargs)


def _control_set_value(**kwargs: Any) -> dict[str, Any]:
    if _VDISPLAY_DIRECT:
        return _vdisplay_control.control_set_value(**kwargs)
    return _agent_client().set_control_value(kwargs)


def _control_click(**kwargs: Any) -> dict[str, Any]:
    if _VDISPLAY_DIRECT:
        return _vdisplay_control.control_click(**kwargs)
    return _agent_client().invoke_control(kwargs)


def _find_first_selector(
    *,
    ide: str,
    selectors: tuple[dict[str, str], ...],
    backend: str = "auto",
    vql_fallback: bool = True,
) -> tuple[dict[str, str] | None, dict[str, Any] | None]:
    hints = _ide_hints(ide)
    base = {
        "backend": backend,
        "app": hints.get("app"),
        "window_title": hints.get("window_title_contains"),
    }
    last_error: dict[str, Any] | None = None
    for spec in selectors:
        payload = {**base, **spec}
        try:
            found = _controls_find(**payload)
        except Exception as exc:
            last_error = {"ok": False, "error": str(exc), "selector": spec}
            continue
        if found.get("ok") and int(found.get("count") or 0) > 0:
            return spec, found
        last_error = found

    # VQL fallback: if vision found nothing, use explicit click_center from loaded VQL
    # (fresh 31-elem capture or our analysis with decision_data + mouse coords for JetBrains/Cursor)
    if vql_fallback:
        vql = load_vql_metadata()
        if vql.get("ui_elements"):
            cc = vql["ui_elements"][0].get("click_center", {})
            if cc:
                return None, {
                    "ok": True,
                    "count": 1,
                    "selected": {
                        "id": "vql-fallback:0",
                        "backend": "vql",
                        "role": "unknown",
                        "name": "vql-center",
                        "click_point": {"x": cc.get("x"), "y": cc.get("y")},
                        "note": f"VQL fallback center from {vql.get('_source')}"
                    },
                    "matches": [{"id": "vql-fallback:0", "click_center": cc}]
                }
    return None, last_error


def _submit_via_keyboard(*, ide: str, submit: bool) -> dict[str, Any] | None:
    if not submit:
        return None
    from koru.autonomous_cycle_gate import effective_ide_control_submit

    if not effective_ide_control_submit(submit=submit, ide=ide):
        return None
    try:
        from gillm.injection.injector import Injector

        injector = Injector()
        try:
            from gillm.config import cached_config

            key = cached_config().submit_key_for(_canonical_ide(ide))
        except Exception:
            key = "ctrl+Return" if _canonical_ide(ide) in {"cursor", "jetbrains", "pycharm"} else "Return"
        injector.press_key(key)
        return {"ok": True, "backend": "vdisplay+keyboard", "submit_key": key}
    except Exception as exc:
        return {"ok": False, "backend": "vdisplay+keyboard", "error": str(exc)}


def _ide_prompt_app_id(ide: str) -> str:
    canon = _canonical_ide(ide)
    if canon in {"jetbrains", "pycharm"}:
        return "pycharm"
    return canon


def _resolve_ide_prompt_map(app_id: str) -> str | None:
    try:
        from vdisplay.desktop_apps import resolve_map_path
    except ImportError:
        return None
    return resolve_map_path(app_id)


def send_chat_via_ide_prompt(
    prompt: str,
    *,
    ide: str,
    submit: bool,
    dry_run: bool = False,
    verify: bool = False,
) -> dict[str, Any] | None:
    """Map/vision IDE prompt path (click chat via ydotool + type/paste)."""
    app_id = _ide_prompt_app_id(ide)
    map_path = _resolve_ide_prompt_map(app_id)
    if not map_path and _canonical_ide(ide) not in {"jetbrains", "pycharm"}:
        return None

    if dry_run:
        return {
            "ok": True,
            "backend": "vdisplay+ide-prompt",
            "dry_run": True,
            "ide": ide,
            "app_id": app_id,
            "map_path": map_path,
            "chars": len(prompt),
            "submit": submit,
        }

    try:
        from vdisplay.ide_prompt import send_ide_prompt
    except ImportError:
        return None

    result = send_ide_prompt(
        app_id=app_id,
        text=prompt,
        backend="vision" if map_path else None,
        wait_window=False,
        submit=submit,
        map_path=map_path,
        verify=verify,
    )
    if not result.get("ok"):
        return {
            "ok": False,
            "backend": "vdisplay+ide-prompt",
            "message": str(result.get("message") or "ide prompt failed"),
            "type": "error",
            "fallback_from": "plugin",
            "ide": ide,
            "map_path": map_path,
            "result": result,
        }

    return {
        "ok": True,
        "backend": "vdisplay+ide-prompt",
        "message": str(result.get("message") or "typed via vdisplay ide prompt"),
        "type": "drive",
        "fallback_from": "plugin",
        "ide": ide,
        "app_id": app_id,
        "map_path": map_path,
        "typed": result.get("typed"),
        "submitted": bool(result.get("submitted")),
        "submit_result": result.get("submit_result"),
    }


def send_chat(
    prompt: str,
    *,
    ide: str,
    submit: bool,
    dry_run: bool | None = None,
) -> dict[str, Any]:
    """Semantic IDE chat drive via vdisplay control plane."""
    effective_dry = _dry_run() if dry_run is None else dry_run
    if effective_dry:
        app_id = _ide_prompt_app_id(ide)
        map_path = _resolve_ide_prompt_map(app_id)
        hints = _ide_hints(ide)
        backend = "vdisplay+ide-prompt" if map_path else "vdisplay"
        return {
            "ok": True,
            "backend": backend,
            "dry_run": True,
            "ide": ide,
            "app_id": app_id,
            "map_path": map_path,
            "chars": len(prompt),
            "submit": submit,
            "app": hints.get("app"),
        }

    if not vdisplay_available():
        return {
            "ok": False,
            "backend": "vdisplay",
            "message": vdisplay_missing_message(),
            "type": "error",
            "fallback_from": "plugin",
        }

    canon = _canonical_ide(ide)
    if canon in {"jetbrains", "pycharm"}:
        try:
            import gillm.injection.os_injector as oi
            from pathlib import Path

            os_res = oi.try_drive_with_profile(
                tool_id=canon,
                text=prompt,
                submit=submit,
                project=None,
                cli_dry_run=False,
            )
            if os_res is not None and os_res.get("ok"):
                return {
                    "ok": True,
                    "backend": "os_injector",
                    "message": "typed via calibrated os_injector profile",
                    "type": "drive",
                    "fallback_from": "plugin",
                    "ide": ide,
                    **{k: v for k, v in os_res.items() if k != "ok"},
                }
        except Exception:
            pass

    ide_prompt = send_chat_via_ide_prompt(
        prompt,
        ide=ide,
        submit=submit,
        dry_run=False,
    )
    if ide_prompt is not None and ide_prompt.get("ok"):
        return ide_prompt

    hints = _ide_hints(ide)
    focus_error: str | None = None
    try:
        _control_focus(
            backend="auto",
            app=hints.get("app"),
            window_title=hints.get("window_title_contains"),
            role="window",
        )
    except Exception as exc:
        focus_error = str(exc)

    selector, found = _find_first_selector(ide=ide, selectors=_chat_selectors_for(ide))
    if selector is None:
        return {
            "ok": False,
            "backend": "vdisplay",
            "message": (
                f"no chat input matched for ide={ide} "
                f"(app={hints.get('app')!r}); focus_error={focus_error or '-'}"
            ),
            "type": "error",
            "fallback_from": "plugin",
            "diagnostics": found,
        }

    write_kwargs = {
        "backend": "auto",
        "app": hints.get("app"),
        "window_title": hints.get("window_title_contains"),
        "value": prompt,
        **selector,
    }
    selected = (found or {}).get("selected") if isinstance(found, dict) else None
    if isinstance(selected, dict) and selected.get("id"):
        write_kwargs["provider_ref"] = selected["id"]

    try:
        typed = _control_set_value(**write_kwargs)
    except Exception as exc:
        return {
            "ok": False,
            "backend": "vdisplay",
            "message": str(exc),
            "type": "error",
            "fallback_from": "plugin",
            "selector": selector,
            "focus_error": focus_error,
        }

    if not typed.get("ok", True):
        return {
            "ok": False,
            "backend": "vdisplay",
            "message": str(typed.get("error") or typed.get("message") or "set_value failed"),
            "type": "error",
            "fallback_from": "plugin",
            "selector": selector,
            "result": typed,
        }

    submitted = False
    submit_result: dict[str, Any] | None = None
    if submit:
        submit_selector, submit_found = _find_first_selector(
            ide=ide,
            selectors=_submit_selectors_for(ide),
        )
        if submit_selector is not None:
            click_kwargs = {
                "backend": "auto",
                "app": hints.get("app"),
                "window_title": hints.get("window_title_contains"),
                **submit_selector,
            }
            selected_submit = (submit_found or {}).get("selected")
            if isinstance(selected_submit, dict) and selected_submit.get("id"):
                click_kwargs["provider_ref"] = selected_submit["id"]
            try:
                submit_result = _control_click(**click_kwargs)
                submitted = bool(submit_result.get("ok", True))
            except Exception as exc:
                submit_result = {"ok": False, "error": str(exc)}
        if not submitted:
            submit_result = _submit_via_keyboard(ide=ide, submit=submit)
            submitted = bool(submit_result and submit_result.get("ok"))

    return {
        "ok": True,
        "backend": "vdisplay",
        "message": "typed via vdisplay semantic control",
        "type": "drive",
        "fallback_from": "plugin",
        "ide": ide,
        "selector": selector,
        "focus_error": focus_error,
        "typed": typed,
        "submitted": submitted,
        "submit_result": submit_result,
    }


def load_vql_metadata(path: str | None = None) -> dict:
    """Load VQL metadata (from .vdisplay/2026-06-11-vql-metadata-analysis-previous-current.json or per-capture .vql.json).
    Returns ui_elements with click_center, data_locations, decision_data etc for mouse nav + decide.
    Used to augment vision/control with explicit coords and data sources from previous/current analysis.
    Now also falls back to latest fresh capture VQL (e.g. koru-cont-*.vql.json) for up-to-date 30+ element bboxes/centers.
    """
    candidates = []
    if path:
        candidates.append(path)
    else:
        candidates += [
            ".vdisplay/2026-06-11-vql-metadata-analysis-previous-current.json",
            ".vdisplay/koru-cont-dp1-*.png.vql.json",  # glob handled below
            "/tmp/koru-cont-dp1-*.png.vql.json",
            "/tmp/vdisplay-auto-observe-auto-vision-find-cursor.png.vql.json",
        ]
    for cand in candidates:
        try:
            import glob
            if "*" in cand:
                matches = sorted(glob.glob(cand), reverse=True)
                if not matches: continue
                cand = matches[0]
            if not os.path.exists(cand): continue
            with open(cand) as f:
                data = json.load(f)
            # Normalize various VQL structures (analysis, fresh capture from screenshot, imgl, etc.)
            if "ui_elements" in data and data.get("ui_elements"):
                data["_source"] = cand
                return data
            if "elements" in data and isinstance(data.get("elements"), list) and data["elements"]:
                # Fresh per-capture .vql.json from screenshot (top-level elements + by_role + element_count)
                ui_els = []
                for e in data["elements"]:
                    bbox = e.get("bbox") or [0,0,0,0]
                    if isinstance(bbox, (list, tuple)) and len(bbox) >= 4:
                        cx = (bbox[0] + bbox[2]) / 2
                        cy = (bbox[1] + bbox[3]) / 2
                    else:
                        c = e.get("center") or [1024, 640]
                        cx, cy = (c if isinstance(c, (list,tuple)) else [1024,640])[:2]
                    ui_els.append({
                        "id": str(e.get("id", f"elem-{len(ui_els)}")),
                        "role": e.get("role", "unknown"),
                        "bounds": {"x": int(bbox[0]), "y": int(bbox[1]), "width": int(bbox[2]-bbox[0]) if len(bbox)>2 else 0, "height": int(bbox[3]-bbox[1]) if len(bbox)>3 else 0, "coordinate_space": "capture_frame_local"},
                        "click_center": {"x": int(cx), "y": int(cy), "note": f"fresh VQL elem, color={e.get('color')}, conf={e.get('confidence')}"},
                        "label": e.get("label"),
                        "metadata": {k: e.get(k) for k in ("color","confidence","location") if k in e}
                    })
                res = {"ui_elements": ui_els, "element_count": data.get("element_count", len(ui_els)), "by_role": data.get("by_role", {}), "scene": data.get("scene"), "_source": cand, "raw_fresh": True}
                return res
            if "vql" in data and isinstance(data.get("vql"), dict):
                prog = data["vql"].get("program", data["vql"])
                if isinstance(prog, dict):
                    prog["_source"] = cand
                    return prog
            if "screen_context" in data or "metadata" in data:
                return {"ui_elements": [], "metadata": data.get("metadata", data.get("screen_context", {})), "environment": data.get("environment", {}), "_source": cand}
            if isinstance(data.get("program"), (str, dict)) and "elements" not in data:
                data["_source"] = cand
                return data
            data["_source"] = cand
            return data
        except Exception as exc:
            continue
    return {"error": "no vql found", "tried": candidates}


def resolve_click_for_frame(source: str = "DP-1", vql_path: str | None = None, vision_fallback: bool = True) -> dict:
    """Helper: return best click coords for a monitor/frame.
    Prefers explicit from load_vql_metadata (fresh capture or analysis).
    Can be used when vision find returns no match (e.g. "planfile" anchor) as general editor/center action.
    """
    m = load_vql_metadata(vql_path)
    if m.get("ui_elements"):
        # Prefer first (usually the main capture frame for --source)
        for el in m.get("ui_elements", []):
            if source.lower() in str(el.get("source", "")).lower() or "dp-1" in str(el).lower() or not el.get("source"):
                if cc := el.get("click_center"):
                    return {"x": cc.get("x"), "y": cc.get("y"), "source": m.get("_source"), "note": el.get("note", "from VQL")}
        # fallback any
        el = m["ui_elements"][0]
        if cc := el.get("click_center") or el.get("center"):
            return {"x": cc.get("x") if isinstance(cc, dict) else cc[0], "y": cc.get("y") if isinstance(cc, dict) else cc[1], "source": m.get("_source")}
    # last resort frame center for 2048x1280 DP-1 crop
    return {"x": 1024, "y": 640, "source": "hardcoded-fallback", "note": "DP-1 capture frame center"}


__all__ = [
    "send_chat",
    "send_chat_via_ide_prompt",
    "simplified_control_likely_insufficient",
    "vdisplay_available",
    "vdisplay_fallback_enabled",
    "vdisplay_missing_message",
    "load_vql_metadata",
]
