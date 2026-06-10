"""vdisplay semantic control fallback for koru autonomous / coru drive.

When simplified control paths fail (plugin socket, blind wtype/ydotool, coordinate
injectors), koru can delegate to vdisplay's control plane for full semantic
automation: AT-SPI / Playwright / terminal / X11 / vision routing with verify.
"""

from __future__ import annotations

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


def vdisplay_available() -> bool:
    if _VDISPLAY_DIRECT:
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
    try:
        from vdisplay.desktop_apps import ide_hints_for

        return ide_hints_for(canon)
    except Exception:
        return dict(_IDE_HINTS.get(canon, {"app": canon, "window_title_contains": canon}))


def _chat_selectors_for(ide: str) -> tuple[dict[str, str], ...]:
    try:
        from vdisplay.desktop_apps import chat_selectors_for

        return chat_selectors_for(_canonical_ide(ide))
    except Exception:
        return _CHAT_INPUT_SELECTORS


def _submit_selectors_for(ide: str) -> tuple[dict[str, str], ...]:
    try:
        from vdisplay.desktop_apps import submit_selectors_for

        return submit_selectors_for(_canonical_ide(ide))
    except Exception:
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
        hints = _ide_hints(ide)
        return {
            "ok": True,
            "backend": "vdisplay",
            "dry_run": True,
            "ide": ide,
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


__all__ = [
    "send_chat",
    "simplified_control_likely_insufficient",
    "vdisplay_available",
    "vdisplay_fallback_enabled",
    "vdisplay_missing_message",
]
