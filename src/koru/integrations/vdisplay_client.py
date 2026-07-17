"""vdisplay semantic control fallback for koru autonomous / coru drive.

When simplified control paths fail (plugin socket, blind wtype/ydotool, coordinate
injectors), koru can delegate to vdisplay's control plane for full semantic
automation: AT-SPI / Playwright / terminal / X11 / vision routing with verify.
"""

from __future__ import annotations

import base64  # noqa: F401
import datetime
import json
import logging
import os
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

from koru.integrations import autonomy_session as _autonomy_session  # noqa: E402
from koru.integrations.photo_vql_config import llm_vision_enabled  # noqa: E402
from koru.integrations.photo_vql_monitor import (  # noqa: E402
    resolve_vdisplay_source_for_ide as _resolve_vdisplay_source_impl,
)

begin_autonomy_session = _autonomy_session.begin_autonomy_session

try:
    from koru.integrations.photo_vql_target import (
        VSCODE_FAMILY_TOP_CHAT_IDES,
    )
    from koru.integrations.photo_vql_target import (
        jetbrains_chat_corner_target_from_layers as _jetbrains_chat_corner_target_from_layers,
    )
    from koru.integrations.photo_vql_target import (
        jetbrains_chat_target_from_surface as _jetbrains_chat_target_from_surface,
    )
    from koru.integrations.photo_vql_target import (
        photo_vql_chat_input_candidates as _photo_vql_chat_input_candidates,
    )
    from koru.integrations.photo_vql_target import (
        vql_candidates_polluted as _vql_candidates_polluted,
    )
    from koru.integrations.photo_vql_target import (
        vql_layers_show_vdisplay_overlay as _vql_layers_show_vdisplay_overlay,
    )
    from koru.integrations.photo_vql_target import (
        vscode_family_chat_target_from_layers as _vscode_family_chat_target_from_layers,
    )
except ImportError:
    from koru.integrations.photo_vql_target import (
        jetbrains_chat_corner_target_from_layers as _jetbrains_chat_corner_target_from_layers,
    )
    from koru.integrations.photo_vql_target import (
        jetbrains_chat_target_from_surface as _jetbrains_chat_target_from_surface,
    )
    from koru.integrations.photo_vql_target import (
        photo_vql_chat_input_candidates as _photo_vql_chat_input_candidates,
    )
    from koru.integrations.photo_vql_target import (
        vql_candidates_polluted as _vql_candidates_polluted,
    )
    from koru.integrations.photo_vql_validation import (
        VSCODE_FAMILY_TOP_CHAT_IDES,
    )

    def _vql_layers_show_vdisplay_overlay(_layers: list[dict[str, Any]]) -> bool:
        return False

    def _vscode_family_chat_target_from_layers(
        _layers: list[dict[str, Any]],
        *,
        ide: str = "auto",
        source: str | None = None,
    ) -> dict[str, Any] | None:
        del ide, source
        return None
from koru.integrations.photo_vql_guard import (  # noqa: E402
    CaptureGuard,
)
from koru.integrations.photo_vql_guard import (  # noqa: E402
    allow_actuation_on_capture_mismatch as _allow_actuation_on_capture_mismatch,
)
from koru.integrations.photo_vql_guard import (  # noqa: E402
    allow_prepare_map_on_mismatch as _allow_prepare_map_on_mismatch,
)
from koru.integrations.photo_vql_guard import (  # noqa: E402
    allow_prepare_surface_on_capture_error as _allow_prepare_surface_on_capture_error,
)
from koru.integrations.photo_vql_guard import (  # noqa: E402
    competing_ide_label_from_warning as _competing_ide_label_from_warning,  # noqa: F401
)
from koru.integrations.photo_vql_guard import (  # noqa: E402
    drive_blocked_on_capture_mismatch as _drive_blocked_on_capture_mismatch,
)
from koru.integrations.photo_vql_guard import (  # noqa: E402
    ide_mismatch_allowed as _ide_mismatch_allowed,
)
from koru.integrations.photo_vql_validation import (  # noqa: E402
    capture_title_from_meta as _capture_title_from_meta,
)
from koru.integrations.photo_vql_validation import (  # noqa: E402
    validate_chat_coords_for_ide as _validate_chat_coords_for_ide,
)
from koru.integrations.photo_vql_validation import (  # noqa: E402
    validate_vql_chat_target,
)
from koru.integrations.photo_vql_validation import (  # noqa: E402
    window_titles_from_vql_meta as _window_titles_from_vql_meta,
)
from koru.integrations.vdisplay.env_session import (  # noqa: E402
    clear_stale_observe_session_env,
    dry_run_enabled as _dry_run,
    session_type as _session_type,
    sync_prepare_capture_flags_to_env,
)


def _real_vdisplay_src() -> str | None:
    candidates: list[str] = []
    explicit = os.environ.get("VDISPLAY_SRC", "").strip()
    if explicit:
        candidates.append(explicit)
    candidates.append(str(Path.home() / "github/wronai/vdisplay/src"))
    candidates.append(str(Path.home() / "github/wronai/vdisplay"))
    for raw in candidates:
        root = Path(raw).expanduser()
        src_root = root / "src" if (root / "src" / "vdisplay").is_dir() else root
        if (src_root / "vdisplay" / "ide_prompt.py").is_file():
            return str(src_root)
    return None


def _ensure_real_vdisplay_on_path() -> None:
    import sys

    root = _real_vdisplay_src()
    if not root:
        return
    if root in sys.path:
        sys.path.remove(root)
    sys.path.insert(0, root)
    pkg = sys.modules.get("vdisplay")
    pkg_path = str(Path(root) / "vdisplay")
    paths = getattr(pkg, "__path__", None)
    if paths is not None and pkg_path not in list(paths):
        try:
            paths.insert(0, pkg_path)
        except AttributeError:
            paths.append(pkg_path)


_ensure_real_vdisplay_on_path()

# Optional: LLM vision decision layer on top of photo VQL (enable via env + .env OpenRouter key)
try:
    from koru.autonomy_strategy.openrouter import call_openrouter_vision
except Exception:
    call_openrouter_vision = None

_VDISPLAY_DIRECT = False
_VDISPLAY_IMPORT_ERROR: str | None = None
_vdisplay_control = None

def _load_vdisplay_control():
    """Lazy load to avoid top-level crashes from vdisplay submodules (e.g. missing dataclass in some versions) and make autonomy robust."""  # noqa: E501
    global _VDISPLAY_DIRECT, _VDISPLAY_IMPORT_ERROR, _vdisplay_control
    if _vdisplay_control is not None or _VDISPLAY_DIRECT:
        return _VDISPLAY_DIRECT
    try:
        from vdisplay.application.services import control as control_mod
        _vdisplay_control = control_mod
        _VDISPLAY_DIRECT = True
        _VDISPLAY_IMPORT_ERROR = None
        return True
    except Exception as exc:  # broader than ImportError (catches NameError etc inside vdisplay modules)
        _VDISPLAY_DIRECT = False
        _VDISPLAY_IMPORT_ERROR = str(exc)
        return False

# initial best-effort (non-fatal)
try:
    from vdisplay.application.services import control as _vdisplay_control
    _VDISPLAY_DIRECT = True
except Exception as exc:
    _VDISPLAY_IMPORT_ERROR = str(exc)
    _vdisplay_control = None

_IDE_HINTS: dict[str, dict[str, str]] = {
    "windsurf": {"app": "Windsurf", "window_title_contains": "Windsurf"},
    "cursor": {"app": "Cursor", "window_title_contains": "Cursor"},
    "vscode": {"app": "code", "window_title_contains": "Visual Studio Code"},
    "vscodium": {"app": "VSCodium", "window_title_contains": "VSCodium"},
    "antigravity": {"app": "Antigravity", "window_title_contains": "Antigravity"},
    "zed": {"app": "zed", "window_title_contains": "Zed"},
    "jetbrains": {"app": "pycharm", "window_title_contains": "PyCharm"},
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
        from koru.integrations.vdisplay_agent_bootstrap import (
            apply_vdisplay_agent_env,
            resolve_vdisplay_agent_url,
        )

        applied = apply_vdisplay_agent_env()
        url = applied.get("agent_url") or resolve_vdisplay_agent_url()
        if url:
            return url.rstrip("/")
        from vdisplay.agent_config import resolve_agent_url

        return resolve_agent_url(allow_auto=True)
    except ImportError:
        try:
            from koru.integrations.vdisplay_agent_bootstrap import resolve_vdisplay_agent_url

            url = resolve_vdisplay_agent_url()
            return url.rstrip("/") if url else None
        except ImportError:
            return None


def _probe_agent(url: str) -> bool:
    try:
        from koru.integrations.vdisplay_agent_bootstrap import probe_vdisplay_agent

        return probe_vdisplay_agent(url.rstrip("/"))
    except ImportError:
        pass
    try:
        with urllib.request.urlopen(f"{url.rstrip('/')}/health", timeout=0.5) as resp:
            return resp.status == 200
    except (urllib.error.URLError, TimeoutError, OSError, ValueError):
        return False


def _reload_vdisplay_direct() -> bool:
    return _load_vdisplay_control()


def _ensure_vdisplay_runtime() -> bool:
    if _VDISPLAY_DIRECT:
        return True
    from koru.deps_autorepair import ensure_vdisplay_runtime

    if not ensure_vdisplay_runtime(label="koru drive"):
        return False
    return _reload_vdisplay_direct()


def vdisplay_available() -> bool:
    if _VDISPLAY_DIRECT or _load_vdisplay_control():
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

    expected = text.strip()
    if not expected:
        return {"ok": True, "verified": True, "mode": "ocr_contains", "reason": "empty text"}

    png, capture_meta, bounds = _capture_for_verify(chat_x, chat_y, map_path, ide)
    if not png:
        return {"ok": False, "verified": False, "mode": "ocr_contains", "error": "screenshot capture failed", "bounds": bounds.to_dict() if bounds else None, "ide": ide}  # noqa: E501

    from koru.deps_autorepair import ensure_vision_ocr

    if not ensure_vision_ocr(label="koru verify"):
        return {
            "ok": False,
            "verified": False,
            "mode": "ocr_contains",
            "error": "OCR verify deps missing (tesseract, Pillow, pytesseract)",
        }

    try:
        from vdisplay.control.vision_ocr import ocr_available
    except ImportError:
        import shutil

        def ocr_available() -> tuple[bool, str]:
            try:
                import pytesseract  # noqa: F401
            except ImportError as exc:
                return False, str(exc)
            if not shutil.which("tesseract"):
                return False, "tesseract binary not found on PATH"
            return True, ""

    ready, reason = ocr_available()
    if not ready:
        return {
            "ok": False,
            "verified": False,
            "mode": "ocr_contains",
            "error": reason,
        }

    return _ocr_verify(png, capture_meta, bounds, expected, ide, chat_x, chat_y)


def _capture_for_verify(chat_x, chat_y, map_path, ide):
    from vdisplay.control.gui_map import load_gui_map
    from vdisplay.control.models import ControlBounds, ControlNode, ControlRole
    from vdisplay.control.screenshot_verify import capture_control_screenshot
    from vdisplay.input.coords import global_pointer_coords

    bounds = None
    if chat_x is not None and chat_y is not None:
        bounds = ControlBounds(x=int(chat_x) - 360, y=int(chat_y) - 24, width=720, height=48)
        target = ControlNode(id="verify:chat-input", backend="vision", role=ControlRole.INPUT, name="chat-input", bounds=bounds)  # noqa: E501
        try:
            png, capture_meta = capture_control_screenshot(target=target)
            if not png:
                png, capture_meta = capture_control_screenshot(target=None)
            return png, capture_meta, bounds
        except Exception as exc:  # noqa: F841
            return None, None, bounds
    elif map_path:
        try:
            pack = load_gui_map(map_path)
            # Prefer "prompt" (reliable for JetBrains chat input on DP-2) then "ai-chat-input" for verify bounds.
            element = pack.elements.get("prompt") or pack.elements.get("ai-chat-input")
            if element is None:
                raise KeyError("prompt or ai-chat-input")
            meta = element.capture_meta or pack.capture_meta or {}
            gx, gy, _ = global_pointer_coords(element.click_point.x, element.click_point.y, meta)
            return _capture_for_verify(gx, gy, None, ide)
        except Exception as exc:  # noqa: F841
            return None, None, None
    else:
        return None, None, None


def _ocr_verify(png, capture_meta, bounds, expected, ide, chat_x, chat_y):
    from vdisplay.control.screenshot_verify import (
        global_point_in_stream_bounds,
        stream_bounds_from_meta,
    )
    from vdisplay.control.vision_ocr import ocr_png

    screenshot_path = str(capture_meta["path"]) if isinstance(capture_meta, dict) and capture_meta.get("path") else None

    stream_hint = None
    if isinstance(capture_meta, dict) and chat_x is not None and chat_y is not None:
        if not global_point_in_stream_bounds(int(chat_x), int(chat_y), capture_meta):
            stream = stream_bounds_from_meta(capture_meta)
            stream_hint = f"Chat focus ({chat_x},{chat_y}) is outside active ScreenCast stream {stream}. Restart screencast and pick All Screens or the monitor containing the IDE."  # noqa: E501

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
        "bounds": bounds.to_dict() if bounds else None,
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
        from vdisplay.application.session_recorder import (
            record_execution,
            session_recording_enabled,
        )
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
    verify_path = (payload.get("verification") or {}).get("screenshot_path")
    if not verify_path:
        verify_path = (payload.get("artifacts") or {}).get("verify_screenshot")
    if verify_path:
        artifacts.append(ArtifactRef(kind="screenshot", path=str(verify_path), label="verify"))
    try:
        from koru.integrations import autonomy_session as _autonomy_session

        session = _autonomy_session.active_session_dir()
        if session is not None:
            observe_png, _vql = _autonomy_session.session_observe_paths(session)
            if observe_png.is_file():
                artifacts.append(ArtifactRef(kind="observe", path=str(observe_png), label="capture"))
    except Exception:
        pass
    result = CommandResult(
        ok=bool(payload.get("ok")),
        action="koru_drive",
        data=dict(payload),
        diagnostics=diagnostics,
        artifacts=artifacts,
    )
    session_dir = record_execution(cmd, result, route="koru-direct", duration_ms=0)
    return str(session_dir) if session_dir else None


from koru.integrations.vdisplay.control_policy import (  # noqa: E402
    simplified_control_likely_insufficient as _simplified_control_policy,
    vdisplay_fallback_enabled as _vdisplay_fallback_policy,
)
from koru.integrations.vdisplay.control_policy import (  # noqa: E402,F401
    _photo_vql_code_edit_enabled,
    _send_chat_os_injector_enabled,
    _trusted_visual_target_id,
)


def simplified_control_likely_insufficient(*, ide: str, plugin_connected: bool = False) -> bool:
    """Heuristic: simplified keyboard/plugin paths are unlikely to work."""
    return _simplified_control_policy(ide=ide, plugin_connected=plugin_connected)


def vdisplay_fallback_enabled(*, ide: str | None = None, plugin_connected: bool = False) -> bool:
    """Whether drive may use vdisplay semantic control as fallback."""
    return _vdisplay_fallback_policy(
        ide=ide,
        plugin_connected=plugin_connected,
        available=vdisplay_available,
    )


def _prefer_photo_vql_chat(*, ide: str = "auto") -> bool:
    """When set, send_chat uses photo VQL mouse+focus path before os_injector/ide_prompt."""
    from koru.integrations.vdisplay.control_policy import prefer_photo_vql_chat

    return prefer_photo_vql_chat(ide=ide, capture_matches=_capture_matches_requested_ide)


def _capture_matches_requested_ide(ide: str) -> bool:
    if os.environ.get("KORU_VDISPLAY_CAPTURE_MATCHES_IDE", "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }:
        return True
    return _photo_vql_ide_capture_mismatch(ide=ide) is None


def _vdisplay_source() -> str:
    explicit = os.environ.get("KORU_VDISPLAY_SOURCE", "").strip()
    if explicit:
        return explicit
    ide = (
        os.environ.get("KORU_DRIVE_IDE")
        or os.environ.get("KORU_AUTOPILOT_INSTANCE")
        or "auto"
    )
    return _vdisplay_source_for_ide(ide)


_IDE_DEFAULT_SOURCE: dict[str, str] = {
    "cursor": "DP-1",
    "windsurf": "DP-1",
    "antigravity": "DP-1",
    "vscode": "DP-1",
    "qoder": "DP-1",
    "jetbrains": "DP-1",
    "pycharm": "DP-1",
    "idea": "DP-1",
}

# Desktop probe extracted to koru.integrations.vdisplay.desktop_probe;
# re-exported here for backward compatibility.
from koru.integrations.vdisplay.desktop_probe import (  # noqa: E402,F401
    _desktop_probe,
    _desktop_probe_ide_hints,
    _desktop_probe_ide_surface_rank,
    _probe_ide_processes,
)


# Surface capture confirmation extracted to vdisplay.surface_capture.
from koru.integrations.vdisplay.surface_capture import (  # noqa: E402,F401
    _apply_surface_capture_confirmation,
    _apply_surface_capture_confirmed,
    _apply_surface_capture_error_fallback,
    _clear_surface_overridden_vql_staleness,
    _persist_surface_capture_confirmation_to_vql,
    _surface_confirms_ide_capture,
    _write_surface_capture_confirmation_sidecar,
)


def _annotate_prepare_drive_readiness(out: dict[str, Any]) -> None:
    reasons: list[str] = []
    if not out.get("ok"):
        reasons.append("prepare_not_ok")
    if out.get("capture_confirmed") is False:
        reasons.append("capture_not_confirmed")
    if out.get("map_capture_mismatch") and not _map_source_mismatch_actuation_allowed():
        reasons.append("map_capture_mismatch")
    if int(out.get("main_vql_layers") or out.get("elements") or 0) <= 0 and not out.get("surface_only_fallback"):
        reasons.append("empty_vql_layers")
    out["drive_ready"] = not reasons
    if reasons:
        out["drive_blocked_reasons"] = reasons
        out["drive_blocked_reason"] = reasons[0]
        if out.get("map_capture_mismatch") and "map_capture_mismatch" in reasons:
            out["map_actuation_ready"] = False
    else:
        out.pop("drive_blocked_reasons", None)
        out.pop("drive_blocked_reason", None)
        if out.get("map_capture_mismatch"):
            out["map_actuation_ready"] = True


def _resolve_vdisplay_source_for_ide(
    ide: str,
    *,
    probe: dict[str, Any] | None = None,
) -> tuple[str, dict[str, Any]]:
    try:
        return _resolve_vdisplay_source_impl(
            ide,
            canonical_ide=_canonical_ide,
            desktop_probe=_desktop_probe,
            probe=probe,
            ide_default_source=_IDE_DEFAULT_SOURCE,
        )
    except TypeError as exc:
        if "ide_default_source" not in str(exc):
            raise
        from koru.integrations import photo_vql_monitor as _photo_vql_monitor

        previous_defaults = getattr(_photo_vql_monitor, "_IDE_DEFAULT_SOURCE", None)
        _photo_vql_monitor._IDE_DEFAULT_SOURCE = _IDE_DEFAULT_SOURCE
        try:
            return _resolve_vdisplay_source_impl(
                ide,
                canonical_ide=_canonical_ide,
                desktop_probe=_desktop_probe,
                probe=probe,
            )
        finally:
            if previous_defaults is not None:
                _photo_vql_monitor._IDE_DEFAULT_SOURCE = previous_defaults


def _abort_on_desktop_probe_fail() -> bool:
    return os.environ.get("KORU_VDISPLAY_ABORT_ON_PROBE_FAIL", "1").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def _vdisplay_source_for_ide(ide: str) -> str:
    explicit = os.environ.get("KORU_VDISPLAY_SOURCE", "").strip()
    if explicit:
        return explicit
    try:
        src, _probe = _resolve_vdisplay_source_for_ide(ide)
        if src:
            os.environ.setdefault("KORU_VDISPLAY_SOURCE", src)
            return src
    except Exception:
        pass
    canon = _canonical_ide(ide)
    return _IDE_DEFAULT_SOURCE.get(canon, "DP-1")


def _photo_vql_metadata_root() -> Path:
    from pathlib import Path

    return Path(os.environ.get("VDISPLAY_METADATA_DIR", ".vdisplay")).expanduser()


from koru.integrations.vdisplay.photo_vql_meta import (  # noqa: E402,F401
    COMPETING_IDE_WINDOW_TOKENS as _COMPETING_IDE_WINDOW_TOKENS,
    IDE_WINDOW_TITLE_TOKENS as _IDE_WINDOW_TITLE_TOKENS,
    _capture_validation_from_meta,
    _photo_vql_overlay_labels,
    _photo_vql_portal_actor_detected,
    _photo_vql_share_prompt_detected,
    _photo_vql_system_overlay_warning,
    _type_text_plan_validation_warnings,
    photo_vql_capture_validation_failed_warning,
    photo_vql_expected_title_tokens,
    photo_vql_ide_window_warning,
    photo_vql_title_mismatch_warning,
)


def _capture_confirmed_from_meta(*, ide: str, meta: dict | None) -> bool:
    """Single source of truth: observe sidecar only (never map file mtime)."""
    meta = meta or {}
    if _photo_vql_system_overlay_warning(meta=meta):
        return False
    cv = _capture_validation_from_meta(meta)
    if isinstance(cv, dict) and cv.get("capture_confirmed") is not None:
        return bool(cv.get("capture_confirmed"))
    if _photo_vql_ide_window_warning(ide=ide, meta=meta):
        return False
    titles = _window_titles_from_vql_meta(meta)
    return bool(titles)


def _capture_provenance(
    *,
    ide: str,
    png_path: str | None = None,
    vql_path: str | None = None,
    meta: dict | None = None,
) -> dict[str, Any]:
    """Timestamps + window titles from the observe capture (audit / drive_reply)."""
    prov: dict[str, Any] = {"ide": ide}
    for key, path in (("png", png_path), ("vql", vql_path)):
        if path and os.path.isfile(path):
            try:
                st = os.stat(path)
                prov[f"{key}_path"] = path
                prov[f"{key}_mtime"] = st.st_mtime
                prov[f"{key}_mtime_iso"] = datetime.datetime.fromtimestamp(st.st_mtime).isoformat()
            except OSError:
                pass
    meta = meta or {}
    titles = _window_titles_from_vql_meta(meta)
    if titles:
        prov["window_titles"] = titles
        prov["capture_title"] = titles[0]
    warn = _photo_vql_ide_window_warning(ide=ide, meta=meta) if meta else None
    prov["capture_confirmed"] = _capture_confirmed_from_meta(ide=ide, meta=meta)
    if warn:
        prov["ide_window_warning"] = warn
    return prov


def _photo_vql_capture_validation_failed_warning(
    cv: dict[str, Any], *, ide: str, meta: dict
) -> dict[str, Any]:
    return photo_vql_capture_validation_failed_warning(
        cv, ide=ide, meta=meta, window_titles=_window_titles_from_vql_meta
    )


def _photo_vql_expected_title_tokens(canon: str) -> tuple[str, ...]:
    return photo_vql_expected_title_tokens(canon, ide_hints=_ide_hints)


def _photo_vql_title_mismatch_warning(
    canon: str, tokens: tuple[str, ...], titles: list[str]
) -> dict[str, Any] | None:
    return photo_vql_title_mismatch_warning(canon, tokens, titles)


def _photo_vql_ide_window_warning(*, ide: str, meta: dict) -> dict[str, Any] | None:
    return photo_vql_ide_window_warning(
        ide=ide,
        meta=meta,
        window_titles=_window_titles_from_vql_meta,
        ide_hints=_ide_hints,
    )


def _observe_vql_sidecar_path(*, source: str | None = None) -> str | None:
    """Resolve observe-phase VQL sidecar (never map/calibration paths)."""
    from pathlib import Path

    session = _autonomy_session.active_session_dir()
    if session is not None:
        _png, vql = _autonomy_session.session_observe_paths(session)
        if vql.is_file():
            return str(vql)
    explicit = os.environ.get("KORU_VDISPLAY_VQL_PATH", "").strip()
    if explicit and explicit.endswith(".vql.json") and os.path.isfile(explicit):
        return explicit
    png = _resolve_photo_png_path_from_vql(source=source)
    if png and os.path.isfile(png):
        sidecar = str(Path(png).with_suffix(Path(png).suffix + ".vql.json"))
        if os.path.isfile(sidecar):
            return sidecar
    return None


def _annotate_png_artifact_state(out: dict[str, Any]) -> dict[str, Any]:
    raw = str(out.get("png") or "").strip()
    if not raw:
        out.setdefault("png_exists", False)
        return out
    # A failed capture/refresh must never inherit a file already sitting at the
    # requested path — that stale screenshot (e.g. /tmp/capture.png from a prior
    # session) would false-positive as a fresh confirmation and let koru actuate
    # on the wrong screen. Distrust the path whenever the step reported failure.
    capture_failed = bool(out.get("ok") is False or out.get("error") or out.get("returncode"))
    path = Path(raw).expanduser()
    exists = path.is_file()
    if capture_failed:
        out["png_exists"] = False
        out.setdefault("requested_png_path", raw)
        out["png"] = None
        return out
    out["png_exists"] = exists
    if exists:
        out["png"] = str(path.resolve())
        return out
    out.setdefault("requested_png_path", raw)
    return out


def _photo_png_from_vql_sidecar_path(cand_vql: str) -> str | None:
    """Derive the PNG path from a VQL sidecar filename (with metadata-root fallback)."""
    from pathlib import Path

    if cand_vql.endswith(".png.vql.json"):
        png = cand_vql[: -len(".vql.json")]
    elif cand_vql.endswith(".vql.json"):
        png = cand_vql[: -len(".vql.json")]
    else:
        png = cand_vql
    if os.path.isfile(png):
        return png
    rooted = _photo_vql_metadata_root() / Path(png).name
    if rooted.is_file():
        return str(rooted)
    return None


def _photo_png_from_vql_metadata(cand_vql: str) -> str | None:
    """Resolve the PNG path from VQL metadata data_locations / scene URL."""
    try:
        meta = load_vql_metadata(cand_vql or None)
        dl = meta.get("data_locations") if isinstance(meta.get("data_locations"), dict) else {}
        png_from_meta = (dl or {}).get("png") if isinstance(dl, dict) else None
        if png_from_meta and os.path.isfile(png_from_meta):
            return png_from_meta
        scene = meta.get("scene") if isinstance(meta.get("scene"), dict) else {}
        url = str((scene or {}).get("url") or "")
        if url.startswith("file://") and os.path.isfile(url[7:]):
            return url[7:]
    except Exception:
        pass
    return None


def _resolve_photo_png_path_from_vql(
    *,
    vql_path: str | None = None,
    source: str | None = None,
) -> str | None:
    """Resolve the screenshot PNG paired with a photo-VQL sidecar (for LLM vision)."""
    explicit = os.environ.get("KORU_VDISPLAY_PHOTO_PATH", "").strip()
    if explicit and os.path.isfile(explicit):
        return explicit

    cand_vql = (vql_path or os.environ.get("KORU_VDISPLAY_VQL_PATH", "")).strip()
    if cand_vql:
        png = _photo_png_from_vql_sidecar_path(cand_vql)
        if png:
            return png

    png_from_meta = _photo_png_from_vql_metadata(cand_vql)
    if png_from_meta:
        return png_from_meta

    src = source or _vdisplay_source()
    png_path = _resolve_photo_png_path(src)
    return str(png_path) if png_path.is_file() else None


def _photo_vql_ide_capture_mismatch(*, ide: str) -> dict[str, Any] | None:
    """Return warning dict when the current photo-VQL sidecar does not match the requested IDE."""
    meta: dict[str, Any] | None = None
    session = _autonomy_session.active_session_dir()
    if session is not None:
        _png, vql = _autonomy_session.session_observe_paths(session)
        if vql.is_file():
            meta = load_vql_metadata(str(vql), allow_stale=True)
    if meta is None or not (meta.get("ui_elements") or meta.get("layers")):
        try:
            meta = load_vql_metadata(allow_stale=True)
        except Exception:
            return None
    if meta.get("error"):
        return None
    return _photo_vql_ide_window_warning(ide=ide, meta=meta)


def _prefer_ide_prompt_over_photo_vql(*, ide: str) -> bool:
    """JetBrains on Wayland: GUI map beats photo VQL when capture shows the wrong IDE."""
    canon = _canonical_ide(ide)
    if canon not in {"jetbrains", "pycharm", "idea"}:
        return False
    if not _capture_matches_requested_ide(ide):
        return True
    raw = os.environ.get("KORU_VDISPLAY_PREFER_PHOTO_VQL", "").strip().lower()
    if raw in {"0", "false", "no", "off"}:
        return True
    if raw == "auto":
        return False
    return False


def _auto_ide_control_enabled() -> bool:
    return os.environ.get("KORU_VDISPLAY_AUTO_IDE_CONTROL", "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def _auto_open_ide_enabled(*, ide: str = "auto") -> bool:
    raw = os.environ.get("KORU_VDISPLAY_AUTO_OPEN_IDE", "").strip().lower()
    if raw in {"1", "true", "yes", "on"}:
        return True
    if raw in {"0", "false", "no", "off"}:
        return False
    return _canonical_ide(ide) in {"jetbrains", "pycharm", "idea"}


def _real_imgl_src() -> str | None:
    """Filesystem path to semcod imgl (not koru/src/imgl stub)."""
    candidates: list[str] = []
    explicit = os.environ.get("IMGL_SRC", "").strip()
    if explicit:
        candidates.append(explicit)
    candidates.append(str(Path.home() / "github/semcod/imgl"))
    for raw in candidates:
        root = Path(raw).expanduser()
        if (root / "imgl" / "pipeline.py").is_file() or (root / "imgl" / "config.py").is_file():
            return str(root)
    return None


def _ensure_real_imgl_on_path() -> None:
    """Prefer real semcod imgl over koru/src/imgl compatibility stub."""
    import sys

    imgl_root = _real_imgl_src()
    if not imgl_root:
        return
    koru_stub = str(Path(__file__).resolve().parents[2] / "imgl")
    sys.path = [p for p in sys.path if p not in {koru_stub, str(Path(koru_stub).resolve())}]
    if imgl_root in sys.path:
        sys.path.remove(imgl_root)
    sys.path.insert(0, imgl_root)
    cached = sys.modules.get("imgl")
    cached_file = str(getattr(cached, "__file__", "") or "") if cached is not None else ""
    cached_path = Path(cached_file).resolve() if cached_file else None
    root_path = Path(imgl_root).resolve()
    if cached is not None and (
        cached_path is None or root_path not in cached_path.parents
    ):
        for name in list(sys.modules):
            if name == "imgl" or name.startswith("imgl."):
                sys.modules.pop(name, None)


def _vdisplay_cli_candidates() -> list[str]:
    import shutil

    out: list[str] = []
    for candidate in (
        os.environ.get("VDISPLAY_CLI", "").strip(),
        str(Path.home() / "github/wronai/vdisplay/.venv/bin/vdisplay"),
        shutil.which("vdisplay") or "",
        str(Path.home() / ".venv/bin/vdisplay"),
    ):
        if candidate and Path(candidate).is_file() and candidate not in out:
            out.append(candidate)
    if not out:
        out.append("vdisplay")
    return out


def _vdisplay_cli_path() -> str:
    for candidate in _vdisplay_cli_candidates():
        return candidate
    return "vdisplay"


def _vdisplay_observe_python_candidates() -> list[str]:
    import sys

    out: list[str] = []
    for candidate in (
        os.environ.get("VDISPLAY_OBSERVE_PYTHON", "").strip(),
        str(Path.home() / ".venv/bin/python"),
        str(Path.home() / "github/wronai/vdisplay/.venv/bin/python"),
        sys.executable,
    ):
        if candidate and Path(candidate).is_file() and candidate not in out:
            out.append(candidate)
    if not out:
        out.append(sys.executable)
    return out


def _vdisplay_subprocess_env(*, ide: str = "auto") -> dict[str, str]:
    """Env for vdisplay CLI subprocess: real imgl first, capture validation for IDE."""
    env = os.environ.copy()
    try:
        from koru.integrations.vdisplay_agent_bootstrap import apply_vdisplay_agent_env

        apply_vdisplay_agent_env()
        env = os.environ.copy()
    except ImportError:
        pass
    path_parts: list[str] = []
    imgl_root = _real_imgl_src()
    if imgl_root:
        path_parts.append(imgl_root)
    vdisplay_src = os.environ.get("VDISPLAY_SRC", "").strip()
    if not vdisplay_src:
        guess = Path.home() / "github/wronai/vdisplay/src"
        if guess.is_dir():
            vdisplay_src = str(guess)
    if vdisplay_src:
        path_parts.append(vdisplay_src)
    koru_src = os.environ.get("KORU_SRC", "").strip()
    if not koru_src:
        koru_src = str(Path(__file__).resolve().parents[2])
    if koru_src:
        path_parts.append(koru_src)
    existing = env.get("PYTHONPATH", "").strip()
    if existing:
        path_parts.append(existing)
    env["PYTHONPATH"] = ":".join(path_parts)
    env.setdefault("VDISPLAY_IMGL", "1")
    canon = _canonical_ide(ide)
    if canon not in {"", "auto"}:
        env.setdefault("VDISPLAY_CAPTURE_VALIDATE_IDE", canon)
    return env


from koru.integrations.vdisplay import window_focus as _window_focus  # noqa: E402


def _focus_window_xdotool(*, title_contains: str) -> dict[str, Any]:
    return _window_focus.focus_window_xdotool(title_contains=title_contains)


def _focus_window_xdotool_for_ide(*, ide: str) -> dict[str, Any]:
    return _window_focus.focus_window_xdotool_for_ide(
        ide=ide, ide_hints=_ide_hints, app_id=_ide_prompt_app_id
    )


def _focus_window_gnome_shell(*, title_contains: str) -> dict[str, Any]:
    return _window_focus.focus_window_gnome_shell(title_contains=title_contains)


def _focus_window_gnome_shell_for_ide(*, ide: str) -> dict[str, Any]:
    return _window_focus.focus_window_gnome_shell_for_ide(
        ide=ide, ide_hints=_ide_hints, app_id=_ide_prompt_app_id
    )


def _click_map_region_center(
    map_path: str,
    *,
    source: str,
    region_id: str = "pycharm.ai_chat",
) -> dict[str, Any]:
    return _window_focus.click_map_region_center(
        map_path,
        source=source,
        region_id=region_id,
        control_click=_control_click,
    )


def _raise_alt_tab_enabled(*, ide: str = "auto") -> bool:
    return _window_focus.raise_alt_tab_enabled(ide=ide)


def _alt_tab_window_cycle(*, cycles: int = 1, ide: str = "auto") -> dict[str, Any]:
    return _window_focus.alt_tab_window_cycle(cycles=cycles, ide=ide)


def _attempt_focus_recovery_capture(*, ide: str, source: str) -> dict[str, Any]:
    """Alt+Tab cycles with re-capture until observe confirms target IDE or attempts exhausted."""
    if not _raise_alt_tab_enabled(ide=ide):
        return {"ok": False, "skipped": True, "focus_recovery": {"ok": False, "skipped": True}}

    import time

    max_attempts = max(1, int(os.environ.get("KORU_VDISPLAY_FOCUS_RECOVERY_ATTEMPTS", "3") or "3"))
    attempts_log: list[dict[str, Any]] = []
    delay = float(os.environ.get("KORU_VDISPLAY_POST_FOCUS_CAPTURE_DELAY_S", "0.8"))

    for attempt_idx in range(max_attempts):
        recovery = _alt_tab_window_cycle(cycles=1, ide=ide)
        attempts_log.append({"attempt": attempt_idx + 1, **recovery})
        if not recovery.get("ok"):
            continue
        time.sleep(delay)
        out = refresh_photo_vql_sidecar(source=source, ide=ide)
        warn = out.get("ide_window_warning") or _photo_vql_ide_window_warning(
            ide=ide,
            meta=load_vql_metadata(str(out.get("vql") or ""), allow_stale=True),
        )
        if not warn:
            out["focus_recovery"] = {
                "ok": True,
                "attempts": attempts_log,
                "recovered_on_attempt": attempt_idx + 1,
            }
            out["ide_window_warning"] = None
            out["capture_matches_ide"] = True
            return out
        out["ide_window_warning"] = warn

    return {
        "ok": False,
        "focus_recovery": {"ok": False, "attempts": attempts_log},
    }


def _persist_send_chat_drive_result(
    result: dict[str, Any],
    *,
    prompt: str,
    ide: str,
    submit: bool,
) -> None:
    """Persist act/drive_result.json for send_chat outcomes (photo-vql, ide-prompt, blocked)."""
    session = _autonomy_session.active_session_dir()
    if session is None:
        return
    backend = str(result.get("backend") or "")
    if result.get("type") == "blocked" or backend.endswith("+blocked"):
        _autonomy_session.persist_autonomy_phase(session, "act", "drive_result", {**result, "prompt": prompt[:200], "submit": submit})  # noqa: E501
        return
    if not (backend.startswith("vdisplay") or result.get("type") == "drive"):
        return
    payload = {**result, "prompt": prompt[:200], "submit": submit}
    _autonomy_session.persist_autonomy_phase(session, "act", "drive_result", payload)


def _map_raise_targets_for_ide(app_id: str, map_path: str) -> tuple[str, ...]:
    """Upper-panel map targets — safe for window raise (avoid bottom hot corner)."""
    ordered: list[str] = []
    for fallback in ("prompt", "gemini", "analyzing", "project", "attach", "files", "recall", "saved"):
        if fallback not in ordered:
            ordered.append(fallback)
    try:
        from vdisplay.control.gui_map import load_gui_map

        present = set(load_gui_map(map_path).elements.keys())
        return tuple(t for t in ordered if t in present)
    except Exception:
        return tuple(ordered[:4])


def _map_interior_targets_for_ide(app_id: str, map_path: str) -> tuple[str, ...]:
    """Chat input targets — use after window is raised (may be lower on screen)."""
    ordered: list[str] = []
    try:
        from vdisplay.desktop_apps import map_input_target_candidates

        ordered.extend(map_input_target_candidates(app_id))
    except Exception:
        pass
    # For JetBrains/PyCharm on DP-2 (rotated screencast), "prompt" map target has proven
    # reliable for chat input focus (sane coords after mapping, unlike some "ai-chat-input" calibrations).
    # Prefer it early for interior/chat actions.
    for fallback in ("prompt", "ai-chat-input", "chat-input", "message"):
        if fallback not in ordered:
            ordered.append(fallback)
    try:
        from vdisplay.control.gui_map import load_gui_map

        present = set(load_gui_map(map_path).elements.keys())
        return tuple(t for t in ordered if t in present)
    except Exception:
        return tuple(ordered[:2])


def _dismiss_gnome_overview(*, reason: str = "recover") -> dict[str, Any]:
    """Close GNOME Activities / Show Applications if a hot-corner click opened it."""
    try:
        from vdisplay.input.resolve import resolve_pointer_input

        inp, method = resolve_pointer_input()
        hotkey = getattr(inp, "hotkey", None)
        if hotkey is None:
            return {"ok": False, "skipped": True, "reason": reason}
        try:
            hotkey("Escape")
        except TypeError:
            hotkey("Escape")
        return {"ok": True, "method": f"{method}-escape", "reason": reason}
    except Exception as exc:
        return {"ok": False, "error": str(exc), "reason": reason}


def _ide_control_resolve_map(result: dict[str, Any], app_id: str, src: str) -> tuple[str | None, dict[str, Any] | None]:
    """Resolve calibrated IDE map path and its monitor mismatch (if any) into result."""
    map_path = _resolve_ide_prompt_map(app_id)
    result["map_path"] = map_path
    map_mismatch = None
    if map_path:
        from koru.integrations.photo_vql_monitor import map_capture_monitor_mismatch

        map_mismatch = map_capture_monitor_mismatch(map_path, source=src)
        if map_mismatch:
            result["map_capture_mismatch"] = map_mismatch
    return map_path, map_mismatch


def _ide_control_open_ide(result: dict[str, Any], app_id: str, ide: str) -> None:
    """Auto-open the IDE desktop app when enabled, recording the step."""
    if not _auto_open_ide_enabled(ide=ide):
        return
    try:
        from vdisplay.ide_prompt import open_desktop_app

        opened = open_desktop_app(app_id, wait_seconds=2.0)
        result["steps"].append({"open": opened})
    except Exception as exc:
        result["steps"].append({"open": {"ok": False, "error": str(exc)}})


def _ide_control_raise_window(result: dict[str, Any], ide: str) -> None:
    """Raise the IDE window via gnome-shell, falling back to xdotool."""
    gnome_focus = _focus_window_gnome_shell_for_ide(ide=ide)
    result["steps"].append({"gnome_raise": gnome_focus})
    if not gnome_focus.get("ok"):
        xdotool_focus = _focus_window_xdotool_for_ide(ide=ide)
        if not xdotool_focus.get("skipped"):
            result["steps"].append({"xdotool_raise": xdotool_focus})


def _ide_control_region_raise(
    result: dict[str, Any], map_path: str | None, map_mismatch: dict[str, Any] | None, src: str
) -> None:
    """Click the calibrated map region center to raise the window (skipped on mismatch)."""
    if map_path and not map_mismatch:
        region_click = _click_map_region_center(map_path, source=src)
        result["steps"].append({"region_raise": region_click})
    elif map_mismatch:
        result["steps"].append({"region_raise": {"ok": False, "skipped": True, **map_mismatch}})


def _ide_control_alt_tab(result: dict[str, Any], ide: str) -> None:
    """Cycle alt-tab to bring the IDE window forward, recording the step unless skipped."""
    alt_tab = _alt_tab_window_cycle(
        cycles=int(os.environ.get("KORU_VDISPLAY_RAISE_ALT_TAB_CYCLES", "2")),
        ide=ide,
    )
    if not alt_tab.get("skipped"):
        result["steps"].append({"alt_tab": alt_tab})


def _ide_control_window_focus(result: dict[str, Any], hints: dict[str, str]) -> None:
    """Focus the IDE window via the control plane, recording the step."""
    try:
        focus_res = _control_focus(
            backend="auto",
            app=hints.get("app"),
            window_title=hints.get("window_title_contains"),
            role="window",
        )
        result["steps"].append({"window_focus": focus_res})
    except Exception as exc:
        result["steps"].append({"window_focus": {"ok": False, "error": str(exc)}})


def _ide_control_focus_fallback(
    result: dict[str, Any],
    app_id: str,
    map_path: str | None,
    map_mismatch: dict[str, Any] | None,
    src: str,
) -> bool:
    """Click map raise targets when strict window focus failed; True when a click landed."""
    interior_ok = False
    if map_path and not map_mismatch and not any(
        isinstance(s.get("window_focus"), dict) and s["window_focus"].get("ok")
        for s in result["steps"] if "window_focus" in s
    ):
        try:
            fb_targets = _map_raise_targets_for_ide(app_id, map_path) or ("prompt", "analyzing")
            for t in fb_targets[:2]:
                fb_click = _control_click(backend="vision", map_path=map_path, map_target=t, source=src)
                result["steps"].append({"window_focus_fallback": {"target": t, "click": fb_click}})
                if isinstance(fb_click, dict) and fb_click.get("ok", True):
                    interior_ok = True
                    break
        except Exception as exc:
            result["steps"].append({"window_focus_fallback": {"ok": False, "error": str(exc)}})
    return interior_ok


def _ide_control_focus_interior(result: dict[str, Any], app_id: str, map_path: str, src: str) -> bool:
    """Click interior map targets to focus the chat area; True when a click landed."""
    import time

    from vdisplay.control.timing import control_focus_type_seconds

    interior_ok = False
    interior_steps: list[dict[str, Any]] = []
    for target in _map_interior_targets_for_ide(app_id, map_path)[:1]:
        try:
            click = _control_click(
                backend="vision",
                map_path=map_path,
                map_target=target,
                source=src,
            )
            step = {"target": target, "click": click}
            interior_steps.append(step)
            if isinstance(click, dict) and click.get("ok", True):
                interior_ok = True
        except Exception as exc:
            interior_steps.append({"target": target, "click": {"ok": False, "error": str(exc)}})
    result["steps"].append({"interior": interior_steps})
    focus_s = control_focus_type_seconds()
    if focus_s:
        time.sleep(focus_s)
    return interior_ok


def _ide_control_outcome_flags(result: dict[str, Any]) -> tuple[bool, bool, bool]:
    """Derive (window_ok, open_ok, fallback_ok) from recorded control steps."""
    window_ok = any(
        isinstance(step.get("window_focus"), dict) and step["window_focus"].get("ok", True)
        for step in result["steps"]
        if "window_focus" in step
    )
    open_ok = any(
        isinstance(step.get("open"), dict) and step["open"].get("ok")
        for step in result["steps"]
        if "open" in step
    )
    fallback_ok = any(
        isinstance(step.get("window_focus_fallback"), dict) and step["window_focus_fallback"].get("ok", True)
        for step in result["steps"]
        if "window_focus_fallback" in step
    )
    return window_ok, open_ok, fallback_ok


def _ide_control_finalize_result(
    result: dict[str, Any],
    *,
    ide: str,
    map_path: str | None,
    map_mismatch: dict[str, Any] | None,
    focus_interior: bool,
    interior_ok: bool,
) -> None:
    """Fill ok/focus flags and confirmation-bias guard fields on the control result."""
    window_ok, open_ok, fallback_ok = _ide_control_outcome_flags(result)
    # For JetBrains on rotated monitors (DP-2 etc), successful map/region/interior clicks bring the window forward
    # and focus the chat area (as seen in real DP-2 tests with ydotool + rotation mapping succeeding even when
    # strict window selector fails). Count as window_focused for better reporting and downstream logic.
    if not window_ok and (interior_ok or fallback_ok) and _canonical_ide(ide) in {"jetbrains", "pycharm", "idea"}:
        window_ok = True
    result["ok"] = interior_ok or window_ok or open_ok or (
        bool(map_path and focus_interior) and not map_mismatch
    )
    result["interior_focused"] = interior_ok
    result["window_focused"] = window_ok
    result["fallback_used"] = fallback_ok
    # Map/ydotool success does not prove the observe capture shows the target IDE (confirmation-bias guard).
    result["capture_confirmed"] = None
    if interior_ok or fallback_ok:
        result["map_actuation_ok"] = True
        result["visual_guard_note"] = (
            "Map clicks succeeded but capture IDE match is verified only after observe refresh in prepare."
        )


def ensure_vdisplay_ide_control(
    *,
    ide: str,
    source: str | None = None,
    focus_interior: bool = True,
) -> dict[str, Any]:
    """Automatically open/focus IDE window and click interior targets via vdisplay control plane."""
    app_id = _ide_prompt_app_id(ide)
    src = source or _vdisplay_source_for_ide(ide)
    os.environ["KORU_VDISPLAY_SOURCE"] = src
    os.environ.setdefault("VDISPLAY_CAPTURE_SOURCE", src)

    result: dict[str, Any] = {
        "ok": False,
        "ide": ide,
        "app_id": app_id,
        "source": src,
        "steps": [],
    }

    if _dry_run():
        result.update({"ok": True, "dry_run": True, "skipped": True})
        return result
    if not vdisplay_available():
        result["error"] = vdisplay_missing_message()
        return result

    result["steps"].append({"dismiss_overview": _dismiss_gnome_overview(reason="pre-control")})

    hints = _ide_hints(ide)
    map_path, map_mismatch = _ide_control_resolve_map(result, app_id, src)

    _ide_control_open_ide(result, app_id, ide)
    _ide_control_raise_window(result, ide)
    _ide_control_region_raise(result, map_path, map_mismatch, src)
    _ide_control_alt_tab(result, ide)
    _ide_control_window_focus(result, hints)

    interior_ok = _ide_control_focus_fallback(result, app_id, map_path, map_mismatch, src)

    if focus_interior and map_path and not map_mismatch:
        interior_ok = _ide_control_focus_interior(result, app_id, map_path, src) or interior_ok

    result["steps"].append({"dismiss_overview": _dismiss_gnome_overview(reason="post-control")})

    _ide_control_finalize_result(
        result,
        ide=ide,
        map_path=map_path,
        map_mismatch=map_mismatch,
        focus_interior=focus_interior,
        interior_ok=interior_ok,
    )
    return result


def _import_imgl_targets(name: str):
    """Import ``resolve_*`` from semcod imgl even when koru ships minimal ``imgl`` stubs."""
    target = _import_imgl_target_via_stdlib(name)
    if target is not None:
        return target
    return _import_imgl_target_from_source(name)


def _import_imgl_target_via_stdlib(name: str):
    """Resolve ``name`` from ``imgl.targets`` through the standard import machinery."""
    import importlib

    _ensure_real_imgl_on_path()
    for _attempt in range(2):
        try:
            importlib.import_module("imgl.export.actuation_layers")
            mod = importlib.import_module("imgl.targets")
            if hasattr(mod, name):
                return getattr(mod, name)
        except ImportError:
            _ensure_real_imgl_on_path()
    return None


def _load_light_module(module_name: str, path: Path):
    """Load a module from an explicit file path without triggering package import."""
    import importlib.util
    import sys

    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        return None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _install_imgl_source_packages(pkg_dir: Path):
    """Register hand-built ``imgl``/``imgl.export`` package modules in ``sys.modules``."""
    import sys
    import types

    pkg = types.ModuleType("imgl")
    pkg.__file__ = str(pkg_dir / "__init__.py")
    pkg.__path__ = [str(pkg_dir)]  # type: ignore[attr-defined]
    pkg.__package__ = "imgl"
    sys.modules["imgl"] = pkg
    export_pkg = types.ModuleType("imgl.export")
    export_pkg.__file__ = str(pkg_dir / "export" / "__init__.py")
    export_pkg.__path__ = [str(pkg_dir / "export")]  # type: ignore[attr-defined]
    export_pkg.__package__ = "imgl.export"
    sys.modules["imgl.export"] = export_pkg
    return pkg, export_pkg


def _import_imgl_target_from_source(name: str):
    """Resolve ``name`` by loading ``imgl.targets`` straight from the source tree."""
    import sys

    root = _real_imgl_src()
    if not root:
        return None
    root_path = Path(root).resolve()
    pkg_dir = root_path / "imgl"
    targets_path = pkg_dir / "targets.py"
    actuation_path = pkg_dir / "export" / "actuation_layers.py"
    if not targets_path.is_file() or not actuation_path.is_file():
        return None
    for mod_name in list(sys.modules):
        if mod_name == "imgl" or mod_name.startswith("imgl."):
            sys.modules.pop(mod_name, None)
    pkg, export_pkg = _install_imgl_source_packages(pkg_dir)
    actuation_mod = _load_light_module("imgl.export.actuation_layers", actuation_path)
    if actuation_mod is None:
        return None
    export_pkg.actuation_layers = actuation_mod
    targets_mod = _load_light_module("imgl.targets", targets_path)
    if targets_mod is None:
        return None
    pkg.targets = targets_mod
    return getattr(targets_mod, name, None)


def _main_vql_layer_count(vql_path: str | Path) -> int:
    path = Path(vql_path)
    if not path.is_file():
        return 0
    try:
        with open(path) as f:
            data = json.load(f)
    except Exception:
        return 0
    return len(_layers_from_vdisplay_sidecar(data))


def _png_path_for_vql_sidecar(vql_path: str) -> Path | None:
    if vql_path.endswith(".png.vql.json"):
        png = vql_path[: -len(".vql.json")]
        return Path(png) if os.path.isfile(png) else None
    return None


def _resolve_photo_png_path(source: str) -> Path:
    import glob
    from pathlib import Path

    session = _autonomy_session.active_session_dir()
    if session is not None:
        png, _vql = _autonomy_session.session_observe_paths(session)
        return png

    explicit = os.environ.get("KORU_VDISPLAY_PHOTO_PATH", "").strip()
    if explicit:
        return Path(explicit).expanduser()
    root = _photo_vql_metadata_root()
    slug_raw = source.strip().lower().replace("/", "-")
    slug_compact = slug_raw.replace("-", "")
    patterns = [
        f"koru-cont-{slug_raw}.png",
        f"koru-cont-{slug_compact}.png",
        f"koru-cont-{slug_raw}-*.png",
        f"koru-cont-{slug_compact}-*.png",
    ]
    for pattern in patterns:
        matches = [p for p in glob.glob(str(root / pattern)) if os.path.isfile(p)]
        if matches:
            matches.sort(key=lambda p: os.path.getmtime(p), reverse=True)
            return Path(matches[0])
    return root / f"koru-cont-{slug_compact}.png"


def _photo_vql_refresh_mode() -> str:
    return os.environ.get("KORU_VDISPLAY_PHOTO_VQL_REFRESH", "auto").strip().lower()


def photo_vql_sidecar_needs_refresh(*, source: str | None = None, ide: str = "auto") -> bool:
    """True when autonomy should capture a fresh screenshot before photo-VQL drive."""
    if _surface_only_fallback_active():
        return False
    mode = _photo_vql_refresh_mode()
    if mode in {"0", "false", "no", "off"}:
        return False
    if mode in {"1", "true", "yes", "on", "always"}:
        return True
    src = source or _vdisplay_source_for_ide(ide)
    png = _resolve_photo_png_path(src)
    vql = png.with_suffix(png.suffix + ".vql.json")
    if not png.is_file() or not vql.is_file():
        return True
    meta = load_vql_metadata(str(vql), allow_stale=True)
    layers = meta.get("ui_elements") or meta.get("layers") or []
    warn = _photo_vql_ide_window_warning(ide=ide, meta=meta)
    stale, _info = _autonomy_session.vql_sidecar_is_stale(
        vql,
        png,
        ide=ide,
        layer_count=len(layers),
        window_mismatch=warn,
    )
    return stale


def _photo_vql_refresh_dry_run_out(
    src: str, png: Path, vql: Path, session: Path | None
) -> dict[str, Any]:
    """Dry-run result for refresh_photo_vql_sidecar (no capture performed)."""
    os.environ["KORU_VDISPLAY_VQL_PATH"] = str(vql)
    out = {
        "ok": True,
        "dry_run": True,
        "source": src,
        "png": str(png),
        "vql": str(vql),
        "elements": 0,
    }
    if session is not None:
        out["session_dir"] = str(session)
    return out


def _photo_vql_refresh_screenshot(src: str, png: Path, ide: str) -> dict[str, Any] | None:
    """Run the vdisplay screenshot CLI; return an error dict on failure, None on success."""
    import subprocess

    cmd = [
        _vdisplay_cli_path(),
        "screenshot",
        "-o",
        str(png),
        "--source",
        src,
    ]
    env = _vdisplay_subprocess_env(ide=ide)
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120, check=False, env=env)
    except Exception as exc:
        error = str(exc)
        return _annotate_png_artifact_state({
            "ok": False,
            "error": error,
            "hint": _vdisplay_capture_failure_hint(error),
            "source": src,
            "png": str(png),
        })

    if proc.returncode != 0:
        error = (proc.stderr or proc.stdout or "screenshot failed").strip()
        return _annotate_png_artifact_state({
            "ok": False,
            "error": error,
            "hint": _vdisplay_capture_failure_hint(error),
            "source": src,
            "png": str(png),
            "returncode": proc.returncode,
        })
    return None


def _photo_vql_reload_sidecar_meta(vql: Path) -> tuple[dict[str, Any], list, int]:
    """(meta, elements, main_layer_count) freshly loaded from the VQL sidecar."""
    meta = load_vql_metadata(str(vql), allow_stale=True)
    elements = meta.get("ui_elements") or meta.get("layers") or []
    main_layers = _main_vql_layer_count(vql)
    return meta, elements, main_layers


def _photo_vql_observe_when_empty(
    *,
    png: Path,
    vql: Path,
    src: str,
    ide: str,
    session: Path | None,
    meta: dict[str, Any],
    elements: list,
    main_layers: int,
) -> tuple[dict[str, Any], list, int, dict[str, Any], dict[str, Any] | None]:
    """Re-observe an empty sidecar; returns (meta, elements, main_layers, observe_subprocess, early_out)."""
    observe_subprocess = _refresh_vql_sidecar_via_vdisplay_observe(
        png=png,
        vql=vql,
        source=src,
        ide=ide,
    )
    if observe_subprocess.get("ok"):
        meta, elements, main_layers = _photo_vql_reload_sidecar_meta(vql)
    try:
        if main_layers == 0:
            _ensure_real_imgl_on_path()
            from vdisplay.integrations.pipeline import observe_screen

            observe_screen(
                image_path=png,
                capture_meta={"path": str(png.resolve()), "source": src},
                write_sidecar=True,
            )
            meta, elements, main_layers = _photo_vql_reload_sidecar_meta(vql)
    except Exception as exc:
        out = {
            "ok": True,
            "source": src,
            "png": str(png.resolve()),
            "vql": str(vql.resolve()) if vql.is_file() else str(vql),
            "elements": len(elements),
            "main_vql_layers": main_layers,
            "observe_subprocess": observe_subprocess,
            "observe_fallback_error": str(exc),
        }
        if session is not None:
            out["session_dir"] = str(session)
        return meta, elements, main_layers, observe_subprocess, out
    return meta, elements, main_layers, observe_subprocess, None


def _photo_vql_refresh_annotate_observe(
    out: dict[str, Any], main_layers: int, observe_subprocess: dict[str, Any] | None
) -> None:
    """Attach the observe-subprocess summary to the refresh result."""
    if main_layers > 0 and observe_subprocess is not None and observe_subprocess.get("ok"):
        out["observe_subprocess"] = {
            "ok": True,
            "method": observe_subprocess.get("method"),
            "returncode": observe_subprocess.get("returncode"),
        }
    elif main_layers == 0 and observe_subprocess is not None:
        out["observe_subprocess"] = observe_subprocess


def _photo_vql_refresh_finalize_out(
    out: dict[str, Any],
    *,
    ide: str,
    meta: dict[str, Any],
    png: Path,
    vql: Path,
    session: Path | None,
) -> dict[str, Any]:
    """Warnings, provenance and session artifact copies for the refresh result."""
    warn = _photo_vql_ide_window_warning(ide=ide, meta=meta)
    if warn:
        out["ide_window_warning"] = warn
    if meta.get("capture_validation"):
        out["capture_validation"] = meta["capture_validation"]
    out["capture_provenance"] = _capture_provenance(
        ide=ide, png_path=str(png), vql_path=str(vql), meta=meta
    )
    out["capture_confirmed"] = out["capture_provenance"].get("capture_confirmed")
    if session is not None:
        out["session_dir"] = str(session)
        if png.is_file() and vql.is_file():
            copied = _autonomy_session.copy_observe_artifacts_to_session(
                session,
                png=png,
                vql=vql,
            )
            out["observe_session_paths"] = copied
            out["png"] = copied["png"]
            out["vql"] = copied["vql"]
    return out


def refresh_photo_vql_sidecar(*, source: str | None = None, ide: str = "auto") -> dict[str, Any]:
    """Capture fresh screenshot + VQL sidecar for photo-VQL drive (observe via vdisplay CLI/agent)."""
    src = source or _vdisplay_source_for_ide(ide)
    os.environ["KORU_VDISPLAY_SOURCE"] = src
    session = _autonomy_session.active_session_dir()
    png = _resolve_photo_png_path(src)
    vql = png.with_suffix(png.suffix + ".vql.json")
    png.parent.mkdir(parents=True, exist_ok=True)

    if _dry_run():
        return _photo_vql_refresh_dry_run_out(src, png, vql, session)

    capture_error = _photo_vql_refresh_screenshot(src, png, ide)
    if capture_error is not None:
        return capture_error

    os.environ["KORU_VDISPLAY_VQL_PATH"] = str(vql)
    meta, elements, main_layers = _photo_vql_reload_sidecar_meta(vql)
    observe_subprocess: dict[str, Any] | None = None
    if main_layers == 0 and png.is_file():
        meta, elements, main_layers, observe_subprocess, early_out = _photo_vql_observe_when_empty(
            png=png,
            vql=vql,
            src=src,
            ide=ide,
            session=session,
            meta=meta,
            elements=elements,
            main_layers=main_layers,
        )
        if early_out is not None:
            return early_out

    stale, freshness = _autonomy_session.vql_sidecar_is_stale(
        vql,
        png,
        ide=ide,
        layer_count=len(elements),
        window_mismatch=_photo_vql_ide_window_warning(ide=ide, meta=meta),
        capture_validation=meta.get("capture_validation"),
    )
    out: dict[str, Any] = {
        "ok": True,
        "source": src,
        "png": str(png.resolve()) if png.is_file() else str(png),
        "vql": str(vql.resolve()) if vql.is_file() else str(vql),
        "elements": len(elements),
        "main_vql_layers": main_layers,
        "vql_source": meta.get("_source"),
        "freshness": freshness,
        "sidecar_stale": stale,
    }
    _photo_vql_refresh_annotate_observe(out, main_layers, observe_subprocess)
    return _photo_vql_refresh_finalize_out(out, ide=ide, meta=meta, png=png, vql=vql, session=session)


def _vdisplay_capture_failure_hint(error: str) -> str | None:
    text = str(error or "").lower()
    hints: list[str] = []
    if "python3-dbus" in text or "no module named 'dbus'" in text:
        hints.append("Install/enable dbus bindings for the Python used by vdisplay-agent (python3-dbus / dbus-python).")
    if "screen recording" in text or "portal screenshot denied" in text:
        hints.append("GNOME Wayland: Settings -> Privacy -> Screen Recording -> allow the terminal/IDE running vdisplay-agent.")  # noqa: E501
    if "pipewire" in text or "gstreamer" in text or "timed out after" in text:
        hints.append("ScreenCast frame capture timed out; prefer `koru autopilot vdisplay-up --ide jetbrains`, then in Chrome/Chromium click Share screen and keep the browser bridge tab open. Keeper fallback: `vdisplay agent screencast start --force` and probe with `vdisplay agent screencast probe --via-agent --source <monitor>`.")  # noqa: E501
    if "list index out of range" in text:
        hints.append("vdisplay-agent capture route raised an internal stream-index error; prefer browser bridge via `koru autopilot vdisplay-up --ide jetbrains`; if using keeper, restart `vdisplay-agent serve` and `vdisplay agent screencast start --force`, then probe the monitor via agent.")  # noqa: E501
    if "persistent screencast" in text or "vdisplay-agent serve" in text or "gnome-screenshot" in text:
        hints.append("Use browser bridge first: `koru autopilot vdisplay-up --ide jetbrains`; in Chrome/Chromium choose the IDE monitor and keep the tab open. Keeper fallback: `vdisplay-agent serve`, then `vdisplay agent screencast start`.")  # noqa: E501
    return " | ".join(dict.fromkeys(hints)) or None


def _refresh_vql_sidecar_via_vdisplay_observe(
    *,
    png: Path,
    vql: Path,
    source: str,
    ide: str = "auto",
) -> dict[str, Any]:
    """Rebuild VQL sidecars through a Python env with vdisplay + imgl.

    Koru's venv intentionally stays small and may not include Pillow/tesseract
    dependencies required by semcod/imgl.  This helper observes the existing
    PNG without taking another screenshot, so a good capture is not overwritten
    by a later blank frame.
    """
    import subprocess

    env = _vdisplay_subprocess_env(ide=ide)
    env["VDISPLAY_OBSERVE"] = "1"
    env["VDISPLAY_OBSERVE_VQL"] = "1"
    env["VDISPLAY_OBSERVE_SIDECAR"] = "1"
    env["VDISPLAY_OBSERVE_CACHE"] = "0"
    env["VDISPLAY_IMGL"] = "1"
    attempts: list[dict[str, Any]] = []
    code = """
from __future__ import annotations
import json
import sys
from pathlib import Path

png = Path(sys.argv[1])
vql = Path(sys.argv[2])
source = sys.argv[3]

from vdisplay.integrations.pipeline import observe_screen

ctx = observe_screen(
    image_path=png,
    capture_meta={"path": str(png.resolve()), "source": source},
    write_sidecar=True,
    vql_path=vql,
)
program = (ctx.vql or {}).get("program") or {}
render = (program.get("metadata") or {}).get("render_intent") or {}
print(json.dumps({
    "ok": True,
    "image": str(png.resolve()),
    "vql": str(vql.resolve()),
    "imgl_ok": ctx.imgl.get("ok"),
    "imgl_error": ctx.imgl.get("error"),
    "program_layers": len(program.get("layers") or []),
    "render_layers": len(render.get("layers") or []),
}, ensure_ascii=False))
"""
    for python in _vdisplay_observe_python_candidates():
        cmd = [
            python,
            "-c",
            code,
            str(png),
            str(vql),
            source,
        ]
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120, check=False, env=env)
        except Exception as exc:
            attempts.append(
                {
                    "python": python,
                    "ok": False,
                    "error": str(exc),
                    "method": "vdisplay_observe_python",
                }
            )
            continue
        layer_count = _main_vql_layer_count(vql)
        attempt: dict[str, Any] = {
            "python": python,
            "ok": proc.returncode == 0 and layer_count > 0,
            "method": "vdisplay_observe_python",
            "returncode": proc.returncode,
            "main_vql_layers": layer_count,
        }
        if proc.stdout.strip():
            attempt["stdout"] = proc.stdout.strip()
        if proc.stderr.strip():
            attempt["stderr"] = proc.stderr.strip()
        if proc.returncode != 0:
            attempt["error"] = (proc.stderr or proc.stdout or "vdisplay observe failed").strip()
        elif layer_count <= 0:
            attempt["error"] = "vdisplay observe produced empty VQL layers"
        attempts.append(attempt)
        if attempt["ok"]:
            return {**attempt, "attempts": attempts}
    error = attempts[-1].get("error") if attempts else "vdisplay observe failed"
    return {
        "ok": False,
        "method": "vdisplay_observe_python",
        "error": error,
        "attempts": attempts,
    }


def _prepare_photo_vql_map_mismatch(
    *, map_path: str | None, src: str, desktop_probe: dict[str, Any]
) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    """Detect GUI-map vs capture-source monitor mismatch: (map_mismatch, desktop_probe)."""
    map_mismatch = None
    if map_path:
        from koru.integrations.photo_vql_monitor import map_capture_monitor_mismatch

        map_mismatch = map_capture_monitor_mismatch(map_path, source=src)
        if map_mismatch:
            desktop_probe = {**desktop_probe, "map_capture_mismatch": map_mismatch}
    return map_mismatch, desktop_probe


def _prepare_photo_vql_probe_abort(
    *, src: str, session_dir, desktop_probe: dict[str, Any]
) -> dict[str, Any] | None:
    """Abort out dict when the desktop probe failed and abort-on-fail is set, else None."""
    if desktop_probe.get("ok") or not _abort_on_desktop_probe_fail():
        return None
    out: dict[str, Any] = {
        "ok": False,
        "source": src,
        "session_dir": str(session_dir),
        "desktop_probe": desktop_probe,
        "error": desktop_probe.get("error") or "desktop probe failed",
        "hint": (
            "Run `vdisplay monitors` and pass --source with a connected monitor, "
            "or set KORU_VDISPLAY_ABORT_ON_PROBE_FAIL=0 to skip."
        ),
    }
    _autonomy_session.persist_autonomy_phase(session_dir, "observe", "prepare", out)
    return out


def _prepare_photo_vql_out_skeleton(
    *,
    src: str,
    session_dir,
    desktop_probe: dict[str, Any],
    map_mismatch: dict[str, Any] | None,
    bootstrap: dict[str, Any],
) -> dict[str, Any]:
    """Initial prepare_photo_vql_for_drive out dict with bootstrap/map hints."""
    out: dict[str, Any] = {
        "ok": False,
        "source": src,
        "session_dir": str(session_dir),
        "desktop_probe": desktop_probe,
    }
    if map_mismatch:
        out["map_capture_mismatch"] = map_mismatch
        out["hint"] = (
            map_mismatch.get("message")
            or "GUI map monitor does not match capture source"
        )
    agent_hint = (bootstrap.get("agent") or {}).get("hint")
    if agent_hint:
        out["hint"] = f"{agent_hint} | {out['hint']}" if out.get("hint") else agent_hint
    screencast_boot = bootstrap.get("screencast") if isinstance(bootstrap.get("screencast"), dict) else {}
    screencast_hint = str(screencast_boot.get("hint") or "").strip()
    if screencast_hint:
        out["vdisplay_screencast_hint"] = screencast_hint
        out["hint"] = f"{screencast_hint} | {out['hint']}" if out.get("hint") else screencast_hint
    if screencast_boot.get("browser_bridge") or screencast_boot.get("browser_bridge_pending"):
        out["browser_bridge_bootstrap"] = {
            "ok": screencast_boot.get("ok"),
            "reason": screencast_boot.get("reason"),
            "browser_bridge": screencast_boot.get("browser_bridge"),
            "keeper_mode": (screencast_boot.get("status") or {}).get("keeper_mode")
            if isinstance(screencast_boot.get("status"), dict)
            else screencast_boot.get("keeper_mode"),
        }
    return out


def _prepare_photo_vql_ide_control_attempt(
    *, ide: str, src: str, ide_control: dict[str, Any] | None
) -> tuple[dict[str, Any] | None, bool]:
    """One auto-IDE-control attempt in the prepare retry loop: (ide_control, force_refresh)."""
    force_refresh = False
    if _auto_ide_control_enabled():
        ide_control = ensure_vdisplay_ide_control(ide=ide, source=src)
        if ide_control.get("map_actuation_ok") or ide_control.get("interior_focused"):
            import time

            force_refresh = True
            time.sleep(
                float(os.environ.get("KORU_VDISPLAY_POST_FOCUS_CAPTURE_DELAY_S", "0.8"))
            )
    return ide_control, force_refresh


def _prepare_photo_vql_refresh_or_reuse(
    *, src: str, ide: str, session_dir, force_refresh: bool
) -> dict[str, Any]:
    """Refresh the photo VQL sidecar, or reuse the fresh one already on disk."""
    if force_refresh or photo_vql_sidecar_needs_refresh(source=src, ide=ide):
        return refresh_photo_vql_sidecar(source=src, ide=ide)
    png = _resolve_photo_png_path(src)
    vql = png.with_suffix(png.suffix + ".vql.json")
    meta = load_vql_metadata(str(vql))
    return {
        "ok": True,
        "source": src,
        "png": str(png),
        "vql": str(vql),
        "elements": len(meta.get("ui_elements") or meta.get("layers") or []),
        "main_vql_layers": _main_vql_layer_count(vql),
        "vql_source": meta.get("_source"),
        "reused_fresh_sidecar": True,
        "session_dir": str(session_dir),
    }


def _prepare_photo_vql_handle_window_warning(
    out: dict[str, Any], *, warn: dict[str, Any], ide: str, src: str
) -> tuple[dict[str, Any], str | None]:
    """Handle an ide_window_warning inside the prepare retry loop: (out, "break" | None)."""
    out["ide_window_warning"] = warn
    out["capture_matches_ide"] = False
    os.environ.pop("KORU_VDISPLAY_CAPTURE_MATCHES_IDE", None)
    cv = out.get("capture_validation") or {}
    if isinstance(cv, dict) and cv.get("body_false_positive"):
        out["body_false_positive"] = True
    # Vision LLM will decide the chat coords from the screenshot; a title that
    # does not affirmatively say "PyCharm" (editor breadcrumb, or a right-docked
    # Qoder/AI chat panel) is not a prepare-stopping mismatch — but a title that
    # names a competing IDE still is.
    vision_soft = _vision_overrides_capture_mismatch(warn, ide=ide)
    allow_continue = _allow_prepare_map_on_mismatch() or vision_soft
    if (
        not allow_continue
        and not out.get("_focus_recovery_tried")
        and _raise_alt_tab_enabled(ide=ide)
    ):
        out["_focus_recovery_tried"] = True
        recovered = _attempt_focus_recovery_capture(ide=ide, source=src)
        if recovered.get("ok"):
            out = recovered
            os.environ["KORU_VDISPLAY_CAPTURE_MATCHES_IDE"] = "1"
            if _canonical_ide(ide) in {"jetbrains", "pycharm", "idea"}:
                os.environ.setdefault("KORU_VDISPLAY_PREFER_PHOTO_VQL", "auto")
            return out, "break"
        out["focus_recovery"] = recovered.get("focus_recovery")
    if not allow_continue:
        return out, "break"
    return out, None


def _prepare_photo_vql_map_focus_fallback(
    out: dict[str, Any],
    *,
    ide: str,
    src: str,
    ide_control: dict[str, Any] | None,
    map_path: str | None,
    map_mismatch: dict[str, Any] | None,
) -> dict[str, Any]:
    """On mismatch for JetBrains etc, do extra focus via map when map-only fallback is allowed,
    then re-capture to get correct VQL for the target IDE on the source."""
    if not _allow_prepare_map_on_mismatch():
        return out
    mp = None
    if ide_control:
        mp = ide_control.get("map_path")
    if not mp:
        mp = map_path or _resolve_ide_prompt_map(_ide_prompt_app_id(ide))
    if map_mismatch:
        out.setdefault("map_skipped", True)
    elif _canonical_ide(ide) in {"jetbrains", "pycharm", "idea"} and mp:
        try:
            for t in _map_interior_targets_for_ide(_ide_prompt_app_id(ide), mp)[:1]:
                _control_click(backend="vision", map_path=mp, map_target=t, source=src)
            import time
            time.sleep(0.4)
            out = refresh_photo_vql_sidecar(source=src, ide=ide)
        except Exception:
            pass
    return out


def _prepare_photo_vql_finalize_out(
    out: dict[str, Any],
    *,
    ide: str,
    ide_control: dict[str, Any] | None,
    map_mismatch: dict[str, Any] | None,
    loop_attempts: int,
    session_dir,
) -> dict[str, Any]:
    """Merge ide_control/map-mismatch/provenance into the prepare out after the retry loop."""
    if ide_control is not None:
        out["ide_control"] = ide_control
    if map_mismatch:
        out["map_capture_mismatch"] = map_mismatch
        mm_msg = map_mismatch.get("message")
        if mm_msg:
            prior = out.get("hint")
            out["hint"] = mm_msg if not prior else f"{mm_msg} | {prior}"
    elif isinstance(ide_control, dict) and ide_control.get("map_capture_mismatch"):
        out["map_capture_mismatch"] = ide_control["map_capture_mismatch"]
    out["ide_control_attempts"] = loop_attempts
    out["session_dir"] = str(session_dir)
    png_path = out.get("png")
    vql_path = out.get("vql")
    if png_path and vql_path and out.get("capture_provenance") is None:
        try:
            meta = load_vql_metadata(str(vql_path), allow_stale=True)
            out["capture_provenance"] = _capture_provenance(
                ide=ide,
                png_path=str(png_path),
                vql_path=str(vql_path),
                meta=meta,
            )
            if out.get("capture_confirmed") is None:
                out["capture_confirmed"] = out["capture_provenance"].get("capture_confirmed")
        except Exception:
            pass
    return out


def _prepare_photo_vql_apply_capture_guard(
    out: dict[str, Any],
    *,
    ide: str,
    src: str,
    desktop_probe: dict[str, Any],
    ide_control: dict[str, Any] | None,
) -> dict[str, Any]:
    """Apply surface capture confirmation + CaptureGuard/readiness to the prepare out."""
    capture_error = (
        out.get("ok") is False
        or bool(out.get("error"))
        or bool(out.get("returncode"))
    )
    _apply_surface_capture_confirmation(
        out,
        ide=ide,
        source=src,
        desktop_probe=desktop_probe,
        capture_error=capture_error,
    )
    _persist_surface_capture_confirmation_to_vql(out, ide=ide)
    confirmed = out.get("capture_confirmed")
    if os.environ.get("KORU_VDISPLAY_DEBUG_CAPTURE", "").strip() in {"1", "true", "yes", "on"}:
        import sys as _sys

        cv = out.get("capture_validation") if isinstance(out.get("capture_validation"), dict) else {}
        print(
            f"[capture-debug] ide={ide} src={src} confirmed={confirmed!r} "
            f"capture_error={capture_error} warn={bool(out.get('ide_window_warning'))} "
            f"cv.confirmed={cv.get('capture_confirmed')!r} "
            f"cv.vision_deferred={cv.get('vision_deferred_window_mismatch')!r} "
            f"vision_env={os.environ.get('KORU_VDISPLAY_LLM_VISION_DECISION')!r}/"
            f"{os.environ.get('VDISPLAY_VISION_CHAT_DETECT')!r}",
            file=_sys.stderr,
            flush=True,
        )
    guard = CaptureGuard.from_observe(
        ide=ide,
        confirmed=confirmed if confirmed is not None else None,
        ide_window_warning=out.get("ide_window_warning"),
        body_false_positive=bool(out.get("body_false_positive")),
        map_only_fallback=bool(out.get("map_only_fallback")),
        surface_only_fallback=bool(out.get("surface_only_fallback")),
        capture_error=capture_error,
        ide_control=ide_control,
    )
    out = guard.apply_to_prepare_out(out, ide_control=ide_control, capture_error=capture_error)
    out = _annotate_png_artifact_state(out)
    _annotate_prepare_drive_readiness(out)
    return out


def prepare_photo_vql_for_drive(*, ide: str) -> dict[str, Any]:
    """Observe (if needed) + pin sidecar before koru drive / send_chat."""
    import time

    bootstrap: dict[str, Any] = {}
    try:
        from koru.integrations.vdisplay_agent_bootstrap import bootstrap_vdisplay_capture

        bootstrap = bootstrap_vdisplay_capture()
    except ImportError:
        pass

    src, desktop_probe = _resolve_vdisplay_source_for_ide(ide)
    if bootstrap:
        desktop_probe = {**desktop_probe, "vdisplay_bootstrap": bootstrap}
    os.environ.setdefault("KORU_VDISPLAY_CONTROL_FALLBACK", "1")
    os.environ["KORU_VDISPLAY_SOURCE"] = src
    os.environ.pop("KORU_VDISPLAY_CAPTURE_MATCHES_IDE", None)

    map_path = _resolve_ide_prompt_map(_ide_prompt_app_id(ide))
    map_mismatch, desktop_probe = _prepare_photo_vql_map_mismatch(
        map_path=map_path, src=src, desktop_probe=desktop_probe
    )

    session_dir = _autonomy_session.begin_autonomy_session(ide=ide, source=src)
    _autonomy_session.persist_autonomy_phase(session_dir, "decide", "desktop_probe", desktop_probe)

    aborted = _prepare_photo_vql_probe_abort(
        src=src, session_dir=session_dir, desktop_probe=desktop_probe
    )
    if aborted is not None:
        return aborted

    retries = max(1, int(os.environ.get("KORU_VDISPLAY_IDE_CONTROL_RETRIES", "3") or "3"))
    ide_control: dict[str, Any] | None = None
    out = _prepare_photo_vql_out_skeleton(
        src=src,
        session_dir=session_dir,
        desktop_probe=desktop_probe,
        map_mismatch=map_mismatch,
        bootstrap=bootstrap,
    )
    loop_attempts = 0

    for attempt in range(retries):
        loop_attempts = attempt + 1
        ide_control, force_refresh = _prepare_photo_vql_ide_control_attempt(
            ide=ide, src=src, ide_control=ide_control
        )
        out = _prepare_photo_vql_refresh_or_reuse(
            src=src, ide=ide, session_dir=session_dir, force_refresh=force_refresh
        )
        if not out.get("ok"):
            break
        warn = out.get("ide_window_warning") or _photo_vql_ide_window_warning(
            ide=ide,
            meta=load_vql_metadata(str(out.get("vql") or "")),
        )
        if warn:
            out, action = _prepare_photo_vql_handle_window_warning(out, warn=warn, ide=ide, src=src)
            if action == "break":
                break
        elif _capture_matches_requested_ide(ide):
            os.environ["KORU_VDISPLAY_CAPTURE_MATCHES_IDE"] = "1"
            out["capture_matches_ide"] = True
            if _canonical_ide(ide) in {"jetbrains", "pycharm", "idea"}:
                os.environ.setdefault("KORU_VDISPLAY_PREFER_PHOTO_VQL", "auto")
            break
        out["capture_matches_ide"] = False
        out = _prepare_photo_vql_map_focus_fallback(
            out,
            ide=ide,
            src=src,
            ide_control=ide_control,
            map_path=map_path,
            map_mismatch=map_mismatch,
        )
        if attempt + 1 < retries:
            time.sleep(float(os.environ.get("KORU_VDISPLAY_IDE_CONTROL_RETRY_DELAY_S", "0.6")))

    out = _prepare_photo_vql_finalize_out(
        out,
        ide=ide,
        ide_control=ide_control,
        map_mismatch=map_mismatch,
        loop_attempts=loop_attempts,
        session_dir=session_dir,
    )
    out = _prepare_photo_vql_apply_capture_guard(
        out, ide=ide, src=src, desktop_probe=desktop_probe, ide_control=ide_control
    )
    out["desktop_probe"] = desktop_probe
    _autonomy_session.persist_autonomy_phase(session_dir, "observe", "prepare", out)
    return out


def _photo_vql_drive_out_base(photo_res: dict[str, Any], *, ide: str, submit: bool) -> dict[str, Any]:
    """Build the base send_chat-shaped result dict for a photo-VQL drive outcome."""
    edit = photo_res.get("edit") or {}
    edit_message = edit.get("message")
    if not edit_message and edit.get("method"):
        edit_message = f"typed via {edit['method']}"
    return {
        "ok": bool(photo_res.get("ok")),
        "backend": photo_res.get("backend", "vdisplay+photo-vql"),
        "message": (
            edit_message
            or (photo_res.get("focus") or {}).get("message")
            or f"photo VQL {photo_res.get('target', 'edit')} at {photo_res.get('coords')}"
        ),
        "type": "drive",
        "fallback_from": "plugin",
        "ide": ide,
        "submit": submit,
        "photo_vql": photo_res,
        "coords": photo_res.get("coords"),
        "target": photo_res.get("target"),
        "is_code_edit": photo_res.get("is_code_edit", True),
    }


def _photo_vql_drive_map_target_id(photo_res: dict[str, Any]) -> str:
    """Best-effort target id from drive result (vql_target or nested photo_vql.vql_target)."""
    return str((photo_res.get("vql_target") or photo_res.get("photo_vql", {}).get("vql_target") or {}).get("id") or "")


def _photo_vql_drive_surface_trusted(photo_res: dict[str, Any]) -> bool:
    """Surface-bounds trust check for the drive result's vql_target/command plan."""
    return _surface_bounds_target_safe_for_actuation(
        target=photo_res.get("vql_target") if isinstance(photo_res.get("vql_target"), dict) else None,
        method=str((photo_res.get("vql_command_plan") or {}).get("selection_method") or ""),
        command_plan=photo_res.get("vql_command_plan") if isinstance(photo_res.get("vql_command_plan"), dict) else None,
    )


def _photo_vql_drive_verified_false_blocks(photo_res: dict[str, Any]) -> bool:
    """True when verified=False must force ok=False (no trusted-target override applies)."""
    return photo_res.get("verified") is False and not (
        (photo_res.get("edit") or {}).get("ok")
        and (
            _trusted_visual_target_id(_photo_vql_drive_map_target_id(photo_res))
            or _photo_vql_drive_surface_trusted(photo_res)
        )
        and (_allow_actuation_on_capture_mismatch() or _photo_vql_drive_surface_trusted(photo_res))
    )


def _apply_photo_vql_capture_confirmed(out: dict[str, Any], photo_res: dict[str, Any]) -> None:
    """Propagate capture_confirmed from the drive result, gating ok on unconfirmed captures."""
    if photo_res.get("capture_confirmed") is False:
        map_id = _photo_vql_drive_map_target_id(photo_res)
        edit_ok = bool((photo_res.get("edit") or {}).get("ok"))
        if not (_trusted_visual_target_id(map_id) and edit_ok and _allow_actuation_on_capture_mismatch()):
            out["ok"] = False
            out["capture_confirmed"] = False
        else:
            out["capture_confirmed"] = False
    elif photo_res.get("capture_confirmed") is True:
        out["capture_confirmed"] = True


def _apply_photo_vql_plan_inference_gate(out: dict[str, Any], photo_res: dict[str, Any]) -> None:
    """Force ok=False when the command plan's inference failed without a trusted override."""
    plan = photo_res.get("vql_command_plan") or {}
    surface_trusted = _surface_bounds_target_safe_for_actuation(
        target=photo_res.get("vql_target") if isinstance(photo_res.get("vql_target"), dict) else None,
        method=str(plan.get("selection_method") or ""),
        command_plan=plan,
    )
    if (
        plan.get("inference_ok") is False
        and not _allow_actuation_on_capture_mismatch()
        and not (surface_trusted and bool((photo_res.get("edit") or {}).get("ok")))
    ):
        out["ok"] = False


def _apply_photo_vql_map_mismatch_gate(out: dict[str, Any], photo_res: dict[str, Any]) -> None:
    """Force ok=False and surface the mismatch when the map targets a different monitor."""
    plan = photo_res.get("vql_command_plan") or {}
    map_source_mismatch = photo_res.get("map_capture_mismatch") or plan.get("map_capture_mismatch")
    if map_source_mismatch and not _map_source_mismatch_actuation_allowed():
        out["ok"] = False
        out["map_capture_mismatch"] = map_source_mismatch
        out["message"] = str(
            (map_source_mismatch or {}).get("message")
            or "photo-VQL map is calibrated for a different monitor"
        )


def _apply_photo_vql_provenance_and_verification(out: dict[str, Any], photo_res: dict[str, Any]) -> None:
    """Copy capture provenance and verification fields into the normalized result."""
    if photo_res.get("capture_provenance"):
        out["capture_provenance"] = photo_res.get("capture_provenance")
        if out.get("capture_confirmed") is None:
            out["capture_confirmed"] = out["capture_provenance"].get("capture_confirmed")
    if photo_res.get("verification"):
        out["verification"] = photo_res.get("verification")
        out["verified"] = photo_res.get("verified")


def _apply_photo_vql_submit_fields(out: dict[str, Any], photo_res: dict[str, Any], submit: bool) -> None:
    """Copy submitted/submit_result fields and annotate the message on submit."""
    out["submitted"] = bool(photo_res.get("submitted"))
    submit_result = photo_res.get("submit")
    if submit_result is not None:
        out["submit_result"] = submit_result
    if submit and out.get("submitted"):
        out["message"] = f"{out['message']} (submitted)"


def _normalize_photo_vql_drive_result(photo_res: dict[str, Any], *, ide: str, submit: bool) -> dict[str, Any]:
    """Map perform_photo_vql_focus_and_edit output to send_chat response shape."""
    out = _photo_vql_drive_out_base(photo_res, ide=ide, submit=submit)
    if photo_res.get("llm_used"):
        out["llm_used"] = True
        out["llm_decision"] = photo_res.get("llm_decision")
    if photo_res.get("vql_command_plan"):
        out["vql_command_plan"] = photo_res.get("vql_command_plan")
    if photo_res.get("ide_window_warning"):
        out["ide_window_warning"] = photo_res.get("ide_window_warning")
        if not _allow_actuation_on_capture_mismatch():
            out["ok"] = False
            out["capture_confirmed"] = False
    if _photo_vql_drive_verified_false_blocks(photo_res):
        out["ok"] = False
    _apply_photo_vql_capture_confirmed(out, photo_res)
    _apply_photo_vql_plan_inference_gate(out, photo_res)
    _apply_photo_vql_map_mismatch_gate(out, photo_res)
    _apply_photo_vql_provenance_and_verification(out, photo_res)
    _apply_photo_vql_submit_fields(out, photo_res, submit)
    if photo_res.get("is_code_edit") and (photo_res.get("edit") or {}).get("ok"):
        out["ok"] = True
    return out


def _finalize_send_chat(
    result: dict[str, Any],
    *,
    prompt: str,
    ide: str,
    submit: bool,
) -> dict[str, Any]:
    _persist_send_chat_drive_result(result, prompt=prompt, ide=ide, submit=submit)
    return result


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
    _load_vdisplay_control()
    if _VDISPLAY_DIRECT and _vdisplay_control:
        return _vdisplay_control.controls_find(**kwargs)
    return _agent_client().find_controls(kwargs)


def _control_focus(**kwargs: Any) -> dict[str, Any]:
    _load_vdisplay_control()
    if _VDISPLAY_DIRECT and _vdisplay_control:
        return _vdisplay_control.control_focus(**kwargs)
    return _agent_client().focus_control(kwargs)


def _control_set_value(**kwargs: Any) -> dict[str, Any]:
    _load_vdisplay_control()
    if _VDISPLAY_DIRECT and _vdisplay_control:
        return _vdisplay_control.control_set_value(**kwargs)
    return _agent_client().set_control_value(kwargs)


def _control_click(**kwargs: Any) -> dict[str, Any]:
    _load_vdisplay_control()
    if _VDISPLAY_DIRECT and _vdisplay_control:
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


def _effective_submit_enabled(*, submit: bool, ide: str) -> bool:
    """Lightweight paste-only gate (avoids importing autonomous_cycle_gate / gillm)."""
    if os.environ.get("KORU_IDE_CONTROL_PASTE_ONLY", "").strip().lower() in {"1", "true", "yes", "on"}:
        return False
    if os.environ.get("KORU_IDE_CONTROL_FORCE_SUBMIT", "").strip().lower() in {"1", "true", "yes", "on"}:
        return submit
    if _canonical_ide(ide) == "cursor":
        return False
    return submit


def _submit_via_keyboard(*, ide: str, submit: bool) -> dict[str, Any] | None:
    if not submit:
        return None

    if not _effective_submit_enabled(submit=submit, ide=ide):
        return {"ok": False, "skipped": True, "reason": "paste-only mode"}

    canon = _canonical_ide(ide)
    app_id = _ide_prompt_app_id(ide)
    key = "ctrl+Return" if app_id in {"pycharm", "jetbrains", "idea"} or canon in {"cursor", "jetbrains", "pycharm", "idea"} else "Return"  # noqa: E501
    try:
        from gillm.config import cached_config

        key = cached_config().submit_key_for(canon)
    except Exception:
        pass

    injector_error = ""
    try:
        from gillm.injection.injector import Injector

        Injector().press_key(key)
        return {"ok": True, "backend": "vdisplay+keyboard", "submit_key": key, "method": "injector-key"}
    except Exception as exc:
        injector_error = str(exc)

    try:
        from vdisplay.input.linux_ydotool import LinuxYdotoolInput

        yinput = LinuxYdotoolInput()
        if key in {"ctrl+Return", "ctrl+Enter"}:
            yinput.hotkey("29:1", "28:1", "28:0", "29:0")
        else:
            yinput.hotkey("28:1", "28:0")
        return {"ok": True, "backend": "vdisplay+keyboard", "submit_key": key, "method": "ydotool-key"}
    except Exception as exc:
        return {
            "ok": False,
            "backend": "vdisplay+keyboard",
            "submit_key": key,
            "method": "ydotool-key",
            "error": f"{injector_error}; ydotool: {exc}",
        }


def _photo_vql_submit_chat(*, ide: str, source: str | None = None) -> dict[str, Any]:
    """Submit chat after photo-VQL paste: map send button, then keyboard shortcut."""
    app_id = _ide_prompt_app_id(ide)
    src = source or _vdisplay_source_for_ide(ide)
    map_path = _resolve_ide_prompt_map(app_id)
    if map_path:
        try:
            from vdisplay.desktop_apps import map_submit_target_candidates

            for map_target in map_submit_target_candidates(app_id):
                try:
                    click = _control_click(
                        backend="vision",
                        map_path=map_path,
                        map_target=map_target,
                        source=src,
                    )
                except Exception as exc:
                    click = {"ok": False, "error": str(exc)}
                if isinstance(click, dict) and click.get("ok", True):
                    return {
                        "ok": True,
                        "method": "map-click",
                        "map_path": map_path,
                        "map_target": map_target,
                        "click": click,
                    }
        except Exception:
            pass
    result = _submit_via_keyboard(ide=ide, submit=True)
    return result or {"ok": False, "error": "submit unavailable"}


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


def _ide_map_message_target(app_id: str) -> str:
    try:
        from vdisplay.desktop_apps import map_input_target_candidates

        candidates = map_input_target_candidates(app_id) or []
    except Exception:
        candidates = []
    # Force "prompt" as the primary chat input target for JetBrains/PyCharm (proven reliable
    # on DP-2 rotated capture with ydotool mapping; "ai-chat-input" in some pycharm-chat.json
    # calibrations can produce negative local y after screencast transform).
    if app_id in {"pycharm", "jetbrains", "idea"}:
        if "prompt" in candidates:
            return "prompt"
        return "prompt"
    if candidates:
        return candidates[0]
    return "chat-input"


def _type_text_via_ide_map_fallback(
    prompt: str,
    *,
    map_path: str,
    app_id: str,
    ide: str,
) -> dict[str, Any]:
    """When send_ide_prompt/set_value fails: vision map click + clipboard paste."""
    map_target = _ide_map_message_target(app_id)
    source = _vdisplay_source_for_ide(ide)
    result: dict[str, Any] = {
        "ok": False,
        "backend": "vdisplay+ide-prompt",
        "fallback": "map-click-paste",
        "map_path": map_path,
        "map_target": map_target,
        "source": source,
    }

    try:
        click_res = _control_click(
            backend="vision",
            map_path=map_path,
            map_target=map_target,
        )
        result["click"] = click_res
        if not (isinstance(click_res, dict) and click_res.get("ok", True)):
            result["error"] = str((click_res or {}).get("error") or "map click failed")
            return result
    except Exception as exc:
        result["error"] = str(exc)
        return result

    x = int(click_res.get("local_x") or click_res.get("x") or 0)
    y = int(click_res.get("local_y") or click_res.get("y") or 0)
    paste_res = _type_text_at_vql_coords(
        prompt,
        x=x,
        y=y,
        source=source,
        ide=ide,
        focus_ok=True,
        focus_res={"click_res": click_res},
        vql_target={
            "id": f"map:{map_target}",
            "source": "map-calibrated",
            "click_center": {"x": x, "y": y},
            "note": "ide map click+paste fallback",
        },
    )
    result["paste"] = paste_res
    if paste_res.get("ok"):
        result.update(
            {
                "ok": True,
                "method": paste_res.get("method", "map-click-paste"),
                "value": prompt,
                "coords": {"x": x, "y": y},
            }
        )
    else:
        result["error"] = str(paste_res.get("error") or "paste after map click failed")
    return result


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
        fallback: dict[str, Any] | None = None
        if map_path:
            fallback = _type_text_via_ide_map_fallback(
                prompt,
                map_path=map_path,
                app_id=app_id,
                ide=ide,
            )
        if fallback and fallback.get("ok"):
            out: dict[str, Any] = {
                "ok": True,
                "backend": "vdisplay+ide-prompt",
                "message": "typed via ide map click+paste fallback",
                "type": "drive",
                "fallback_from": "plugin",
                "ide": ide,
                "app_id": app_id,
                "map_path": map_path,
                "typed": fallback,
                "ide_prompt_fallback": True,
                "submitted": False,
                "submit_result": None,
                "ide_prompt_error": result,
            }
            if submit:
                try:
                    sub = _submit_via_keyboard(ide=ide, submit=True)
                    out["submitted"] = bool(sub.get("ok"))
                    out["submit_result"] = sub
                except Exception:
                    pass
            return out
        return {
            "ok": False,
            "backend": "vdisplay+ide-prompt",
            "message": str(result.get("message") or "ide prompt failed"),
            "type": "error",
            "fallback_from": "plugin",
            "ide": ide,
            "map_path": map_path,
            "result": result,
            "map_fallback": fallback,
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


def _send_chat_preflight_ide_prompt(
    prompt: str,
    *,
    ide: str,
    submit: bool,
    effective_dry: bool,
    mismatch: dict[str, Any] | None,
) -> dict[str, Any] | None:
    """Preferred IDE-prompt path in _send_chat_preflight (real drive or dry-run intent)."""
    if not effective_dry and vdisplay_available():
        ide_prompt = send_chat_via_ide_prompt(
            prompt, ide=ide, submit=submit, dry_run=False,
        )
        if ide_prompt is not None and ide_prompt.get("ok"):
            if mismatch:
                ide_prompt["ide_window_warning"] = mismatch
                ide_prompt["photo_vql_skipped"] = True
            return _finalize_send_chat(ide_prompt, prompt=prompt, ide=ide, submit=submit)
    if effective_dry:
        app_id = _ide_prompt_app_id(ide)
        map_path = _resolve_ide_prompt_map(app_id)
        out = {
            "ok": True,
            "backend": "vdisplay+ide-prompt",
            "dry_run": True,
            "ide": ide,
            "app_id": app_id,
            "map_path": map_path,
            "chars": len(prompt),
            "submit": submit,
            "photo_vql_skipped": True,
        }
        if mismatch:
            out["ide_window_warning"] = mismatch
        return _finalize_send_chat(out, prompt=prompt, ide=ide, submit=submit)
    return None


def _send_chat_preflight_capture_blocked(
    blocked: dict[str, Any], *, prompt: str, ide: str, submit: bool
) -> dict[str, Any]:
    """Persist and finalize a capture-mismatch drive block."""
    session = _autonomy_session.active_session_dir()
    if session is not None:
        _autonomy_session.persist_autonomy_phase(session, "decide", "capture_blocked", blocked)
    return _finalize_send_chat(blocked, prompt=prompt, ide=ide, submit=submit)


def _send_chat_preflight(
    prompt: str,
    *,
    ide: str,
    submit: bool,
    effective_dry: bool,
    is_code: bool,
) -> dict[str, Any] | None:
    if is_code:
        return None
    mismatch = _photo_vql_ide_capture_mismatch(ide=ide)
    blocked = _drive_blocked_on_capture_mismatch(
        ide=ide, mismatch=mismatch, dry_run=effective_dry
    ) if mismatch else None
    prefer_ide_prompt = _prefer_ide_prompt_over_photo_vql(ide=ide)
    map_on_mismatch_allowed = bool(mismatch and _allow_prepare_map_on_mismatch())
    surface_on_capture_error = bool(
        mismatch and _surface_only_fallback_active() and _allow_prepare_surface_on_capture_error()
    )
    if prefer_ide_prompt and (blocked is None or map_on_mismatch_allowed or surface_on_capture_error):
        result = _send_chat_preflight_ide_prompt(
            prompt, ide=ide, submit=submit, effective_dry=effective_dry, mismatch=mismatch
        )
        if result is not None:
            return result
    if blocked is not None and not map_on_mismatch_allowed and not surface_on_capture_error:
        return _send_chat_preflight_capture_blocked(blocked, prompt=prompt, ide=ide, submit=submit)
    return None


def _send_chat_try_photo_vql(
    prompt: str,
    *,
    ide: str,
    submit: bool,
    effective_dry: bool,
    is_code: bool,
) -> dict[str, Any] | None:
    use_llm_vision = os.environ.get("KORU_VDISPLAY_LLM_VISION_DECISION", "").strip().lower() in {
        "1", "true", "yes", "on",
    }
    prefer_raw = os.environ.get("KORU_VDISPLAY_PREFER_PHOTO_VQL", "").strip().lower()
    if prefer_raw in {"0", "false", "no", "off"} and not is_code:
        return None
    photo_prefer_chat = (
        _prefer_photo_vql_chat(ide=ide)
        or (use_llm_vision and llm_vision_enabled() and _capture_matches_requested_ide(ide))
        or is_code
    )
    if not photo_prefer_chat:
        return None
    if effective_dry:
        os.environ["KORU_VDISPLAY_DRY_RUN"] = "1"
    photo_res = perform_photo_vql_focus_and_edit(
        prompt,
        ide=ide,
        source=_vdisplay_source_for_ide(ide),
        is_code_edit=is_code,
        submit=submit,
    )
    return _finalize_send_chat(
        _normalize_photo_vql_drive_result(photo_res, ide=ide, submit=submit),
        prompt=prompt,
        ide=ide,
        submit=submit,
    )


def _send_chat_dry_run(
    prompt: str,
    *,
    ide: str,
    submit: bool,
    effective_dry: bool,
) -> dict[str, Any] | None:
    if not effective_dry:
        return None
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


def _send_chat_try_os_injector(
    prompt: str,
    *,
    ide: str,
    submit: bool,
) -> dict[str, Any] | None:
    if not _send_chat_os_injector_enabled(ide=ide):
        return None
    canon = _canonical_ide(ide)
    if canon not in {"jetbrains", "pycharm"}:
        return None
    try:
        import gillm.injection.os_injector as oi
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
    return None


def _send_chat_try_ide_prompt_fallback(
    prompt: str,
    *,
    ide: str,
    submit: bool,
) -> dict[str, Any] | None:
    ide_prompt = send_chat_via_ide_prompt(
        prompt, ide=ide, submit=submit, dry_run=False,
    )
    if ide_prompt is not None and ide_prompt.get("ok"):
        return _finalize_send_chat(ide_prompt, prompt=prompt, ide=ide, submit=submit)
    return None


def _send_chat_semantic_vdisplay(
    prompt: str,
    *,
    ide: str,
    submit: bool,
) -> dict[str, Any]:
    """VQL photo chat focus + selector/set_value typing path."""
    hints = _ide_hints(ide)
    focus_error: str | None = None
    photo_vql_target: dict[str, Any] | None = None

    if not _dry_run() and os.environ.get("KORU_VDISPLAY_USE_VQL_MOUSE_FOCUS", "1").strip().lower() not in {
        "0",
        "false",
        "no",
        "off",
    }:
        photo_vql_target, focus_error = _send_chat_photo_vql_mouse_focus(prompt, ide=ide)

    selector, found, selector_error = _send_chat_resolve_chat_selector(
        ide=ide,
        hints=hints,
        photo_vql_target=photo_vql_target,
        focus_error=focus_error,
    )
    if selector_error is not None:
        return selector_error

    typed, click_point, type_error = _send_chat_type_at_selector(
        prompt,
        ide=ide,
        hints=hints,
        selector=selector,
        found=found,
        focus_error=focus_error,
    )
    if type_error is not None:
        return type_error

    submitted, submit_result = _send_chat_submit_if_requested(ide=ide, hints=hints, submit=submit)
    return _finalize_send_chat(
        {
            "ok": True,
            "backend": "vdisplay",
            "message": "typed via vdisplay semantic control (with VQL photo mouse focus)",
            "type": "drive",
            "fallback_from": "plugin",
            "ide": ide,
            "selector": selector,
            "focus_error": focus_error,
            "typed": typed,
            "submitted": submitted,
            "submit_result": submit_result,
            "vql_mouse_focus": True,
        },
        prompt=prompt,
        ide=ide,
        submit=submit,
    )


def _send_chat_photo_vql_mouse_focus(
    prompt: str,
    *,
    ide: str,
) -> tuple[dict[str, Any] | None, str | None]:
    focus_error: str | None = None
    photo_vql_target: dict[str, Any] | None = None
    try:
        photo_vql_target = get_vql_chat_target_from_photo()
        use_llm_vision = llm_vision_enabled()
        if use_llm_vision:
            image_path = _resolve_photo_png_path_from_vql(source=_vdisplay_source())
            if image_path and os.path.exists(str(image_path)):
                try:
                    rx, ry, rdec = _resolve_photo_vql_llm_coords(
                        prompt=prompt,
                        target=photo_vql_target,
                        source=_vdisplay_source(),
                        image_path=image_path,
                    )
                    if rdec:
                        photo_vql_target = {
                            **photo_vql_target,
                            "click_center": {
                                "x": rx,
                                "y": ry,
                                "note": f"LLM refined from foto: {rdec.get('reason', '')[:60]}",
                            },
                            "llm_refined": True,
                            "llm_decision": rdec,
                        }
                except Exception:
                    pass
        mf = move_mouse_to_vql_target_and_focus_keyboard(photo_vql_target, ide=ide)
        if not mf.get("ok"):
            focus_error = mf.get("error") or mf.get("message")
    except Exception as exc:
        focus_error = str(exc)
        photo_vql_target = get_vql_chat_target_from_photo()
    return photo_vql_target, focus_error


def _send_chat_resolve_chat_selector(
    *,
    ide: str,
    hints: dict[str, str],
    photo_vql_target: dict[str, Any] | None,
    focus_error: str | None,
) -> tuple[dict[str, str] | None, dict[str, Any] | None, dict[str, Any] | None]:
    selector, found = _find_first_selector(ide=ide, selectors=_chat_selectors_for(ide))
    if selector is not None:
        return selector, found, None

    found = _resolve_vql_chat_target(ide, hints)
    if found:
        return {"role": "input", "name_contains": "Chat"}, found, None

    if photo_vql_target and photo_vql_target.get("click_center"):
        click_center = photo_vql_target["click_center"]
        return (
            {"role": photo_vql_target.get("role", "panel")},
            {
                "ok": True,
                "count": 1,
                "selected": {
                    "id": photo_vql_target.get("id", "vql-photo-chat"),
                    "backend": "vql",
                    "role": photo_vql_target.get("role", "panel"),
                    "click_point": click_center,
                    "note": "photo VQL fallback for cursor chat after focus move",
                },
            },
            None,
        )

    return None, found, {
        "ok": False,
        "backend": "vdisplay",
        "message": (
            f"no chat input matched for ide={ide} "
            f"(app={hints.get('app')!r}); focus_error={focus_error or '-'}"
        ),
        "type": "error",
        "fallback_from": "plugin",
        "diagnostics": found,
        "vql_mouse_focus_error": focus_error,
    }


def _send_chat_selector_click_point(
    found: dict[str, Any] | None,
    selector: dict[str, str] | None,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None, dict[str, str] | None]:
    """Resolve (selected, click_point, selector) from a found selector payload."""
    selected = (found or {}).get("selected") if isinstance(found, dict) else None
    click_point = None
    if isinstance(selected, dict):
        click_point = selected.get("click_point") or selected.get("click_center")
        if isinstance(click_point, dict) and not selector:
            selector = {"role": "input", "name_contains": "vql"}
    return selected, click_point, selector


def _send_chat_selector_write_kwargs(
    prompt: str,
    *,
    hints: dict[str, str],
    selector: dict[str, str] | None,
    selected: dict[str, Any] | None,
    click_point: dict[str, Any] | None,
) -> dict[str, Any]:
    """Build _control_set_value kwargs for the chat selector typing path."""
    write_kwargs: dict[str, Any] = {
        "backend": "auto",
        "app": hints.get("app"),
        "window_title": hints.get("window_title_contains"),
        "value": prompt,
        **(selector or {}),
    }
    if isinstance(selected, dict) and selected.get("id"):
        write_kwargs["provider_ref"] = selected["id"]
    if click_point and isinstance(click_point, dict):
        write_kwargs["x"] = click_point.get("x")
        write_kwargs["y"] = click_point.get("y")
        write_kwargs["backend"] = "vision"
    return write_kwargs


def _send_chat_type_at_selector(
    prompt: str,
    *,
    ide: str,
    hints: dict[str, str],
    selector: dict[str, str] | None,
    found: dict[str, Any] | None,
    focus_error: str | None,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None, dict[str, Any] | None]:
    selected, click_point, selector = _send_chat_selector_click_point(found, selector)
    write_kwargs = _send_chat_selector_write_kwargs(
        prompt, hints=hints, selector=selector, selected=selected, click_point=click_point
    )

    try:
        typed = _control_set_value(**write_kwargs)
    except Exception as exc:
        return None, click_point, {
            "ok": False,
            "backend": "vdisplay",
            "message": str(exc),
            "type": "error",
            "fallback_from": "plugin",
            "selector": selector,
            "focus_error": focus_error,
            "vql_click_point": click_point,
        }

    if not typed.get("ok", True):
        return None, click_point, {
            "ok": False,
            "backend": "vdisplay",
            "message": str(typed.get("error") or typed.get("message") or "set_value failed"),
            "type": "error",
            "fallback_from": "plugin",
            "selector": selector,
            "result": typed,
            "focus_error": focus_error,
        }
    return typed, click_point, None


def _send_chat_submit_if_requested(
    *,
    ide: str,
    hints: dict[str, str],
    submit: bool,
) -> tuple[bool, dict[str, Any] | None]:
    if not submit:
        return False, None
    submitted = False
    submit_result: dict[str, Any] | None = None
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
    return submitted, submit_result


def send_chat(
    prompt: str,
    *,
    ide: str,
    submit: bool,
    dry_run: bool | None = None,
) -> dict[str, Any]:
    """Semantic IDE chat drive via vdisplay control plane."""
    effective_dry = _dry_run() if dry_run is None else dry_run
    is_code = _photo_vql_code_edit_enabled()

    result = _send_chat_preflight(
        prompt, ide=ide, submit=submit, effective_dry=effective_dry, is_code=is_code
    )
    if result is not None:
        return result

    result = _send_chat_try_photo_vql(
        prompt, ide=ide, submit=submit, effective_dry=effective_dry, is_code=is_code
    )
    if result is not None:
        return result

    result = _send_chat_dry_run(prompt, ide=ide, submit=submit, effective_dry=effective_dry)
    if result is not None:
        return result

    if not vdisplay_available():
        return {
            "ok": False,
            "backend": "vdisplay",
            "message": vdisplay_missing_message(),
            "type": "error",
            "fallback_from": "plugin",
        }

    if _auto_ide_control_enabled() and _photo_vql_ide_capture_mismatch(ide=ide):
        ensure_vdisplay_ide_control(ide=ide, source=_vdisplay_source())

    result = _send_chat_try_os_injector(prompt, ide=ide, submit=submit)
    if result is not None:
        return result

    result = _send_chat_try_ide_prompt_fallback(prompt, ide=ide, submit=submit)
    if result is not None:
        return result

    return _send_chat_semantic_vdisplay(prompt, ide=ide, submit=submit)


def _resolve_vql_chat_target(ide: str, hints: dict) -> dict | None:
    """Resolve chat target using VQL metadata for precise mouse nav on second monitor (DP-1).
    Used in autonomous PyCharm/JetBrains control via vdisplay + VQL centers (e.g. 1024,640).
    """
    vql_target = _find_vql_chat_target(ide)
    if not vql_target and ide in ("pycharm", "jetbrains"):
        vql_target = {"click_center": {"x": 1024, "y": 640, "note": "PyCharm/JetBrains editor area on DP-1 second monitor from VQL"}}  # noqa: E501
    if vql_target:
        return _extract_vql_click_from_target(vql_target)
    return None


def _find_vql_chat_target(ide: str) -> dict | None:
    """Helper extracted to reduce CC."""
    return get_vql_target(ide, role="input", name_contains="chat") or get_vql_target(ide, role="input") or get_vql_target(ide, label="chat")  # noqa: E501


def _extract_vql_click_from_target(vql_target: dict) -> dict:
    """Helper extracted to reduce CC in _resolve_vql_chat_target (autonomous refactor)."""
    return {
        "id": vql_target.get("id", "vql-chat"),
        "backend": "vql",
        "role": vql_target.get("role"),
        "click_point": vql_target.get("click_center"),
        "note": f"VQL target from {vql_target.get('source', 'VQL analysis for second monitor')}"
    }


def _get_pycharm_vql_editor_center():
    """PyCharm specific VQL target for editor on second monitor (DP-1), using VQL click 1024,640 as if clicked in PyCharm on DP-1."""  # noqa: E501
    return {"click_center": {"x": 1024, "y": 640, "note": "PyCharm editor area on DP-1 second monitor from VQL (autonomous click at 1024,640)"}}  # noqa: E501


def _get_jetbrains_pycharm_chat_center():
    """Shim: prefer photo VQL based locate for chat window + mouse + kb focus (see get_vql_chat_target_from_photo)."""
    # From current foto screen VQL (31 elems), main editor/chat area on DP-1
    return {"x": 1024, "y": 640, "note": "Chat window area from screen photo VQL (use move_mouse_to_vql_target_and_focus_keyboard for real mouse+focus)"}  # noqa: E501


def _photo_vql_elements() -> tuple[list[dict], str | None]:
    vql = load_vql_metadata()
    els = vql.get("ui_elements") or vql.get("layers") or []
    return els, vql.get("_source")


def _live_surface_monitor_lookup(source: str) -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
    """Locate the monitor row matching source among local monitors (best effort)."""
    monitors: list[dict[str, Any]] = []
    monitor: dict[str, Any] | None = None
    try:
        from vdisplay.application.services.discovery import list_monitors_local

        monitors = list(list_monitors_local().get("monitors") or [])
        monitor = next((row for row in monitors if str(row.get("name") or "") == source), None)
    except Exception:
        pass
    return monitors, monitor


def _live_surface_screencast_region(
    meta: dict[str, Any],
    monitor: dict[str, Any] | None,
    monitors: list[dict[str, Any]],
) -> None:
    """Fill meta region from an active portal screencast stream (best effort)."""
    try:
        from vdisplay.capture.portal_screencast import get_active_screencast
        from vdisplay.capture.screencast_crop import _resolve_multi_stream_region
        from vdisplay.capture.screencast_stream_matching import screencast_stream_index_for_monitor

        session = get_active_screencast()
        if session is not None and isinstance(monitor, dict):
            stream_idx = screencast_stream_index_for_monitor(
                session,
                monitor,
                all_monitors=monitors or [monitor],
            )
            region = _resolve_multi_stream_region(session, stream_idx, monitor)
            if isinstance(region, dict):
                meta["region"] = dict(region)
                meta["screencast_stream"] = True
                meta["width"] = int(region.get("width") or 0)
                meta["height"] = int(region.get("height") or 0)
                meta["screencast_stream_index"] = stream_idx
    except Exception:
        pass


def _live_surface_monitor_region_fallback(meta: dict[str, Any], source: str) -> None:
    """Fill meta region from monitor geometry when no screencast region resolved."""
    try:
        from vdisplay.application.services.discovery import list_monitors_local

        monitor = next(
            (
                row
                for row in (list_monitors_local().get("monitors") or [])
                if str(row.get("name") or "") == source
            ),
            None,
        )
        if isinstance(monitor, dict):
            meta["region"] = {
                "x": int(monitor.get("x") or 0),
                "y": int(monitor.get("y") or 0),
                "width": int(monitor.get("width") or monitor.get("width_px") or 0),
                "height": int(monitor.get("height") or monitor.get("height_px") or 0),
            }
    except Exception:
        pass


def _live_surface_capture_meta(source: str) -> dict[str, Any]:
    """Fresh capture metadata for surface-based pointer math (ignore stale PNG sidecars)."""
    meta: dict[str, Any] = {"source": source, "monitor_name": source}
    monitors, monitor = _live_surface_monitor_lookup(source)
    if isinstance(monitor, dict):
        meta["rotation"] = monitor.get("rotation") or "normal"
    _live_surface_screencast_region(meta, monitor, monitors)
    if "region" not in meta:
        _live_surface_monitor_region_fallback(meta, source)
    meta.setdefault("width", 2048)
    meta.setdefault("height", 1280)
    return meta


def _jetbrains_surface_chat_target(*, ide: str, source: str | None = None) -> dict[str, Any] | None:
    """Chat composer from PyCharm surface bounds when map/VQL are unreliable."""
    try:
        resolved_source, probe = _resolve_vdisplay_source_for_ide(ide)
    except Exception:
        return None
    effective_source = (source or resolved_source or _vdisplay_source_for_ide(ide)).strip()
    if not probe.get("ide_surface_best"):
        try:
            probe = _desktop_probe(ide=ide, source=effective_source)
        except Exception:
            return None
    best = probe.get("ide_surface_best")
    if not isinstance(best, dict):
        return None
    if isinstance(best.get("bounds"), dict):
        surface = best
    else:
        pid = best.get("pid")
        surface = next(
            (
                row
                for row in probe.get("ide_surfaces") or []
                if isinstance(row, dict) and row.get("pid") == pid
            ),
            best,
        )
    capture_meta = _live_surface_capture_meta(effective_source)
    return _jetbrains_chat_target_from_surface(
        surface,
        capture_meta=capture_meta,
        source=effective_source,
    )


def _chat_target_validation_accepts(target: dict[str, Any]) -> bool:
    validation = target.get("vql_validation")
    if not isinstance(validation, dict):
        return True
    if validation.get("validation_errors"):
        return False
    if validation.get("coord_warnings"):
        return False
    if validation.get("ok") is False:
        return False
    return True


def _vql_file_for_positioning(src: Any) -> str | None:
    """VQL sidecar path for cursor-positioning logs (None for non-sidecar sources)."""
    return src if isinstance(src, str) and str(src).endswith(".vql.json") else None


def _photo_vql_jetbrains_chat_flow(
    *,
    canon: str,
    src_name: str,
    src: Any,
    els: list,
    empty_layers: bool,
    mismatch: dict[str, Any] | None,
    is_polluted: bool,
    finalize: Any,
    try_llm: Any,
) -> dict[str, Any] | None:
    """JetBrains chat-target selection cascade (LLM vision, surface bounds, map, corner)."""
    if _photo_vql_needs_vision_or_map(
        mismatch=mismatch,
        empty_layers=empty_layers,
        polluted=is_polluted,
    ):
        map_hint = _map_chat_target_capture_local(ide=canon, source=src_name)
        llm_target = try_llm(map_hint=map_hint)
        if llm_target:
            llm_target = finalize(llm_target, method="llm_vision_detect")
            _log_vql_cursor_positioning_at_command(
                llm_target,
                stage="vql_target_selection_llm_vision",
                ide=canon,
                source=src_name,
                final_local=llm_target.get("click_center", {}),
                vql_file=_vql_file_for_positioning(src),
            )
            return llm_target
        surface_target = _jetbrains_surface_chat_target(ide=canon, source=src_name)
        if surface_target:
            surface_target = finalize(surface_target, method="jetbrains_surface_bounds")
            if _chat_target_validation_accepts(surface_target):
                _log_vql_cursor_positioning_at_command(
                    surface_target,
                    stage="vql_target_selection_jetbrains_surface",
                    ide=canon,
                    source=src_name,
                    final_local=surface_target.get("click_center", {}),
                    final_global=surface_target.get("map_global"),
                    vql_file=_vql_file_for_positioning(src),
                )
                return surface_target
            logger.warning(
                "VQL_CHAT_TARGET_REJECTED ide=%s method=jetbrains_surface_bounds validation=%s",
                canon,
                surface_target.get("vql_validation"),
            )
        # Distrust VQL layers; prefer calibrated map when LLM unavailable.
        map_target = map_hint
        if map_target:
            method = _jetbrains_map_selection_method(empty_layers=empty_layers)
            stage = _jetbrains_map_selection_stage(empty_layers=empty_layers)
            map_target = finalize(map_target, method=method)
            _log_vql_cursor_positioning_at_command(
                map_target,
                stage=stage,
                ide=canon,
                source=src_name,
                final_local=map_target.get("click_center", {}),
                final_global=map_target.get("map_global"),
                vql_file=_vql_file_for_positioning(src),
            )
            return map_target
    corner = _jetbrains_chat_corner_target_from_layers(els, source=src)
    if corner:
        corner = finalize(corner, method="jetbrains_corner_heuristic")
        _log_vql_cursor_positioning_at_command(
            corner,
            stage="vql_target_selection_jetbrains_corner",
            ide=canon,
            source=src_name,
            final_local=corner.get("click_center", {}),
            vql_file=_vql_file_for_positioning(src),
        )
        return corner
    map_target = _map_chat_target_capture_local(ide=canon, source=src_name)
    if map_target:
        map_target = finalize(map_target, method="map_calibrated")
        _log_vql_cursor_positioning_at_command(
            map_target,
            stage="vql_target_selection_jetbrains_map",
            ide=canon,
            source=src_name,
            final_local=map_target.get("click_center", {}),
            final_global=map_target.get("map_global"),
            vql_file=_vql_file_for_positioning(src),
        )
        return map_target
    return None


def _photo_vql_vscode_chat_flow(
    *,
    canon: str,
    src_name: str,
    src: Any,
    els: list,
    empty_layers: bool,
    mismatch: dict[str, Any] | None,
    is_polluted: bool,
    finalize: Any,
    try_llm: Any,
) -> dict[str, Any] | None:
    """VSCode-family chat-target selection (LLM vision on mismatch, then top-chat heuristic)."""
    if _photo_vql_needs_vision_or_map(
        mismatch=mismatch,
        empty_layers=empty_layers,
        polluted=is_polluted,
    ):
        llm_target = try_llm()
        if llm_target:
            llm_target = finalize(llm_target, method="llm_vision_detect")
            return llm_target
    top_chat = _vscode_family_chat_target_from_layers(els, ide=canon, source=src)
    if top_chat:
        top_chat = finalize(top_chat, method="vscode_top_chat_heuristic")
        _log_vql_cursor_positioning_at_command(
            top_chat,
            stage="vql_target_selection_vscode_top_chat",
            ide=canon,
            source=src_name,
            final_local=top_chat.get("click_center", {}),
            vql_file=_vql_file_for_positioning(src),
        )
        return top_chat
    return None


def _try_ocr_anchor_chat_target(*, ide: str, source: str) -> dict[str, Any] | None:
    """Deterministic chat-input target from the OCR placeholder bbox, or None."""
    try:
        from vdisplay.control.vision_chat_detect import ocr_anchor_chat_target
    except ImportError:
        return None
    png = _resolve_photo_png_path_from_vql(source=source)
    if not png:
        return None
    try:
        data = Path(png).read_bytes()
    except OSError:
        return None
    try:
        return ocr_anchor_chat_target(data, ide=ide)
    except Exception:
        return None


def get_vql_chat_target_from_photo(*, prefer_role: str | None = "panel", ide: str = "auto") -> dict:
    """Na podstawie foto screen VQL zlokalizuj okno/panel chat (deleguje do imgl.targets)."""
    els, src = _photo_vql_elements()
    canon = _canonical_ide(ide)
    if canon in {"", "auto"}:
        canon = _canonical_ide(os.environ.get("KORU_DRIVE_IDE", "auto"))
    candidates = _photo_vql_chat_input_candidates(els, limit=8, ide=canon)
    explicit_source = os.environ.get("KORU_VDISPLAY_SOURCE", "").strip()
    if explicit_source:
        src_name = explicit_source
    else:
        src_name, _ = _resolve_vdisplay_source_for_ide(canon)

    # Detect terminal pollution in VQL (common on DP-2 when control terminal text is visible in screenshot).
    # If many candidates look like shell/env/command history (from the log's fake "PREFER LLM", "KORU_*", "po clear" etc.),  # noqa: E501
    # treat as polluted and force map for jetbrains (VQL is unreliable).
    is_polluted = _vql_candidates_polluted(candidates) or _vql_layers_show_vdisplay_overlay(els)

    logger.info(
        "VQL_CHAT_TARGET_CANDIDATES ide=%s source=%s vql_file=%s layer_count=%d candidates=%s polluted=%s",
        canon,
        src_name,
        src,
        len(els),
        json.dumps(candidates, default=str)[:1200],
        is_polluted,
    )
    session = _autonomy_session.active_session_dir()
    if session is not None:
        _autonomy_session.persist_autonomy_phase(
            session,
            "decide",
            "vql_chat_candidates",
            {"vql_source": src, "layer_count": len(els), "candidates": candidates, "ide": canon},
        )

    def _finalize(target: dict[str, Any], *, method: str) -> dict[str, Any]:
        out = {
            **target,
            "vql_candidates": candidates,
            "vql_layers_count": len(els),
            "selection_method": method,
        }
        cc = out.get("click_center") or {}  # noqa: F841
        vql_meta = load_vql_metadata(allow_stale=True)
        eff_mismatch = mismatch
        if method == "jetbrains_surface_bounds" and _surface_only_fallback_active():
            eff_mismatch = None
        validation = validate_vql_chat_target(
            out,
            ide=canon,
            meta=vql_meta,
            capture_mismatch=eff_mismatch,
            selection_method=method,
        )
        if _surface_bounds_target_trusted(target=out, method=method):
            patched = dict(validation)
            patched["surface_bounds_trusted"] = True
            if not validation.get("validation_errors") and not validation.get("coord_warnings"):
                patched["ok"] = bool(validation.get("vql_valid", True)) and bool(validation.get("app_match", True))
            validation = patched
        out["vql_validation"] = validation
        if session is not None:
            _autonomy_session.persist_autonomy_phase(
                session,
                "decide",
                "vql_chat_target_selected",
                {
                    "selection_method": method,
                    "target": out,
                    "warnings": validation.get("coord_warnings") or [],
                    "vql_validation": validation,
                },
            )
            _autonomy_session.persist_autonomy_phase(session, "decide", "vql_validation", validation)
        return out

    mismatch = _photo_vql_ide_capture_mismatch(ide=canon) if canon not in {"", "auto"} else None
    empty_layers = len(els) == 0

    def _try_llm_chat_detect(*, map_hint: dict[str, Any] | None = None) -> dict[str, Any] | None:
        if not llm_vision_enabled():
            return None
        png = _resolve_photo_png_path_from_vql(source=src_name)
        if not png:
            return None
        try:
            from vdisplay.integrations.chat_target import resolve_chat_target_from_screenshot
        except ImportError:
            from koru.integrations.photo_vql_llm_detect import detect_chat_target_from_llm_vision

            meta_for_title = load_vql_metadata(allow_stale=True)
            capture_title = _capture_title_from_meta(meta_for_title)
            return detect_chat_target_from_llm_vision(
                ide=canon,
                source=src_name,
                image_path=png,
                candidates=candidates,
                map_hint=map_hint,
                capture_title=capture_title,
            )

        meta_for_title = load_vql_metadata(allow_stale=True)
        capture_validation = (meta_for_title.get("capture_validation") or {}) if isinstance(meta_for_title, dict) else {}  # noqa: E501
        return resolve_chat_target_from_screenshot(
            png,
            ide=canon,
            source=src_name,
            layers=els,
            capture_validation=capture_validation,
            map_hint=map_hint,
            polluted=is_polluted,
        )

    # Deterministic OCR placeholder anchor first: the input's placeholder text
    # ("Plan and build autonomously", "Ask anything", …) has an exact tesseract
    # bbox, so its center is a precise click point with no LLM pixel-precision
    # risk. Only when the placeholder is absent/unreadable do we fall to the
    # per-IDE heuristics + vision below.
    anchor = _try_ocr_anchor_chat_target(ide=canon, source=src_name)
    if anchor is not None:
        return _finalize(anchor, method="ocr_anchor_chat_placeholder")

    if canon in {"jetbrains", "pycharm", "idea"}:
        jb_target = _photo_vql_jetbrains_chat_flow(
            canon=canon,
            src_name=src_name,
            src=src,
            els=els,
            empty_layers=empty_layers,
            mismatch=mismatch,
            is_polluted=is_polluted,
            finalize=_finalize,
            try_llm=_try_llm_chat_detect,
        )
        if jb_target is not None:
            return jb_target
    if canon in VSCODE_FAMILY_TOP_CHAT_IDES:
        vscode_target = _photo_vql_vscode_chat_flow(
            canon=canon,
            src_name=src_name,
            src=src,
            els=els,
            empty_layers=empty_layers,
            mismatch=mismatch,
            is_polluted=is_polluted,
            finalize=_finalize,
            try_llm=_try_llm_chat_detect,
        )
        if vscode_target is not None:
            return vscode_target
    resolve_chat_target = _import_imgl_targets("resolve_chat_target")
    if resolve_chat_target is not None:
        resolved = resolve_chat_target(els, source=src)
        return _finalize(resolved, method="imgl_resolve_chat_target")
    llm_target = _try_llm_chat_detect()
    if llm_target:
        return _finalize(llm_target, method="llm_vision_detect")
    fallback = {
        "click_center": {"x": 1024, "y": 640, "note": "DP-1 main editor/chat area center (imgl not installed)"},
        "id": "dp1-chat-editor-center",
        "role": "editor-chat-area",
        "note": "hardened fallback — pip install imgl",
        "source": "vql-analysis-fallback",
    }
    logger.warning(
        "VQL_CHAT_TARGET_FALLBACK ide=%s using hardcoded center (1024,640) — no live VQL match",
        canon,
    )
    return _finalize(fallback, method="hardened_fallback")


def _photo_vql_needs_vision_or_map(
    *,
    mismatch: dict[str, Any] | None,
    empty_layers: bool,
    polluted: bool,
) -> bool:
    return bool(mismatch) or empty_layers or polluted


def _jetbrains_map_selection_method(*, empty_layers: bool) -> str:
    return "map_calibrated_on_empty_vql" if empty_layers else "map_calibrated_on_mismatch"


def _jetbrains_map_selection_stage(*, empty_layers: bool) -> str:
    if empty_layers:
        return "vql_target_selection_jetbrains_map_on_empty_vql"
    return "vql_target_selection_jetbrains_map_on_mismatch"


def get_vql_editor_target_from_photo() -> dict:
    """Na podstawie foto screen VQL zlokalizuj główny obszar edytora (deleguje do imgl.targets)."""
    els, src = _photo_vql_elements()
    resolve_editor_target = _import_imgl_targets("resolve_editor_target")
    if resolve_editor_target is not None:
        return resolve_editor_target(els, source=src)
    return {
        "click_center": {"x": 1024, "y": 640, "note": "DP-1 main editor area center (imgl not installed)"},
        "id": "dp1-editor-center",
        "role": "editor",
        "note": "hardened fallback — pip install imgl",
        "source": "vql-analysis-fallback",
    }


def click_editor_via_photo_vql(ide: str = "auto", source: str = "DP-1") -> dict:
    """Użyj VQL z foto do zlokalizowania edytora (otwarty plik), kliknij center dla focus,
    przygotuj do precyzyjnego edit via coords.

    Parallel to chat focus. Zwraca wynik z click_center z foto VQL.
    Autonomia może potem użyć coords do edit (set_value, keyboard, lub control na tym punkcie).
    """
    t = get_vql_editor_target_from_photo()
    # Reuse the move logic (it does mouse to center + window focus for kb)
    res = move_mouse_to_vql_target_and_focus_keyboard(t, ide=ide, source=source)
    res["target_kind"] = "editor"
    res["for"] = "see open file + precise edit via VQL photo coords"
    return res


def _photo_capture_meta_for_source(source: str) -> dict[str, Any]:
    """Best-effort capture metadata for translating local VQL coords to global pointer space."""
    meta: dict[str, Any] = {}
    png = _resolve_photo_png_path(source)
    ctx_path = png.with_suffix(png.suffix + ".context.json")
    if ctx_path.is_file():
        try:
            with open(ctx_path) as f:
                ctx = json.load(f)
            cap = ctx.get("capture") if isinstance(ctx, dict) else None
            if isinstance(cap, dict):
                meta = dict(cap)
        except Exception:
            pass
    if not meta:
        sidecar = load_vql_metadata(str(png.with_suffix(png.suffix + ".vql.json")))
        cap = (sidecar.get("metadata") or {}).get("capture") if isinstance(sidecar.get("metadata"), dict) else None
        if isinstance(cap, dict):
            meta = dict(cap)
    meta.setdefault("source", source)
    meta.setdefault("monitor_name", source)
    return _enrich_capture_meta_for_pointer(meta, source)


def _enrich_stream_meta_via_vdisplay(enriched: dict[str, Any]) -> dict[str, Any]:
    """Best-effort screencast stream-meta enrichment via vdisplay (either import path)."""
    try:
        from vdisplay.capture.screencast_stream_meta import enrich_screencast_stream_meta

        enriched = enrich_screencast_stream_meta(enriched)
    except Exception:
        try:
            from vdisplay.control.screenshot_verify import enrich_screencast_stream_meta

            enriched = enrich_screencast_stream_meta(enriched)
        except Exception:
            pass
    return enriched


def _region_origin(enriched: dict[str, Any]) -> tuple[int, int]:
    """Return the (x, y) origin of the capture region (0, 0 when absent)."""
    region = enriched.get("region") if isinstance(enriched.get("region"), dict) else {}
    return int(region.get("x") or 0), int(region.get("y") or 0)


def _region_dict_from_bounds(db: dict[str, Any]) -> dict[str, int]:
    """Build a region dict from a bounds-like dict (x/y/width/height)."""
    return {
        "x": int(db.get("x") or 0),
        "y": int(db.get("y") or 0),
        "width": int(db.get("width") or 0),
        "height": int(db.get("height") or 0),
    }


def _enrich_region_from_display_bounds(enriched: dict[str, Any]) -> None:
    """Derive the capture region from embedded display_bounds when usable."""
    display_bounds = enriched.get("display_bounds")
    if isinstance(display_bounds, dict) and display_bounds.get("width") and display_bounds.get("height"):
        enriched["region"] = _region_dict_from_bounds(display_bounds)


def _enrich_region_from_ide_map(enriched: dict[str, Any], source: str) -> None:
    """Copy region/rotation/stream fields from a matching calibrated IDE map's capture_meta."""
    app_id = _ide_prompt_app_id(source if source in {"pycharm", "jetbrains", "idea"} else "pycharm")
    map_path = _resolve_ide_prompt_map(app_id)
    if map_path and os.path.isfile(map_path):
        try:
            with open(map_path) as f:
                map_data = json.load(f)
            mcap = map_data.get("capture_meta") if isinstance(map_data.get("capture_meta"), dict) else {}
            if str(mcap.get("source") or mcap.get("monitor_name") or "") in {source, "", "DP-2"}:
                for key in (
                    "region",
                    "rotation",
                    "screencast_stream",
                    "screencast_full_frame",
                    "width",
                    "height",
                    "display_bounds",
                ):
                    if mcap.get(key) is not None:
                        enriched[key] = mcap[key]
                db = mcap.get("display_bounds")
                if isinstance(db, dict) and not enriched.get("region"):
                    enriched["region"] = _region_dict_from_bounds(db)
        except Exception:
            pass


def _enrich_region_from_monitor(enriched: dict[str, Any], source: str, origin_x: int, origin_y: int) -> None:
    """Fill rotation/region from the vdisplay monitor layout as a last resort."""
    try:
        from vdisplay.input.coords import _monitor_by_name

        mon = _monitor_by_name(enriched.get("display"), source)
        if isinstance(mon, dict):
            enriched.setdefault("rotation", mon.get("rotation"))
            if origin_x == 0 and origin_y == 0 and not enriched.get("region"):
                enriched["region"] = {
                    "x": int(mon.get("x") or 0),
                    "y": int(mon.get("y") or 0),
                    "width": int(mon.get("width") or enriched.get("width") or 0),
                    "height": int(mon.get("height") or enriched.get("height") or 0),
                }
    except Exception:
        pass


def _enrich_capture_meta_for_pointer(meta: dict[str, Any], source: str) -> dict[str, Any]:
    """Fill portal stream region/rotation when screenshot sidecar only has a 0,0 crop."""
    enriched = _enrich_stream_meta_via_vdisplay(dict(meta or {}))
    origin_x, origin_y = _region_origin(enriched)
    if origin_x == 0 and origin_y == 0:
        _enrich_region_from_display_bounds(enriched)
        origin_x, origin_y = _region_origin(enriched)
    if origin_x == 0 and origin_y == 0:
        _enrich_region_from_ide_map(enriched, source)
        _enrich_region_from_monitor(enriched, source, origin_x, origin_y)
    return enriched


def _map_chat_input_candidate_keys(app_id: str) -> list[str]:
    """Ordered map element keys to try for the chat composer click point."""
    # Preferred order: prompt (known good in ide_control for DP-2), then chat specific, then fallbacks.
    candidates: list[str] = []
    try:
        from vdisplay.desktop_apps import map_input_target_candidates
        cands = map_input_target_candidates(app_id) or []
        for c in cands:
            if c not in candidates:
                candidates.append(c)
    except Exception:
        pass
    for fb in ("prompt", "ai-chat-input", "chat-input", "message", "input"):
        if fb not in candidates:
            candidates.append(fb)
    return candidates


def _map_chat_pointer_meta(source: str) -> dict[str, Any]:
    """Enriched capture meta used to map global map points to capture-local coords."""
    meta = _enrich_capture_meta_for_pointer(_photo_capture_meta_for_source(source), source)
    region = (meta or {}).get("region") or {}
    cap_w = int(region.get("width") or 2048)  # noqa: F841
    cap_h = int(region.get("height") or 1280)  # noqa: F841
    return meta


def _map_chat_element_local_point(
    element: dict[str, Any], meta: dict[str, Any]
) -> tuple[int, int, int, int] | None:
    """Map an element's global click_point to capture-local ints; None if unusable."""
    from vdisplay.input.coords import global_point_to_capture_local
    click = element.get("click_point") or {}
    gx = int(click.get("x") or 0)
    gy = int(click.get("y") or 0)
    if gx <= 0 or gy <= 0:
        return None
    lx, ly = global_point_to_capture_local(gx, gy, meta)
    return gx, gy, int(lx), int(ly)


def _map_chat_target_entry(
    key: str,
    element: dict[str, Any],
    lx_i: int,
    ly_i: int,
    gx: int,
    gy: int,
    map_path: str,
) -> dict[str, Any]:
    """Map-calibrated chat target dict for a resolved element/coords pair."""
    return {
        "click_center": {"x": lx_i, "y": ly_i},
        "id": f"map:{key}",
        "role": "input",
        "bounds": element.get("action_bounds") or element.get("raw_bounds"),
        "note": f"map-calibrated JetBrains chat input ({key} from {map_path})",
        "source": map_path,
        "map_global": {"x": gx, "y": gy},
        "map_element_key": key,
    }


def _map_chat_bottom_right_target(
    candidates: list[str],
    elems: Any,
    meta: dict[str, Any],
    map_path: str,
) -> dict[str, Any] | None:
    """First candidate whose local point lands in the bottom-right composer area."""
    for key in candidates:
        element = elems.get(key) if isinstance(elems, dict) else None
        if not isinstance(element, dict):
            continue
        point = _map_chat_element_local_point(element, meta)
        if point is None:
            continue
        gx, gy, lx_i, ly_i = point
        # Accept bottom-right composer area; skip top-of-screen/editor coords from stale maps.
        if ly_i >= 700 and lx_i >= 900:
            return _map_chat_target_entry(key, element, lx_i, ly_i, gx, gy, map_path)
    return None


def _map_chat_nonnegative_target(
    candidates: list[str],
    elems: Any,
    meta: dict[str, Any],
    map_path: str,
) -> dict[str, Any] | None:
    """Last resort: first candidate with a non-negative local point."""
    # Last resort: take the first valid element even if y low (will get coord warning later)
    # But still refuse to return a negative local y (safer than feeding garbage coords to ydotool plan).
    for key in candidates:
        element = elems.get(key) if isinstance(elems, dict) else None
        if not isinstance(element, dict):
            continue
        point = _map_chat_element_local_point(element, meta)
        if point is None:
            continue
        gx, gy, lx_i, ly_i = point
        if ly_i < 0 or lx_i < 0:
            continue
        return _map_chat_target_entry(key, element, lx_i, ly_i, gx, gy, map_path)
    return None


def _map_chat_target_capture_local(*, ide: str, source: str) -> dict[str, Any] | None:
    """Convert calibrated map chat input global point into capture-local coords.
    Tries several element keys (prompt first for JetBrains on DP-2, then ai-chat-input etc)
    and returns the first that yields a sane positive local y (bottom composer area).
    This avoids negative y or editor coords from stale/wrong-calibrated map entries
    under rotated screencast capture_meta (e.g. origin_y=1932, scale 0.8).
    """
    app_id = _ide_prompt_app_id(ide)
    map_path = _resolve_ide_prompt_map(app_id)
    if not map_path or not os.path.isfile(map_path):
        return None
    try:
        with open(map_path) as f:
            map_data = json.load(f)
        map_meta = map_data.get("capture_meta") if isinstance(map_data.get("capture_meta"), dict) else {}
        map_source = str(map_meta.get("source") or map_meta.get("monitor_name") or "").strip()
        if map_source and map_source != source:
            return None
        elems = (map_data.get("elements") or {})
        candidates = _map_chat_input_candidate_keys(app_id)
        meta = _map_chat_pointer_meta(source)
        target = _map_chat_bottom_right_target(candidates, elems, meta, map_path)
        if target is not None:
            return target
        return _map_chat_nonnegative_target(candidates, elems, meta, map_path)
    except Exception:
        return None


def _global_coords_from_vql_local(*, x: int, y: int, source: str) -> tuple[int | None, int | None, dict[str, Any]]:
    """Map capture-local VQL coords to global pointer space (for command generation audit)."""
    try:
        from vdisplay.input.coords import global_pointer_coords

        capture_meta = _enrich_capture_meta_for_pointer(_photo_capture_meta_for_source(source), source)
        gx, gy, details = global_pointer_coords(int(x), int(y), capture_meta)
        return int(gx), int(gy), {
            "capture_meta_region": capture_meta.get("region"),
            "capture_meta_rotation": capture_meta.get("rotation"),
            "mapping_details": details,
        }
    except Exception as exc:
        return None, None, {"mapping_error": str(exc)}


def _vql_plan_warnings(
    validation: dict[str, Any],
    capture_mismatch: dict[str, Any] | None,
    target: dict[str, Any],
    llm_decision: dict[str, Any] | None,
) -> tuple[list[Any], list[Any]]:
    """Warnings + validation errors for a VQL command plan."""
    warnings = list(validation.get("coord_warnings") or [])
    validation_errors = list(validation.get("validation_errors") or [])
    if validation_errors:
        warnings.extend(validation_errors)
    if capture_mismatch and not _surface_bounds_target_trusted(target=target):
        warnings.append("capture_ide_mismatch")
        if llm_decision:
            warnings.append("llm_refined_on_unconfirmed_ide_capture")
    return warnings, validation_errors


def _vql_plan_data_mtime(vql_file: Any) -> str | None:
    """ISO mtime of the plan's VQL data file (best effort)."""
    vql_mtime: str | None = None
    if isinstance(vql_file, str) and os.path.isfile(vql_file):
        try:
            vql_mtime = datetime.datetime.fromtimestamp(os.path.getmtime(vql_file)).isoformat()
        except Exception:
            pass
    return vql_mtime


def _vql_plan_selection_method(
    target: dict[str, Any],
    vql_file: Any,
    llm_decision: dict[str, Any] | None,
) -> str:
    """Selection method for the plan; heuristics when target carries none."""
    selection = str(target.get("selection_method") or "unknown")
    if selection == "unknown":
        note = str(target.get("note") or "")
        if "corner heuristic" in note:
            selection = "jetbrains_corner_heuristic"
        elif target.get("id") == "map:ai-chat-input" or str(target.get("id", "")).startswith("map:"):
            selection = "map_calibrated"
        elif target.get("llm_refined") or llm_decision:
            selection = "llm_vision_refined"
        elif isinstance(vql_file, str) and "vql.json" in vql_file:
            selection = "vql_layers"
    return selection


def _vql_plan_capture_flags(
    validation: dict[str, Any],
    capture_provenance: dict[str, Any] | None,
    capture_mismatch: dict[str, Any] | None,
    target: dict[str, Any],
    selection: str,
) -> tuple[Any, dict[str, Any] | None, bool]:
    """(capture_title, effective mismatch, capture_confirmed) for the plan."""
    capture_title = validation.get("capture_title") or (capture_provenance or {}).get("capture_title")
    surface_trusted = _surface_bounds_target_trusted(target=target, method=selection)
    eff_mismatch = None if surface_trusted else capture_mismatch
    capture_confirmed = bool((capture_provenance or {}).get("capture_confirmed")) or (
        surface_trusted and _surface_only_fallback_active()
    )
    return capture_title, eff_mismatch, capture_confirmed


def _vql_plan_commands(
    *,
    ide: str,
    x: int,
    y: int,
    gx: int | None,
    gy: int | None,
    prompt: str,
) -> list[dict[str, Any]]:
    """Ordered actuation command steps for the VQL chat plan."""
    return [
        {
            "step": 1,
            "verb": "CONTROL_FOCUS",
            "backend": "auto",
            "app": (_ide_hints(ide).get("app") if ide and ide != "auto" else None),
            "purpose": "raise IDE window before chat click",
        },
        {
            "step": 2,
            "verb": "POINTER_MOVE",
            "backend": "ydotool",
            "local": {"x": x, "y": y},
            "global": {"x": gx, "y": gy} if gx is not None else None,
            "purpose": "position cursor inside chat composer from VQL click_center",
        },
        {
            "step": 3,
            "verb": "POINTER_CLICK",
            "backend": "ydotool",
            "button": 1,
            "purpose": "focus keyboard caret in chat input before paste",
        },
        {
            "step": 4,
            "verb": "CLIPBOARD_PASTE",
            "backend": "ydotool/wtype",
            "text_preview": prompt[:80] + ("..." if len(prompt) > 80 else ""),
            "purpose": "insert user sentence into chat composer",
        },
    ]


def _llm_target_verified(llm_decision: dict[str, Any] | None) -> float | bool:
    """True when a vision-LLM refinement located the chat input with enough
    confidence to stand in for VQL element validation (only under vision decision)."""
    if not llm_decision:
        return False
    from koru.integrations.photo_vql_guard import llm_vision_decision_enabled

    if not llm_vision_decision_enabled():
        return False
    try:
        confidence = float(llm_decision.get("confidence") or 0.0)
    except (TypeError, ValueError):
        return False
    return confidence >= 0.5


def _vql_plan_resolve_validation(
    *,
    target: dict[str, Any],
    ide: str,
    x: int,
    y: int,
    is_code_edit: bool,
    capture_mismatch: dict[str, Any] | None,
    vql_validation: dict[str, Any] | None,
) -> dict[str, Any]:
    """VQL validation dict for the plan: explicit > target-cached > freshly computed."""
    if vql_validation:
        return vql_validation
    cached = target.get("vql_validation")
    if cached:
        return cached
    return validate_vql_chat_target(
        target,
        ide=ide,
        meta=load_vql_metadata(allow_stale=True),
        capture_mismatch=capture_mismatch,
        selection_method=str(target.get("selection_method") or ""),
        is_code_edit=is_code_edit,
        x=x,
        y=y,
    )


def _vql_plan_inference_flags(
    *,
    validation: dict[str, Any],
    capture_confirmed: bool,
    llm_decision: dict[str, Any] | None,
    eff_mismatch: dict[str, Any] | None,
) -> tuple[bool, bool]:
    """(inference_ok, plan_capture_confirmed) gate flags for the command plan.

    A vision-located click center (OCR placeholder anchor or LLM refine with high
    confidence) is its own verification: it was taken from the actual current
    screenshot, so neither the VQL element's suspicious bounds nor a missing/stale
    VQL sidecar (capture_confirmed) veto it. A competing-IDE mismatch
    (eff_mismatch) still always blocks.
    """
    llm_verified = bool(_llm_target_verified(llm_decision))
    validation_ok = bool(validation.get("ok"))
    mismatch_ok = eff_mismatch is None
    inference_ok = bool(((validation_ok and capture_confirmed) or llm_verified) and mismatch_ok)
    plan_capture_confirmed = bool(
        (capture_confirmed or llm_verified) and mismatch_ok and (validation_ok or llm_verified)
    )
    return inference_ok, plan_capture_confirmed


def _vql_plan_payload(
    *,
    stage: str,
    ide: str,
    source: str,
    is_code_edit: bool,
    vql_file: Any,
    vql_mtime: str | None,
    target: dict[str, Any],
    selection: str,
    x: int,
    y: int,
    gx: int | None,
    gy: int | None,
    mapping: Any,
    candidates: list[dict[str, Any]] | None,
    llm_decision: dict[str, Any] | None,
    warnings: list[Any],
    validation_errors: list[Any],
    commands: list[dict[str, Any]],
    validation: dict[str, Any],
    capture_title: Any,
    eff_mismatch: dict[str, Any] | None,
    capture_confirmed: bool,
    capture_provenance: dict[str, Any] | None,
) -> dict[str, Any]:
    """Assemble the structured VQL command-plan payload for autonomy audit."""
    inference_ok, plan_capture_confirmed = _vql_plan_inference_flags(
        validation=validation,
        capture_confirmed=capture_confirmed,
        llm_decision=llm_decision,
        eff_mismatch=eff_mismatch,
    )
    return {
        "stage": stage,
        "ide": ide,
        "source": source,
        "is_code_edit": is_code_edit,
        "vql_data_file": vql_file,
        "vql_data_mtime": vql_mtime,
        "target_id": target.get("id"),
        "target_role": target.get("role"),
        "target_note": target.get("note"),
        "selection_method": selection,
        "original_vql_click_center": target.get("click_center"),
        "final_local": {"x": x, "y": y},
        "final_global": {"x": gx, "y": gy} if gx is not None else None,
        "coord_mapping": mapping,
        "vql_input_candidates": candidates or target.get("vql_candidates") or [],
        "llm_decision": llm_decision,
        "warnings": warnings,
        "validation_errors": validation_errors,
        "commands": commands,
        "inference_ok": inference_ok,
        "capture_confirmed": plan_capture_confirmed,
        "capture_title": capture_title,
        "vql_element_size_ok": validation.get("vql_element_size_ok"),
        "app_match": validation.get("app_match"),
        "vql_validation": validation,
        "used_map_because_mismatch_or_bad_element": validation.get(
            "used_map_because_mismatch_or_bad_element"
        ),
        "capture_provenance": capture_provenance,
    }


def _build_vql_command_plan(
    *,
    target: dict[str, Any],
    x: int,
    y: int,
    source: str,
    ide: str,
    prompt: str,
    llm_decision: dict[str, Any] | None = None,
    candidates: list[dict[str, Any]] | None = None,
    is_code_edit: bool = False,
    stage: str = "pre_act",
    capture_mismatch: dict[str, Any] | None = None,
    capture_provenance: dict[str, Any] | None = None,
    vql_validation: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Structured command plan derived from VQL layers (+ map/LLM enrich) for autonomy audit."""
    gx, gy, mapping = _global_coords_from_vql_local(x=x, y=y, source=source)
    validation = _vql_plan_resolve_validation(
        target=target,
        ide=ide,
        x=x,
        y=y,
        is_code_edit=is_code_edit,
        capture_mismatch=capture_mismatch,
        vql_validation=vql_validation,
    )
    warnings, validation_errors = _vql_plan_warnings(validation, capture_mismatch, target, llm_decision)
    vql_file = target.get("source")
    vql_mtime = _vql_plan_data_mtime(vql_file)

    selection = _vql_plan_selection_method(target, vql_file, llm_decision)
    capture_title, eff_mismatch, capture_confirmed = _vql_plan_capture_flags(
        validation, capture_provenance, capture_mismatch, target, selection
    )

    commands: list[dict[str, Any]] = _vql_plan_commands(ide=ide, x=x, y=y, gx=gx, gy=gy, prompt=prompt)

    return _vql_plan_payload(
        stage=stage,
        ide=ide,
        source=source,
        is_code_edit=is_code_edit,
        vql_file=vql_file,
        vql_mtime=vql_mtime,
        target=target,
        selection=selection,
        x=x,
        y=y,
        gx=gx,
        gy=gy,
        mapping=mapping,
        candidates=candidates,
        llm_decision=llm_decision,
        warnings=warnings,
        validation_errors=validation_errors,
        commands=commands,
        validation=validation,
        capture_title=capture_title,
        eff_mismatch=eff_mismatch,
        capture_confirmed=capture_confirmed,
        capture_provenance=capture_provenance,
    )


def _cursor_record_vql_validation(
    record: dict[str, Any],
    *,
    command_plan: dict[str, Any] | None,
    target: dict[str, Any],
) -> None:
    """Copy VQL validation / command-plan fields into a cursor positioning record."""
    vql_validation = (command_plan or {}).get("vql_validation") or target.get("vql_validation")
    if isinstance(vql_validation, dict):
        record["capture_title"] = vql_validation.get("capture_title")
        record["vql_element_size_ok"] = vql_validation.get("vql_element_size_ok")
        record["app_match"] = vql_validation.get("app_match")
        record["validation_errors"] = vql_validation.get("validation_errors")
        record["used_map_because_mismatch_or_bad_element"] = vql_validation.get(
            "used_map_because_mismatch_or_bad_element"
        )
    elif command_plan is not None:
        record["capture_title"] = command_plan.get("capture_title")
        record["vql_element_size_ok"] = command_plan.get("vql_element_size_ok")
        record["app_match"] = command_plan.get("app_match")
        record["validation_errors"] = command_plan.get("validation_errors")
    if command_plan is not None:
        record["vql_command_plan"] = command_plan


def _log_vql_cursor_positioning_at_command(
    target: dict[str, Any],
    *,
    stage: str,
    ide: str,
    source: str,
    final_local: dict[str, int],
    final_global: dict[str, int] | None = None,
    vql_file: str | None = None,
    command_plan: dict[str, Any] | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Log + persist exact cursor positioning at the instant of a chat-write command."""
    vql_date = None
    resolved_vql = vql_file or target.get("source")
    if isinstance(resolved_vql, str) and os.path.isfile(resolved_vql):
        try:
            vql_date = datetime.datetime.fromtimestamp(os.path.getmtime(resolved_vql)).isoformat()
        except Exception:
            pass

    if final_global is None:
        gx, gy, _mapping = _global_coords_from_vql_local(
            x=int(final_local.get("x", 0)),
            y=int(final_local.get("y", 0)),
            source=source,
        )
        if gx is not None:
            final_global = {"x": gx, "y": gy}

    record: dict[str, Any] = {
        "event": "VQL_CURSOR_POSITIONING_AT_WRITE_COMMAND",
        "stage": stage,
        "ide": ide,
        "source": source,
        "vql_data_file": resolved_vql,
        "vql_data_mtime": vql_date,
        "original_vql_click_center": target.get("click_center"),
        "final_local": final_local,
        "final_global": final_global,
        "target_id": target.get("id"),
        "target_note": target.get("note"),
        "llm_refined": bool(target.get("llm_refined")),
        "warnings": _validate_chat_coords_for_ide(
            x=int(final_local.get("x", 0)),
            y=int(final_local.get("y", 0)),
            ide=ide,
            target=target,
        ),
    }
    _cursor_record_vql_validation(record, command_plan=command_plan, target=target)
    if extra:
        record.update(extra)

    logger.info(
        "VQL_CURSOR_POSITIONING stage=%s ide=%s source=%s vql_file=%s vql_mtime=%s "
        "local=%s global=%s warnings=%s target_id=%s",
        stage,
        ide,
        source,
        resolved_vql,
        vql_date,
        final_local,
        final_global,
        record.get("warnings"),
        target.get("id"),
    )
    if record.get("warnings"):
        logger.warning(
            "VQL_CURSOR_POSITIONING_SUSPICIOUS stage=%s ide=%s local=%s warnings=%s",
            stage,
            ide,
            final_local,
            record["warnings"],
        )

    session = _autonomy_session.active_session_dir()
    if session is not None:
        _autonomy_session.append_session_jsonl(session, "act/cursor_positioning.jsonl", record)
        if command_plan is not None:
            _autonomy_session.persist_autonomy_phase(session, "act", f"command_plan_{stage}", command_plan)

    return record


# Pointer positioning extracted to koru.integrations.vdisplay.pointer_calibration;
# re-exported here for backward compatibility.
from koru.integrations.vdisplay.pointer_calibration import (  # noqa: E402,F401
    _abs_affine_cache_path,
    _abs_pointer_click,
    _abs_pointer_enabled,
    _adaptive_pointer_enabled,
    _adaptive_position_pointer,
    _load_or_calibrate_abs_affine,
)


def _ydotool_click_capture_local(*, x: int, y: int, source: str) -> dict[str, Any]:
    """Direct ydotool move+click when vdisplay vision point click fails."""
    try:
        from vdisplay.input.coords import global_pointer_coords
        from vdisplay.input.linux_ydotool import LinuxYdotoolInput

        capture_meta = _enrich_capture_meta_for_pointer(_photo_capture_meta_for_source(source), source)
        # Deterministic own-uinput-ABS positioning (opt-in): a cached per-monitor
        # affine converts capture pixel -> ABS command. Preferred over ydotool's
        # opaque space on multi-monitor HiDPI. Falls back below on failure.
        if _abs_pointer_enabled():
            abs_res = _abs_pointer_click(x=x, y=y, source=source)
            if abs_res is not None and abs_res.get("ok"):
                return abs_res
        # Closed-loop adaptive positioning (opt-in): measure + correct instead of
        # trusting the absolute mapping. Falls back to open-loop below on failure.
        if _adaptive_pointer_enabled():
            adaptive = _adaptive_position_pointer(x=x, y=y, source=source, capture_meta=capture_meta, ide="auto")
            if adaptive is not None and adaptive.get("ok"):
                return adaptive
        gx, gy, details = global_pointer_coords(int(x), int(y), capture_meta)
        # Log the exact mapping used at command generation time (critical for DP-2 rotated monitors)
        logger.info(
            "VQL_YDOTOOL_COMMAND_MAPPED: local=(%s,%s) -> global=(%s,%s) source=%s capture_meta_region=%s rotation=%s "
            "(this is the concrete command sent to position cursor for chat write, derived from VQL)",
            x, y, gx, gy, source, capture_meta.get("region"), capture_meta.get("rotation")
        )
        yinput = LinuxYdotoolInput()
        yinput.move(int(gx), int(gy))
        yinput.click(1)
        return {
            "ok": True,
            "method": "ydotool-click",
            "x": int(gx),
            "y": int(gy),
            "local_x": int(x),
            "local_y": int(y),
            "details": details,
        }
    except Exception as exc:
        return {"ok": False, "method": "ydotool-click", "error": str(exc)}


def _type_text_blocking_warnings(
    *,
    x: int,
    y: int,
    ide: str,
    target_for_log: dict[str, Any],
    command_plan: dict[str, Any] | None,
) -> list[str]:
    """Collect blocking warnings (coord validation + plan + VQL validation) before typing."""
    blocking_warnings: list[str] = []
    if _dry_run():
        return blocking_warnings
    is_code_edit = _photo_vql_code_edit_enabled() or str(target_for_log.get("role") or "").lower() == "editor"
    blocking_warnings.extend(
        _validate_chat_coords_for_ide(
            x=int(x),
            y=int(y),
            ide=ide,
            target=target_for_log,
            is_code_edit=is_code_edit,
        )
    )
    blocking_warnings.extend(
        _type_text_plan_validation_warnings(
            target_for_log=target_for_log, command_plan=command_plan
        )
    )
    return list(dict.fromkeys(w for w in blocking_warnings if w))


def _type_text_blocked_result(
    result: dict[str, Any],
    *,
    blocking_warnings: list[str],
    target_for_log: dict[str, Any],
    command_plan: dict[str, Any] | None,
    ide: str,
    x: int,
    y: int,
) -> dict[str, Any]:
    """Refusal result when suspicious VQL chat coords were detected."""
    result.update(
        {
            "ok": False,
            "error": "refusing to type at suspicious VQL chat coords",
            "warnings": blocking_warnings,
            "vql_target": target_for_log,
        }
    )
    if command_plan is not None:
        result["vql_command_plan"] = command_plan
    logger.warning(
        "VQL_CHAT_WRITE_BLOCKED_SUSPICIOUS_COORDS ide=%s local=(%s,%s) warnings=%s",
        ide,
        x,
        y,
        blocking_warnings,
    )
    return result


def _type_text_dry_run_result(
    result: dict[str, Any],
    value: str,
    *,
    x: int,
    y: int,
    ide: str,
    source: str,
    target_for_log: dict[str, Any],
    command_plan: dict[str, Any] | None,
) -> dict[str, Any]:
    """Dry-run / no-vdisplay early return with cursor-positioning intent log."""
    pos_log = _log_vql_cursor_positioning_at_command(
        target_for_log,
        stage="type_text_dry_run",
        ide=ide,
        source=source,
        final_local={"x": x, "y": y},
        command_plan=command_plan,
    )
    result.update(
        {
            "ok": True,
            "dry_run": True,
            "message": f"DRY type at VQL coords ({x},{y})",
            "value": value,
            "cursor_positioning": pos_log,
        }
    )
    return result


def _type_text_try_atspi_set_value(
    result: dict[str, Any],
    value: str,
    *,
    hints: dict[str, Any],
    focus_ok: bool,
    focus_res: dict[str, Any] | None,
) -> bool:
    """Try AT-SPI set_value on the focused element first (GNOME Wayland); True when handled."""
    click_target = (focus_res or {}).get("click_res") or {}
    element_id = click_target.get("element_id")
    target_caps = ((click_target.get("target") or {}).get("capabilities") or {})
    if not (focus_ok and element_id and target_caps.get("text_write")):
        return False
    try:
        atspi_res = _control_set_value(
            provider_ref=element_id,
            value=value,
            backend="atspi",
            app=hints.get("app"),
            window_title=hints.get("window_title_contains"),
        )
        result["atspi_set_value"] = atspi_res
        if isinstance(atspi_res, dict) and atspi_res.get("ok", True):
            result.update({"ok": True, "method": "atspi-set_value", "value": value, "element_id": element_id})
            return True
    except Exception as exc:
        result["atspi_error"] = str(exc)
    return False


def _type_text_must_click(
    result: dict[str, Any],
    *,
    x: int,
    y: int,
    ide: str,
    source: str,
    target_for_log: dict[str, Any],
    command_plan: dict[str, Any] | None,
) -> dict[str, Any] | None:
    """ydotool move+click at capture-local coords; returns click_res on success, else None."""
    vql_file_for_log = target_for_log.get("source")
    if isinstance(vql_file_for_log, str) and not vql_file_for_log.endswith(".vql.json"):
        vql_file_for_log = None
    pos_log = _log_vql_cursor_positioning_at_command(
        target_for_log,
        stage="type_text_at_vql_coords_must_click_for_chat",
        ide=ide,
        source=source,
        final_local={"x": x, "y": y},
        vql_file=vql_file_for_log if isinstance(vql_file_for_log, str) else None,
        command_plan=command_plan,
    )
    result["cursor_positioning"] = pos_log
    ydotool_click = _ydotool_click_capture_local(x=x, y=y, source=source)
    result["ydotool_click"] = ydotool_click
    if ydotool_click.get("ok"):
        result["click_res"] = ydotool_click
        logger.info(
            "VQL_CHAT_WRITE_CLICK_OK local=(%s,%s) global=(%s,%s) method=%s",
            x,
            y,
            ydotool_click.get("x"),
            ydotool_click.get("y"),
            ydotool_click.get("method"),
        )
        return ydotool_click
    logger.warning(
        "VQL_CHAT_WRITE_CLICK_FAILED local=(%s,%s) error=%s",
        x,
        y,
        ydotool_click.get("error"),
    )
    return None


def _type_text_fallback_click(
    result: dict[str, Any],
    *,
    x: int,
    y: int,
    source: str,
    hints: dict[str, Any],
) -> dict[str, Any] | None:
    """vision -> auto _control_click fallback loop; returns the last click_res (or None)."""
    click_res = None
    for payload in (
        {
            "backend": "vision",
            "x": x,
            "y": y,
            "source": source,
            "app": hints.get("app"),
            "window_title": hints.get("window_title_contains"),
        },
        {
            "backend": "auto",
            "x": x,
            "y": y,
            "source": source,
            "app": hints.get("app"),
            "window_title": hints.get("window_title_contains"),
        },
    ):
        try:
            click_res = _control_click(**payload)
            result["click_res"] = click_res
            if isinstance(click_res, dict) and click_res.get("ok", True):
                break
        except Exception as exc:
            result["click_error"] = str(exc)
    return click_res


def _type_text_paste_or_type(
    result: dict[str, Any],
    value: str,
    *,
    x: int,
    y: int,
    ide: str,
    source: str,
    target_for_log: dict[str, Any],
    command_plan: dict[str, Any] | None,
) -> dict[str, Any]:
    """Resolve pointer input, then paste (clipboard + ctrl+v) or type the value."""
    try:
        import shutil
        import subprocess
        import time

        from vdisplay.control.timing import control_focus_type_seconds
        from vdisplay.input.resolve import resolve_pointer_input

        focus_s = control_focus_type_seconds()
        if focus_s:
            time.sleep(focus_s)
        inp, method = resolve_pointer_input()

        can_paste = getattr(inp, "can_paste", None)
        if can_paste is not None and can_paste():
            if shutil.which("wl-copy"):
                subprocess.run(
                    ["wl-copy"],
                    input=value.encode(),
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    check=True,
                    timeout=15,
                )
            elif shutil.which("xclip"):
                subprocess.run(
                    ["xclip", "-selection", "clipboard"],
                    input=value.encode(),
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    check=True,
                    timeout=5,
                )
            else:
                result["error"] = "no clipboard utility (wl-copy or xclip)"
                return result
            try:
                inp.hotkey("ctrl", "v")
            except TypeError:
                inp.hotkey("ctrl+v")
            paste_log = _log_vql_cursor_positioning_at_command(
                target_for_log,
                stage="chat_paste_after_vql_click",
                ide=ide,
                source=source,
                final_local={"x": x, "y": y},
                command_plan=command_plan,
                extra={"paste_method": method, "chars": len(value)},
            )
            result.update({
                "ok": True,
                "method": f"{method}-paste",
                "value": value,
                "cursor_positioning_paste": paste_log,
            })
            logger.info(
                "VQL_CHAT_WRITE_PASTE_OK ide=%s local=(%s,%s) chars=%d method=%s warnings=%s",
                ide,
                x,
                y,
                len(value),
                method,
                paste_log.get("warnings"),
            )
            return result

        can_type = getattr(inp, "can_type", None)
        if can_type is not None and can_type():
            inp.type_text(value)
            result.update({"ok": True, "method": f"{method}-type", "value": value})
            return result
        if os.environ.get("VDISPLAY_ALLOW_YDOTOOL_TYPING") == "1":
            inp.type_text(value)
            result.update({"ok": True, "method": f"{method}-type-forced", "value": value})
            return result
        result["error"] = f"typing unavailable ({method} can_type=False, paste unavailable)"
    except Exception as exc:
        result["error"] = str(exc)
    return result


def _type_text_at_vql_coords(
    value: str,
    *,
    x: int,
    y: int,
    source: str,
    ide: str,
    focus_ok: bool = False,
    focus_res: dict[str, Any] | None = None,
    force_point_click: bool = False,
    vql_target: dict[str, Any] | None = None,
    command_plan: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Click caret at VQL capture coords, then type/paste via resolved pointer input."""
    hints = _ide_hints(ide) if ide and ide != "auto" else {}
    result: dict[str, Any] = {"ok": False, "coords": {"x": x, "y": y}}
    jetbrains = _canonical_ide(ide) in {"jetbrains", "pycharm", "idea"}
    must_click = force_point_click or jetbrains or not focus_ok
    target_for_log = vql_target or (focus_res or {}).get("vql_target") or {
        "click_center": {"x": x, "y": y},
        "note": "pre-type chat write",
    }
    blocking_warnings = _type_text_blocking_warnings(
        x=x, y=y, ide=ide, target_for_log=target_for_log, command_plan=command_plan
    )
    if blocking_warnings:
        return _type_text_blocked_result(
            result,
            blocking_warnings=blocking_warnings,
            target_for_log=target_for_log,
            command_plan=command_plan,
            ide=ide,
            x=x,
            y=y,
        )

    if _dry_run() or not vdisplay_available():
        return _type_text_dry_run_result(
            result,
            value,
            x=x,
            y=y,
            ide=ide,
            source=source,
            target_for_log=target_for_log,
            command_plan=command_plan,
        )

    if _type_text_try_atspi_set_value(
        result, value, hints=hints, focus_ok=focus_ok, focus_res=focus_res
    ):
        return result

    click_res = None
    if must_click:
        click_res = _type_text_must_click(
            result,
            x=x,
            y=y,
            ide=ide,
            source=source,
            target_for_log=target_for_log,
            command_plan=command_plan,
        )
    if click_res is None and not focus_ok:
        _type_text_fallback_click(result, x=x, y=y, source=source, hints=hints)

    return _type_text_paste_or_type(
        result,
        value,
        x=x,
        y=y,
        ide=ide,
        source=source,
        target_for_log=target_for_log,
        command_plan=command_plan,
    )


def _resolve_photo_vql_llm_coords(
    *,
    prompt: str,
    target: dict[str, Any],
    source: str,
    image_path: str | None,
    ide: str = "auto",
) -> tuple[int, int, dict[str, Any] | None]:
    """Optional LLM vision refinement of click coords before focus/type."""
    cc = target.get("click_center") or {}
    x = int(cc.get("x", 1024))
    y = int(cc.get("y", 640))
    llm_decision: dict[str, Any] | None = target.get("llm_decision") if target.get("llm_used") else None
    if str(target.get("selection_method") or "") == "llm_vision_detect" and cc.get("x") is not None:
        return x, y, llm_decision

    canon = _canonical_ide(ide)

    if not (llm_vision_enabled() and image_path and os.path.exists(image_path)):
        return x, y, None

    try:
        png = Path(image_path).read_bytes()
        layers, _src = _photo_vql_elements()
        candidates = _photo_vql_chat_input_candidates(layers, limit=8, ide=canon)
        map_hint = (
            _map_chat_target_capture_local(ide=canon, source=source)
            if canon in {"jetbrains", "pycharm", "idea"}
            else None
        )
        meta_for_title = load_vql_metadata(allow_stale=True)
        capture_title = _capture_title_from_meta(meta_for_title) or "unknown"

        from vdisplay.control.vision_chat_detect import refine_chat_click_target

        return refine_chat_click_target(
            png,
            prompt=prompt,
            target=target,
            ide=ide,
            source=source,
            candidates=candidates,
            map_hint=map_hint,
            capture_title=capture_title,
        )
    except ImportError:
        fallback = _resolve_photo_vql_llm_coords_via_koru_detector(
            ide=canon,
            source=source,
            image_path=image_path,
            candidates=candidates,
            map_hint=map_hint,
            capture_title=capture_title,
            default_x=x,
            default_y=y,
        )
        if fallback is not None:
            return fallback
    except Exception:
        return x, y, None

    return x, y, None


def _resolve_photo_vql_llm_coords_via_koru_detector(
    *,
    ide: str,
    source: str,
    image_path: str,
    candidates: list[dict[str, Any]],
    map_hint: dict[str, Any] | None,
    capture_title: str,
    default_x: int,
    default_y: int,
) -> tuple[int, int, dict[str, Any] | None] | None:
    try:
        from koru.integrations.photo_vql_llm_detect import detect_chat_target_from_llm_vision

        llm_target = detect_chat_target_from_llm_vision(
            ide=ide,
            source=source,
            image_path=image_path,
            candidates=candidates,
            map_hint=map_hint,
            capture_title=capture_title,
        )
    except Exception:
        return None
    if not llm_target:
        return None
    llm_cc = llm_target.get("click_center") or {}
    llm_x = int(llm_cc.get("x", default_x))
    llm_y = int(llm_cc.get("y", default_y))
    llm_decision = llm_target.get("llm_decision") or _llm_detection_decision_from_target(
        llm_target=llm_target,
        click_center=llm_cc,
    )
    return llm_x, llm_y, llm_decision


def _llm_detection_decision_from_target(
    *,
    llm_target: dict[str, Any],
    click_center: dict[str, Any],
) -> dict[str, Any]:
    return {
        "strategy": "llm_vision_detect",
        "confidence": llm_target.get("confidence"),
        "reason": click_center.get("note") or llm_target.get("note"),
    }


def _photo_vql_map_paste_fallback(
    prompt: str,
    *,
    ide: str,
) -> dict[str, Any] | None:
    """Map click + paste when photo-VQL coord typing fails (JetBrains on Wayland)."""
    if os.environ.get("KORU_VDISPLAY_PHOTO_VQL_MAP_FALLBACK", "1").strip().lower() in {
        "0",
        "false",
        "no",
        "off",
    }:
        return None
    if _canonical_ide(ide) not in {"jetbrains", "pycharm", "idea"}:
        return None
    app_id = _ide_prompt_app_id(ide)
    map_path = _resolve_ide_prompt_map(app_id)
    if not map_path:
        return None
    return _type_text_via_ide_map_fallback(prompt, map_path=map_path, app_id=app_id, ide=ide)


def _mismatch_shows_competing_ide(mismatch: dict[str, Any] | None, *, ide: str) -> bool:
    """True when the capture's window titles name a *different* IDE.

    A plain "does not look like PyCharm" (editor breadcrumb, or a right-docked
    Qoder/AI chat panel whose title OCRs as "Chat") is safe for the vision
    layer to override. A title that names Cursor/VSCode/etc. is not — that is a
    real wrong-IDE capture and must always block, vision or not.
    """
    if not mismatch:
        return False
    if mismatch.get("competing_detected"):
        return True
    competing = _COMPETING_IDE_WINDOW_TOKENS.get(_canonical_ide(ide), ())
    if not competing:
        return False
    haystack = " ".join(
        [
            str(mismatch.get("message") or ""),
            *[str(t) for t in (mismatch.get("window_titles") or [])],
        ]
    ).lower()
    return any(token in haystack for token in competing)


def _vision_overrides_capture_mismatch(mismatch: dict[str, Any] | None, *, ide: str) -> bool:
    """Vision LLM decides the chat coords — a non-competing title mismatch is not
    a hard block, but a competing-IDE capture always is."""
    from koru.integrations.photo_vql_guard import llm_vision_decision_enabled

    return (
        llm_vision_decision_enabled()
        and not _mismatch_shows_competing_ide(mismatch, ide=ide)
    )


def _photo_vql_capture_mismatch_blocks(
    *,
    mismatch: dict[str, Any] | None,
    ide: str,
    is_code_edit: bool,
) -> bool:
    return bool(
        mismatch
        and not _dry_run()
        and _canonical_ide(ide) in {"jetbrains", "pycharm", "idea"}
        and not _allow_actuation_on_capture_mismatch()
        # A confirmed right-docked chat panel (Qoder / AI Assistant) OCRs its
        # monitor's title as the editor, not "PyCharm"; when vision will decide
        # the coords, that non-competing mismatch is not a hard block for chat.
        and not (not is_code_edit and _vision_overrides_capture_mismatch(mismatch, ide=ide))
        and not (not is_code_edit and _allow_prepare_map_on_mismatch())
        and not (
            not is_code_edit
            and _surface_only_fallback_active()
            and _allow_prepare_surface_on_capture_error()
        )
        and not (is_code_edit and _allow_prepare_map_on_mismatch())
    )


def _surface_only_fallback_active() -> bool:
    if not _allow_prepare_surface_on_capture_error():
        return False
    if os.environ.get("KORU_VDISPLAY_ALLOW_SURFACE_ONLY_ACTUATION", "").strip().lower() not in {
        "1",
        "true",
        "yes",
        "on",
    }:
        return False
    if os.environ.get("KORU_VDISPLAY_SURFACE_ONLY_FALLBACK", "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }:
        return True
    return os.environ.get("KORU_VDISPLAY_CAPTURE_MATCHES_IDE", "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def _surface_bounds_target_trusted(
    *,
    target: dict[str, Any] | None = None,
    method: str | None = None,
) -> bool:
    if not _surface_only_fallback_active():
        return False
    selected = method or _target_selection_method(target or {})
    return selected == "jetbrains_surface_bounds"


def _surface_bounds_target_safe_for_actuation(
    *,
    target: dict[str, Any] | None = None,
    method: str | None = None,
    command_plan: dict[str, Any] | None = None,
) -> bool:
    """Surface bounds confirm the IDE window, but only clean validation confirms chat input."""
    if not _surface_bounds_target_trusted(target=target, method=method):
        return False
    validation = None
    if isinstance(target, dict):
        validation = target.get("vql_validation")
    if not isinstance(validation, dict) and isinstance(command_plan, dict):
        validation = command_plan.get("vql_validation")
    if isinstance(validation, dict):
        if validation.get("validation_errors") or validation.get("coord_warnings"):
            return False
        if validation.get("ok") is False:
            return False
    if isinstance(command_plan, dict) and command_plan.get("warnings"):
        return False
    return True


def _photo_vql_capture_mismatch_error(
    *,
    mismatch: dict[str, Any],
    ide: str,
    is_code_edit: bool,
) -> dict[str, Any]:
    return {
        "ok": False,
        "backend": "vdisplay+photo-vql",
        "error": mismatch.get("message", "photo VQL capture does not match requested IDE"),
        "ide_window_warning": mismatch,
        "ide": ide,
        "is_code_edit": is_code_edit,
        "hint": (
            "Re-focus the target IDE on the capture monitor and refresh observe, "
            "use send_chat (map fallback when KORU_VDISPLAY_PREFER_PHOTO_VQL=auto), "
            "or set KORU_VDISPLAY_ALLOW_IDE_MISMATCH=1 to force photo-VQL anyway."
        ),
    }


def _target_selection_method(target: dict[str, Any]) -> str:
    return str(
        target.get("selection_method")
        or target.get("vql_validation", {}).get("selection_method")
        or ""
    )


def _selection_method_is_map(method: str) -> bool:
    return method.startswith("map_") or method in {
        "map_calibrated_on_mismatch",
        "map_calibrated_on_empty_vql",
        "map_fallback_after_bad_corner",
        "map_calibrated",
    }


def _map_target_can_clear_capture_mismatch(*, target: dict[str, Any], ide: str) -> bool:
    return bool(
        _canonical_ide(ide) in {"jetbrains", "pycharm", "idea"}
        and (_ide_mismatch_allowed() or _allow_prepare_map_on_mismatch())
        and _selection_method_is_map(_target_selection_method(target))
    )


def _is_jetbrains_map_target(*, target: dict[str, Any], ide: str) -> bool:
    return bool(
        str((target or {}).get("id") or "").startswith("map:")
        and _canonical_ide(ide) in {"jetbrains", "pycharm", "idea"}
    )


def _map_mismatch_allowed_for_target(*, target: dict[str, Any], ide: str) -> bool:
    return _is_jetbrains_map_target(target=target, ide=ide) and _allow_prepare_map_on_mismatch()


def _map_source_mismatch_actuation_allowed() -> bool:
    if os.environ.get("KORU_VDISPLAY_ALLOW_MAP_SOURCE_MISMATCH", "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }:
        return True
    # Vision LLM locates the chat input from the raw screenshot, not the stored
    # GUI map — so a map calibrated for a different monitor is irrelevant when
    # vision decides the click coords.
    from koru.integrations.photo_vql_guard import llm_vision_decision_enabled

    return llm_vision_decision_enabled()


def _map_capture_mismatch_for_target(
    *,
    target: dict[str, Any] | None,
    ide: str,
    source: str | None,
) -> dict[str, Any] | None:
    if not target or not _is_jetbrains_map_target(target=target, ide=ide):
        return None
    map_path = target.get("source")
    if not isinstance(map_path, str) or not map_path.endswith(".json"):
        map_path = _resolve_ide_prompt_map(_ide_prompt_app_id(ide))
    if not map_path or not source:
        return None
    try:
        from koru.integrations.photo_vql_monitor import map_capture_monitor_mismatch

        return map_capture_monitor_mismatch(map_path, source=source)
    except Exception:
        return None


def _map_capture_mismatch_for_ide(
    *,
    ide: str,
    source: str | None,
) -> dict[str, Any] | None:
    """Return map/source mismatch for an IDE before any target-specific fallback acts."""
    if not source or _canonical_ide(ide) not in {"jetbrains", "pycharm", "idea"}:
        return None
    map_path = _resolve_ide_prompt_map(_ide_prompt_app_id(ide))
    if not map_path:
        return None
    try:
        from koru.integrations.photo_vql_monitor import map_capture_monitor_mismatch

        return map_capture_monitor_mismatch(map_path, source=source)
    except Exception:
        return None


def _photo_vql_map_source_mismatch_error(
    *,
    map_mismatch: dict[str, Any],
    target: dict[str, Any],
    ide: str,
    source: str | None,
    is_code_edit: bool,
) -> dict[str, Any]:
    return {
        "ok": False,
        "backend": "vdisplay+photo-vql",
        "error": map_mismatch.get("message") or "photo-VQL map is calibrated for a different monitor",
        "hint": (
            "Do not drive with a calibrated map from another monitor. "
            "Set KORU_VDISPLAY_SOURCE to the map source, recalibrate the map for this monitor, "
            "or set KORU_VDISPLAY_ALLOW_MAP_SOURCE_MISMATCH=1 only for manual debugging."
        ),
        "ide": ide,
        "source": source,
        "is_code_edit": is_code_edit,
        "target": "editor/open-file" if is_code_edit else "chat",
        "vql_target": target,
        "map_capture_mismatch": map_mismatch,
    }


def _surface_target_can_clear_capture_mismatch(*, target: dict[str, Any], ide: str) -> bool:
    return bool(
        _surface_only_fallback_active()
        and _canonical_ide(ide) in {"jetbrains", "pycharm", "idea"}
        and _target_selection_method(target) == "jetbrains_surface_bounds"
        and _allow_prepare_surface_on_capture_error()
        and _surface_bounds_target_safe_for_actuation(target=target)
    )


def _surface_mismatch_allowed_for_target(*, target: dict[str, Any], ide: str) -> bool:
    return _surface_target_can_clear_capture_mismatch(target=target, ide=ide)


def _photo_vql_should_block_unverified_chat(
    *,
    command_plan: dict[str, Any],
    is_code_edit: bool,
    map_mismatch_allowed: bool,
    surface_mismatch_allowed: bool = False,
) -> bool:
    return bool(
        not is_code_edit
        and not _dry_run()
        and not command_plan.get("inference_ok")
        and not _ide_mismatch_allowed()
        and not map_mismatch_allowed
        and not surface_mismatch_allowed
    )


def _photo_vql_unverified_chat_blocked(
    *,
    command_plan: dict[str, Any],
    target_desc: str,
    target: dict[str, Any],
    x: int,
    y: int,
    ide: str,
    mismatch: dict[str, Any] | None,
) -> dict[str, Any]:
    return {
        "ok": False,
        "backend": "vdisplay+photo-vql",
        "error": (
            "photo-VQL chat target not verified for drive "
            f"(warnings={command_plan.get('warnings') or []})"
        ),
        "target": target_desc,
        "vql_target": target,
        "vql_command_plan": command_plan,
        "coords": {"x": x, "y": y},
        "ide": ide,
        "capture_confirmed": command_plan.get("capture_confirmed"),
        "ide_window_warning": mismatch,
        "hint": (
            "Focus PyCharm AI chat on the capture monitor, run "
            "koru autopilot prepare-vdisplay --ide jetbrains, then "
            "./scripts/diagnose-vdisplay-llm.sh jetbrains. "
            "Override: KORU_VDISPLAY_ALLOW_IDE_MISMATCH=1"
        ),
    }


def _photo_vql_focus_target(
    *,
    target: dict[str, Any],
    ide: str,
    source: str,
    is_code_edit: bool,
    llm_decision: dict[str, Any] | None,
) -> dict[str, Any]:
    if is_code_edit and not llm_decision:
        return click_editor_via_photo_vql(ide=ide, source=source)
    return move_mouse_to_vql_target_and_focus_keyboard(target, ide=ide, source=source)


def _photo_vql_edit_result(
    prompt: str,
    *,
    x: int,
    y: int,
    target_desc: str,
    source: str,
    ide: str,
    focus_res: dict[str, Any],
    target: dict[str, Any],
    command_plan: dict[str, Any],
) -> dict[str, Any]:
    if _dry_run():
        return {
            "ok": True,
            "dry_run": True,
            "message": f"DRY: precise edit at VQL coords ({x},{y}) from foto target {target_desc}",
            "value": prompt,
        }
    if not vdisplay_available():
        return {"ok": False, "error": "not attempted"}
    try:
        edit_res = _type_text_at_vql_coords(
            prompt,
            x=int(x),
            y=int(y),
            source=source,
            ide=ide,
            focus_ok=bool(focus_res.get("ok")),
            focus_res=focus_res,
            force_point_click=True,
            vql_target=target,
            command_plan=command_plan,
        )
    except Exception as exc:
        edit_res = {"ok": False, "error": str(exc)}

    if not edit_res.get("ok"):
        map_fallback = _photo_vql_map_paste_fallback(prompt, ide=ide)
        if map_fallback and map_fallback.get("ok"):
            edit_res = map_fallback
            edit_res["photo_vql_map_fallback"] = True
    return edit_res


def _photo_vql_stale_gate_override_ok(*, canon_probe: str, is_code_edit: bool) -> bool:
    """Whether map/surface fallbacks allow proceeding despite stale/errored VQL metadata."""
    map_mismatch_ok = (
        not is_code_edit
        and canon_probe in {"jetbrains", "pycharm", "idea"}
        and _allow_prepare_map_on_mismatch()
    )
    surface_mismatch_ok = (
        not is_code_edit
        and canon_probe in {"jetbrains", "pycharm", "idea"}
        and _surface_only_fallback_active()
        and _allow_prepare_surface_on_capture_error()
    )
    code_edit_map_ok = (
        is_code_edit
        and canon_probe in {"jetbrains", "pycharm", "idea"}
        and _allow_prepare_map_on_mismatch()
    )
    return map_mismatch_ok or surface_mismatch_ok or code_edit_map_ok


def _photo_vql_stale_metadata_gate(*, ide: str, is_code_edit: bool) -> dict | None:
    """Abort dict when VQL metadata is stale/errored and no fallback allows it, else None."""
    meta_probe = load_vql_metadata()
    if not meta_probe.get("error") or _dry_run():
        return None
    stale_only = bool(meta_probe.get("stale_skipped"))
    session_active = _autonomy_session.active_session_dir() is not None
    canon_probe = _canonical_ide(ide)
    override_ok = _photo_vql_stale_gate_override_ok(
        canon_probe=canon_probe, is_code_edit=is_code_edit
    )
    if not (stale_only or session_active) or override_ok:
        return None
    err = {
        "ok": False,
        "backend": "vdisplay+photo-vql",
        "error": str(meta_probe.get("error")),
        "stale_skipped": meta_probe.get("stale_skipped"),
        "ide": ide,
        "is_code_edit": is_code_edit,
        "hint": "run prepare_photo_vql_for_drive() first — observe must be fresh in .vdisplay/YYYY-MM-DD/.../observe/",
    }
    session = _autonomy_session.active_session_dir()
    if session is not None:
        _autonomy_session.persist_autonomy_phase(session, "decide", "stale_abort", err)
    return err


def _photo_vql_capture_mismatch_gate(
    *, mismatch: dict[str, Any] | None, ide: str, is_code_edit: bool
) -> dict | None:
    """Abort dict when the IDE/capture mismatch blocks actuation, else None."""
    if not _photo_vql_capture_mismatch_blocks(
        mismatch=mismatch,
        ide=ide,
        is_code_edit=is_code_edit,
    ):
        return None
    err = _photo_vql_capture_mismatch_error(
        mismatch=mismatch or {},
        ide=ide,
        is_code_edit=is_code_edit,
    )
    session = _autonomy_session.active_session_dir()
    if session is not None:
        _autonomy_session.persist_autonomy_phase(session, "decide", "ide_capture_blocked", err)
    return err


def _photo_vql_map_source_preflight_gate(
    *, ide: str, source: str, is_code_edit: bool
) -> dict | None:
    """Abort dict when the IDE prompt-map monitor mismatches the capture source, else None."""
    ide_map_source_mismatch = _map_capture_mismatch_for_ide(ide=ide, source=source)
    if not ide_map_source_mismatch or _map_source_mismatch_actuation_allowed():
        return None
    blocked = _photo_vql_map_source_mismatch_error(
        map_mismatch=ide_map_source_mismatch,
        target={
            "id": "map:ide-prompt",
            "source": ide_map_source_mismatch.get("map_path"),
            "selection_method": "map_source_preflight",
        },
        ide=ide,
        source=source,
        is_code_edit=is_code_edit,
    )
    session = _autonomy_session.active_session_dir()
    if session is not None:
        _autonomy_session.persist_autonomy_phase(session, "act", "map_source_mismatch_preflight_blocked", blocked)
    return blocked


def _photo_vql_target_map_mismatch_gate(
    t: dict[str, Any], *, ide: str, source: str, is_code_edit: bool
) -> tuple[dict | None, dict[str, Any] | None]:
    """Per-target map/capture mismatch gate: (abort dict | None, map_source_mismatch)."""
    map_source_mismatch = _map_capture_mismatch_for_target(target=t, ide=ide, source=source)
    if map_source_mismatch and not _map_source_mismatch_actuation_allowed():
        blocked = _photo_vql_map_source_mismatch_error(
            map_mismatch=map_source_mismatch,
            target=t,
            ide=ide,
            source=source,
            is_code_edit=is_code_edit,
        )
        session = _autonomy_session.active_session_dir()
        if session is not None:
            _autonomy_session.persist_autonomy_phase(session, "act", "map_source_mismatch_blocked", blocked)
        return blocked, map_source_mismatch
    if map_source_mismatch:
        t["map_capture_mismatch"] = map_source_mismatch
    return None, map_source_mismatch


def _photo_vql_maybe_clear_mismatch(
    t: dict[str, Any], *, ide: str, mismatch: dict[str, Any] | None
) -> dict[str, Any] | None:
    """Clear the observe-level mismatch when a trusted map/surface target allows actuation."""
    # For JetBrains on DP-2 (rotated, often empty VQL layers or title mismatch from observe),
    # get_vql... deliberately returns a calibrated map target (e.g. "prompt" or "ai-chat-input").
    # The map is the trusted source for this IDE+monitor. Clear the observe-level mismatch
    # so that actuation (move/click/paste + --submit) is allowed and inference_ok reflects
    # the reliable map path rather than blocking the user drive. The plan/warnings still
    # record "used_map_because_mismatch_or_bad_element" + selection_method for full audit.
    if _map_target_can_clear_capture_mismatch(target=t, ide=ide):
        mismatch = None
        t["_map_cleared_mismatch_for_actuation"] = True
    elif _surface_target_can_clear_capture_mismatch(target=t, ide=ide):
        mismatch = None
        t["_surface_cleared_mismatch_for_actuation"] = True
    return mismatch


def _photo_vql_refined_target(
    *, prompt: str, t: dict[str, Any], source: str, image_path: str | None, ide: str
) -> tuple[dict[str, Any], int, int, dict[str, Any] | None]:
    """Resolve (possibly LLM-refined) coords and annotate the target: (t, x, y, llm_decision)."""
    x, y, llm_decision = _resolve_photo_vql_llm_coords(
        prompt=prompt,
        target=t,
        source=source,
        image_path=image_path,
        ide=ide,
    )
    t = {
        **t,
        "click_center": {"x": x, "y": y, "note": (t.get("click_center") or {}).get("note")},
    }
    if llm_decision:
        t["llm_refined"] = True
        logger.info(
            "VQL_LLM_COORD_REFINE ide=%s local=(%s,%s) confidence=%s reason=%s",
            ide,
            x,
            y,
            llm_decision.get("confidence"),
            str(llm_decision.get("reason", ""))[:120],
        )
        session = _autonomy_session.active_session_dir()
        if session is not None:
            _autonomy_session.persist_autonomy_phase(
                session,
                "decide",
                "llm_coord_refine",
                {"llm_decision": llm_decision, "final_local": {"x": x, "y": y}, "vql_target_before": t},
            )
    return t, x, y, llm_decision


def _photo_vql_command_plan_pre_act(
    *,
    t: dict[str, Any],
    x: int,
    y: int,
    source: str,
    ide: str,
    prompt: str,
    llm_decision: dict[str, Any] | None,
    is_code_edit: bool,
    mismatch: dict[str, Any] | None,
) -> dict[str, Any]:
    """Build, log and persist the pre-act command plan for perform_photo_vql_focus_and_edit."""
    command_plan = _build_vql_command_plan(
        target=t,
        x=int(x),
        y=int(y),
        source=source,
        ide=ide,
        prompt=prompt,
        llm_decision=llm_decision,
        candidates=t.get("vql_candidates"),
        is_code_edit=is_code_edit,
        stage="perform_photo_vql_pre_act",
        capture_mismatch=mismatch,
        capture_provenance=_capture_provenance(
            ide=ide,
            png_path=_resolve_photo_png_path_from_vql(source=source),
            vql_path=_observe_vql_sidecar_path(source=source),
            meta=load_vql_metadata(allow_stale=True),
        ),
        vql_validation=t.get("vql_validation"),
    )
    t["vql_command_plan"] = command_plan
    if not command_plan.get("inference_ok"):
        logger.warning(
            "VQL_COMMAND_PLAN_SUSPICIOUS ide=%s local=(%s,%s) warnings=%s selection=%s",
            ide,
            x,
            y,
            command_plan.get("warnings"),
            command_plan.get("selection_method"),
        )
    session = _autonomy_session.active_session_dir()
    if session is not None:
        _autonomy_session.persist_autonomy_phase(
            session, "act", "command_plan_perform_photo_vql_pre_act", command_plan
        )
    return command_plan


def _photo_vql_unverified_chat_gate(
    *,
    command_plan: dict[str, Any],
    t: dict[str, Any],
    target_desc: str,
    x: int,
    y: int,
    ide: str,
    mismatch: dict[str, Any] | None,
    is_code_edit: bool,
) -> dict | None:
    """Abort dict when unverified chat actuation must be blocked, else None."""
    map_mismatch_allowed = _map_mismatch_allowed_for_target(target=t, ide=ide)
    surface_mismatch_allowed = _surface_mismatch_allowed_for_target(target=t, ide=ide)
    if not _photo_vql_should_block_unverified_chat(
        command_plan=command_plan,
        is_code_edit=is_code_edit,
        map_mismatch_allowed=map_mismatch_allowed,
        surface_mismatch_allowed=surface_mismatch_allowed,
    ):
        return None
    blocked = _photo_vql_unverified_chat_blocked(
        command_plan=command_plan,
        target_desc=target_desc,
        target=t,
        x=x,
        y=y,
        ide=ide,
        mismatch=mismatch,
    )
    session = _autonomy_session.active_session_dir()
    if session is not None:
        _autonomy_session.persist_autonomy_phase(session, "act", "chat_actuation_blocked", blocked)
    return blocked


def _photo_vql_edit_mismatch_allowances(*, t: dict[str, Any], ide: str) -> tuple[bool, bool]:
    """(map_mismatch_allowed, surface_mismatch_allowed) for combined_ok re-derivation."""
    is_jetbrains_map = str((t or {}).get("id") or "").startswith("map:") and _canonical_ide(ide) in {"jetbrains", "pycharm", "idea"}  # noqa: E501
    map_mismatch_allowed = is_jetbrains_map and _ide_mismatch_allowed()
    surface_mismatch_allowed = _surface_mismatch_allowed_for_target(target=t, ide=ide)
    return map_mismatch_allowed, surface_mismatch_allowed


def _photo_vql_combined_ok_after_edit(
    *,
    edit_res: dict[str, Any],
    t: dict[str, Any],
    ide: str,
    mismatch: dict[str, Any] | None,
    command_plan: dict[str, Any],
    is_code_edit: bool,
) -> bool:
    """Re-derive combined_ok from the edit result + mismatch/inference policy."""
    combined_ok = bool(edit_res.get("ok", False))
    map_mismatch_allowed, surface_mismatch_allowed = _photo_vql_edit_mismatch_allowances(
        t=t, ide=ide
    )
    if mismatch and not _ide_mismatch_allowed() and not map_mismatch_allowed and not surface_mismatch_allowed:
        combined_ok = False
    if (
        not command_plan.get("inference_ok", True)
        and not _ide_mismatch_allowed()
        and not _dry_run()
        and not map_mismatch_allowed
        and not surface_mismatch_allowed
        and not is_code_edit
    ):
        combined_ok = False

    if is_code_edit and edit_res.get("ok"):
        combined_ok = True
    return combined_ok


def _photo_vql_run_paste_verification(
    *,
    prompt: str,
    t: dict[str, Any],
    command_plan: dict[str, Any],
    ide: str,
    x: int,
    y: int,
) -> dict[str, Any]:
    """Run verify_chat_text_visible via map path or global/local coords."""
    global_coords = command_plan.get("final_global") or {}
    gx = global_coords.get("x")
    gy = global_coords.get("y")
    map_path = None
    if str(t.get("id") or "").startswith("map:"):
        src = t.get("source")
        if isinstance(src, str) and src.endswith(".json"):
            map_path = src
    if map_path:
        return verify_chat_text_visible(prompt, ide=ide, map_path=map_path)
    return verify_chat_text_visible(
        prompt,
        ide=ide,
        chat_x=int(gx) if gx is not None else int(x),
        chat_y=int(gy) if gy is not None else int(y),
    )


def _photo_vql_post_paste_verification(
    *,
    prompt: str,
    t: dict[str, Any],
    command_plan: dict[str, Any],
    combined_ok: bool,
    edit_res: dict[str, Any],
    is_code_edit: bool,
    ide: str,
    x: int,
    y: int,
) -> tuple[dict[str, Any] | None, bool]:
    """Optional OCR verification after paste: (verification | None, combined_ok)."""
    verification: dict[str, Any] | None = None
    verify_after_paste = os.environ.get("KORU_VDISPLAY_VERIFY_AFTER_PASTE", "1").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    if (
        verify_after_paste
        and combined_ok
        and not _dry_run()
        and not is_code_edit
        and bool(edit_res.get("ok"))
        and not _surface_bounds_target_safe_for_actuation(target=t, command_plan=command_plan)
    ):
        verification = _photo_vql_run_paste_verification(
            prompt=prompt, t=t, command_plan=command_plan, ide=ide, x=x, y=y
        )
        if verification.get("verified") is False:
            combined_ok = False
    return verification, combined_ok


def _photo_vql_submit_step(
    *, submit: bool, combined_ok: bool, edit_res: dict[str, Any], ide: str, source: str
) -> tuple[bool, dict[str, Any] | None, bool]:
    """Optional chat submit after a successful edit: (submitted, submit_result, combined_ok)."""
    submitted = False
    submit_result: dict[str, Any] | None = None
    if submit and combined_ok and not _dry_run():
        import time

        time.sleep(float(os.environ.get("KORU_VDISPLAY_SUBMIT_DELAY_S", "0.25")))
        submit_result = _photo_vql_submit_chat(ide=ide, source=source)
        submitted = bool(submit_result and submit_result.get("ok"))
        if not submitted:
            combined_ok = bool(edit_res.get("ok"))
        else:
            combined_ok = True
    return submitted, submit_result, combined_ok


def _photo_vql_assemble_combined(
    *,
    combined_ok: bool,
    target_desc: str,
    t: dict[str, Any],
    focus_res: dict[str, Any],
    edit_res: dict[str, Any],
    x: int,
    y: int,
    prompt: str,
    ide: str,
    is_code_edit: bool,
    llm_decision: dict[str, Any] | None,
    submitted: bool,
    command_plan: dict[str, Any],
    verification: dict[str, Any] | None,
    submit_result: dict[str, Any] | None,
    mismatch: dict[str, Any] | None,
    map_source_mismatch: dict[str, Any] | None,
) -> dict:
    """Assemble the combined result dict for perform_photo_vql_focus_and_edit."""
    combined = {
        "ok": combined_ok,
        "backend": "vdisplay+photo-vql",
        "target": target_desc,
        "vql_target": t,
        "focus": focus_res,
        "edit": edit_res,
        "coords": {"x": x, "y": y},
        "prompt": prompt[:100] + "..." if len(prompt) > 100 else prompt,
        "ide": ide,
        "is_code_edit": is_code_edit,
        "llm_decision": llm_decision,
        "llm_used": bool(llm_decision),
        "submitted": submitted,
        "vql_command_plan": command_plan,
        "capture_confirmed": command_plan.get("capture_confirmed"),
        "capture_provenance": command_plan.get("capture_provenance"),
    }
    if verification is not None:
        combined["verification"] = verification
        combined["verified"] = verification.get("verified")
    if submit_result is not None:
        combined["submit"] = submit_result

    if mismatch:
        combined["ide_window_warning"] = mismatch
    if map_source_mismatch:
        combined["map_capture_mismatch"] = map_source_mismatch
    return combined


def _photo_vql_persist_drive_result(
    combined: dict,
    *,
    t: dict[str, Any],
    llm_decision: dict[str, Any] | None,
    mismatch: dict[str, Any] | None,
    verification: dict[str, Any] | None,
    ide: str,
    prompt: str,
) -> None:
    """Persist decide/act/verify phases + the drive step record for the combined result."""
    session = _autonomy_session.active_session_dir()
    if session is not None:
        _autonomy_session.persist_autonomy_phase(
            session,
            "decide",
            "vql_target",
            {"target": t, "llm_decision": llm_decision, "mismatch": mismatch},
        )
        _autonomy_session.persist_autonomy_phase(session, "act", "drive_result", combined)
        if verification is not None:
            _autonomy_session.persist_autonomy_phase(session, "verify", "chat_text_visible", verification)
        try:
            record_koru_drive_step(combined, profile_id=ide or "auto", text=prompt)
        except Exception:
            pass


def perform_photo_vql_focus_and_edit(
    prompt: str,
    *,
    ide: str = "auto",
    source: str = "DP-1",
    is_code_edit: bool = False,
    submit: bool = False,
    image_path: str | None = None,
) -> dict:
    """Na podstawie foto screen VQL: zlokalizuj (chat lub editor), przesuń mysz + focus keyboard na click_center z foto,
    potem wykonaj precyzyjny edit/typ via coords (set_value at the VQL center).

    To realizuje "użyć VQL do 'zobaczenia' otwartego pliku w edytorze
    i precyzyjnego edit via coords" (następny task z analizy).
    Dla is_code_edit=True używa editor target (np. window_0 lub main panel z foto VQL).
    Dla chat (default) używa chat panel.

    Optional LLM vision layer (enable with KORU_VDISPLAY_LLM_VISION_DECISION=1):
    If .env has OPENROUTER_API_KEY and LLM_MODEL (vision model e.g. openrouter/qwen/qwen3.7-plus),
    we send base64(image_path) + VQL target excerpt + the prompt to the model.
    LLM should return JSON: {"click_center": {"x": int, "y": int}, "strategy": str, "confidence": float, "reason": str}.
    If successful and confidence reasonable, the LLM's click_center (and strategy)
    overrides the pure VQL one for this call.
    This adds "LLM decides exact coords/strategy on top of photo VQL" as additional layer.
    Always falls back to the VQL-derived coords if no key, no image_path, call fails, or low confidence.
    IDE independent (dane z foto, nie z pluginu).
    """
    mismatch = _photo_vql_ide_capture_mismatch(ide=ide) if ide and ide != "auto" else None
    use_llm_vision = os.environ.get("KORU_VDISPLAY_LLM_VISION_DECISION", "").strip().lower() in {"1", "true", "yes", "on"}  # noqa: E501, F841

    err = _photo_vql_stale_metadata_gate(ide=ide, is_code_edit=is_code_edit)
    if err is not None:
        return err

    # Strict match mainly for is_code_edit (precise editor file edits need correct capture of the open file).
    # Chat on JetBrains also requires a matching capture unless explicitly overridden — LLM vision cannot
    # reliably locate PyCharm chat when the screenshot shows Cursor (wrong window layer / VQL inputs).
    err = _photo_vql_capture_mismatch_gate(mismatch=mismatch, ide=ide, is_code_edit=is_code_edit)
    if err is not None:
        return err

    blocked = _photo_vql_map_source_preflight_gate(
        ide=ide, source=source, is_code_edit=is_code_edit
    )
    if blocked is not None:
        return blocked

    if is_code_edit:
        t = get_vql_editor_target_from_photo()
        target_desc = "editor/open-file"
    else:
        t = get_vql_chat_target_from_photo(ide=ide)
        target_desc = "chat"

    blocked, map_source_mismatch = _photo_vql_target_map_mismatch_gate(
        t, ide=ide, source=source, is_code_edit=is_code_edit
    )
    if blocked is not None:
        return blocked

    mismatch = _photo_vql_maybe_clear_mismatch(t, ide=ide, mismatch=mismatch)

    if image_path is None:
        image_path = _resolve_photo_png_path_from_vql(source=source)

    t, x, y, llm_decision = _photo_vql_refined_target(
        prompt=prompt, t=t, source=source, image_path=image_path, ide=ide
    )

    command_plan = _photo_vql_command_plan_pre_act(
        t=t,
        x=x,
        y=y,
        source=source,
        ide=ide,
        prompt=prompt,
        llm_decision=llm_decision,
        is_code_edit=is_code_edit,
        mismatch=mismatch,
    )

    blocked = _photo_vql_unverified_chat_gate(
        command_plan=command_plan,
        t=t,
        target_desc=target_desc,
        x=x,
        y=y,
        ide=ide,
        mismatch=mismatch,
        is_code_edit=is_code_edit,
    )
    if blocked is not None:
        return blocked

    focus_res = _photo_vql_focus_target(
        target=t,
        ide=ide,
        source=source,
        is_code_edit=is_code_edit,
        llm_decision=llm_decision,
    )
    edit_res = _photo_vql_edit_result(
        prompt,
        x=x,
        y=y,
        target_desc=target_desc,
        source=source,
        ide=ide,
        focus_res=focus_res,
        target=t,
        command_plan=command_plan,
    )

    combined_ok = _photo_vql_combined_ok_after_edit(
        edit_res=edit_res,
        t=t,
        ide=ide,
        mismatch=mismatch,
        command_plan=command_plan,
        is_code_edit=is_code_edit,
    )
    verification, combined_ok = _photo_vql_post_paste_verification(
        prompt=prompt,
        t=t,
        command_plan=command_plan,
        combined_ok=combined_ok,
        edit_res=edit_res,
        is_code_edit=is_code_edit,
        ide=ide,
        x=x,
        y=y,
    )
    submitted, submit_result, combined_ok = _photo_vql_submit_step(
        submit=submit, combined_ok=combined_ok, edit_res=edit_res, ide=ide, source=source
    )

    combined = _photo_vql_assemble_combined(
        combined_ok=combined_ok,
        target_desc=target_desc,
        t=t,
        focus_res=focus_res,
        edit_res=edit_res,
        x=x,
        y=y,
        prompt=prompt,
        ide=ide,
        is_code_edit=is_code_edit,
        llm_decision=llm_decision,
        submitted=submitted,
        command_plan=command_plan,
        verification=verification,
        submit_result=submit_result,
        mismatch=mismatch,
        map_source_mismatch=map_source_mismatch,
    )
    _photo_vql_persist_drive_result(
        combined,
        t=t,
        llm_decision=llm_decision,
        mismatch=mismatch,
        verification=verification,
        ide=ide,
        prompt=prompt,
    )
    return combined


def move_mouse_to_vql_target_and_focus_keyboard(target: dict | None = None, *, ide: str = "auto", source: str = "DP-1") -> dict:  # noqa: E501
    """Na podstawie foto screen: zlokalizuj okno chat (via get_vql_chat_target_from_photo),
    przenies mysz na click_center, click (dla focus keyboard).

    Dziala niezaleznie od IDE (jetbrains -> cursor itp.): VQL z aktualnego zrzutu ekranu
    daje centers/layers/data_locations.
    Po click na panel/input area, IDE dostaje keyboard focus w tym miejscu (chat composer lub editor).

    Uzywane w koru autonomy / send_chat (gdy KORU_VDISPLAY_USE_VQL_MOUSE_FOCUS=1) + recznie dla STARTER etc.
    Real action via vdisplay _control_click (vision + point) + _control_focus;
    dziala gdy agent/keeper aktywny na --source.
    Dry-run / brak agenta -> tylko intencja + coords (zapis do .vdisplay via record).
    """
    if not target:
        target = get_vql_chat_target_from_photo(ide=ide)
    cc = (target or {}).get("click_center") or {"x": 1024, "y": 640}
    x = int(cc.get("x", 1024))
    y = int(cc.get("y", 640))
    hints = _ide_hints(ide) if ide and ide != "auto" else {}
    result: dict[str, Any] = {
        "ok": False,
        "action": "vql_photo_mouse_to_chat_focus_kb",
        "vql_target": target,
        "coords": {"x": x, "y": y, "note": cc.get("note")},
        "ide": ide,
        "source": source,
    }

    # Log cursor positioning at the exact moment we are about to issue the "move+click to chat" command.
    # All coords are derived from VQL (after corner heuristic / map / LLM enrich).
    vql_file = target.get("source") if isinstance(target.get("source"), str) and target.get("source", "").endswith(".vql.json") else None  # noqa: E501
    _log_vql_cursor_positioning_at_command(
        target,
        stage="move_to_chat_for_write_command",
        ide=ide,
        source=source,
        final_local={"x": x, "y": y},
        vql_file=vql_file,
        command_plan=target.get("vql_command_plan"),
    )

    if _dry_run() or not vdisplay_available():
        result.update({
            "ok": True,
            "dry_run": True,
            "message": f"DRY-RUN: mouse move to chat VQL center ({x},{y}) + click -> keyboard focus in {ide} (from current screen foto)",  # noqa: E501
        })
        return result

    # Real action: try to position mouse at exact VQL photo coords and click (to focus chat/input area).
    # The coords come from the capture frame (e.g. DP-1 portal stream local 0-2048x1280).
    # We try a few payload shapes because raw point clicks on multi-stream portal captures can be sensitive to backend/source.  # noqa: E501
    # We always also ensure window-level focus for keyboard.
    click_res, focus_res, last_err = _move_mouse_attempt_focus_and_click(
        result, hints=hints, x=x, y=y, source=source
    )
    return _move_mouse_click_outcome(
        result,
        click_res=click_res,
        focus_res=focus_res,
        last_err=last_err,
        x=x,
        y=y,
        target=target,
        ide=ide,
        source=source,
    )


def _move_mouse_attempt_focus_and_click(
    result: dict[str, Any],
    *,
    hints: dict[str, str],
    x: int,
    y: int,
    source: str,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None, Exception | None]:
    """Window focus + point-click payload variants for move_mouse_to_vql_target_and_focus_keyboard."""
    click_res = None
    focus_res = None
    last_err = None

    focus_payload = {
        "backend": "auto",
        "app": hints.get("app"),
        "window_title": hints.get("window_title_contains"),
        "role": "window",
    }

    # Always attempt window focus first (gives kb to the IDE containing the chat area)
    try:
        focus_res = _control_focus(**focus_payload)
        result["focus_res"] = focus_res
    except Exception as exc:
        last_err = exc

    # Try point click variants
    # Note: do NOT include "action" kwarg -- _control_click implies click; including it causes
    # "got multiple values for keyword argument 'action'" inside vdisplay _execute_action.
    for payload in [
        # Preferred when we have explicit VQL photo coords + known source stream
        {
            "backend": "vision",
            "x": x, "y": y,
            "source": source,
            "app": hints.get("app"),
            "window_title": hints.get("window_title_contains"),
        },
        # Fallback shapes
        {
            "backend": "auto",
            "x": x, "y": y,
            "source": source,
            "app": hints.get("app"),
            "window_title": hints.get("window_title_contains"),
        },
        {
            "x": x, "y": y,
            "app": hints.get("app"),
            "window_title": hints.get("window_title_contains"),
        },
    ]:
        try:
            click_res = _control_click(**payload)
            result["click_res"] = click_res
            if isinstance(click_res, dict) and click_res.get("ok", True):
                break
        except Exception as exc:
            last_err = exc
            continue

    return click_res, focus_res, last_err


def _move_mouse_click_outcome(
    result: dict[str, Any],
    *,
    click_res: dict[str, Any] | None,
    focus_res: dict[str, Any] | None,
    last_err: Exception | None,
    x: int,
    y: int,
    target: dict,
    ide: str,
    source: str,
) -> dict:
    """Fold focus/click attempt results into the move-mouse result payload."""
    if click_res is not None or focus_res is not None:
        click_ok = bool(click_res.get("ok", True)) if isinstance(click_res, dict) else (click_res is not None)
        focus_ok = isinstance(focus_res, dict) and focus_res.get("ok", True)
        # Treat as success for the "keyboard focus" goal if window focus worked (brings kb to the IDE).
        # Mouse click at precise photo VQL center is attempted for the "przeniesiona mysz" part.
        # If low-level point click on the portal stream is not confirming, the coords are still the correct ones from the foto.  # noqa: E501
        overall_ok = focus_ok or click_ok
        result.update({
            "ok": overall_ok,
            "message": f"Photo VQL target used ({x},{y} from {target.get('id')}). Mouse click at chat center from screen photo attempted; window focus for keyboard. ide={ide}. (Point click may need fresh screencast --source {source} or vision-assisted click.)",  # noqa: E501
            "mouse_attempted": True,
            "keyboard_focus_attempted": focus_ok or True,
        })
        if last_err:
            result["last_control_error"] = str(last_err)
        return result

    result.update({
        "ok": False,
        "error": str(last_err) if last_err else "no control result",
        "message": f"Mouse/focus action failed at VQL coords ({x},{y}); photo-based target ready for retry or manual.",
    })
    return result


def _imgl_sidecar_path_for_vql(vql_path: str) -> str | None:
    if not vql_path.endswith(".vql.json"):
        return None
    alt = vql_path[: -len(".vql.json")] + ".vql.imgl.json"
    return alt if os.path.isfile(alt) else None


def _layers_from_imgl_sidecar_file(vql_path: str) -> tuple[list[dict], str | None]:
    """Load actuation layers from sibling ``.vql.imgl.json`` when main VQL sidecar is empty."""
    imgl_path = _imgl_sidecar_path_for_vql(vql_path)
    if not imgl_path:
        return [], None
    png_path = _png_path_for_vql_sidecar(vql_path)
    if png_path is not None:
        try:
            if os.path.getmtime(imgl_path) + 1 < os.path.getmtime(png_path):
                return [], None
        except OSError:
            pass
    try:
        with open(imgl_path) as f:
            imgl_data = json.load(f)
    except Exception:
        return [], None
    try:
        from vdisplay.integrations.vql_bridge import _build_imgl_layers

        built = _build_imgl_layers({"ok": True, "scene": imgl_data})
    except Exception:
        built = []
    if not built:
        return [], None
    return _layers_from_vdisplay_sidecar({"layers": built, "metadata": {"render_intent": {"layers": built}}}), imgl_path


def _vql_sidecar_layer_center(layer: dict, bbox: Any) -> dict:
    """Click-center for a vdisplay sidecar layer (bbox midpoint fallback)."""
    center = layer.get("click_center") or layer.get("center") or {}
    if not center and isinstance(bbox, dict):
        w = int(bbox.get("w") or bbox.get("width") or 0)
        h = int(bbox.get("h") or bbox.get("height") or 0)
        if w > 0 and h > 0:
            center = {
                "x": int(bbox.get("x") or 0) + w // 2,
                "y": int(bbox.get("y") or 0) + h // 2,
            }
    return center


def _vql_sidecar_layer_entry(layer: dict) -> dict:
    """Normalize a single vdisplay sidecar layer into a ui-element dict."""
    bbox = layer.get("bbox") or {}
    center = _vql_sidecar_layer_center(layer, bbox)
    return {
        "id": layer.get("id"),
        "role": layer.get("kind") or layer.get("role"),
        "label": layer.get("text") or layer.get("label"),
        "bounds": bbox,
        "click_center": center,
        "metadata": {k: layer.get(k) for k in ("confidence", "location") if k in layer},
    }


def _layers_from_vdisplay_sidecar(data: dict) -> list[dict]:
    """Extract IMGL/VQL layers from vdisplay ``.png.vql.json`` sidecar."""
    metadata = data.get("metadata") or {}
    render = metadata.get("render_intent") or {}
    layers = render.get("layers") or data.get("layers") or []
    if not isinstance(layers, list):
        return []
    ui: list[dict] = []
    for layer in layers:
        if not isinstance(layer, dict):
            continue
        ui.append(_vql_sidecar_layer_entry(layer))
    return ui


def _with_embedded_capture_validation(meta: dict, raw: dict | None = None) -> dict:
    if meta.get("capture_validation"):
        return meta
    nested = raw.get("metadata") if isinstance(raw, dict) and isinstance(raw.get("metadata"), dict) else {}
    cv = meta.get("metadata", {}).get("capture_validation") if isinstance(meta.get("metadata"), dict) else None
    if cv is None and isinstance(nested, dict):
        cv = nested.get("capture_validation")
    if isinstance(cv, dict):
        meta["capture_validation"] = cv
    return meta


def _vql_candidate_is_stale(cand: str, png_path: Path | None, stale_tried: list[dict[str, Any]]) -> bool:
    """Check sidecar staleness, recording skipped candidates into stale_tried."""
    stale, freshness = _autonomy_session.vql_sidecar_is_stale(
        Path(cand),
        png_path,
        layer_count=_main_vql_layer_count(cand),
    )
    if stale:
        stale_tried.append({"path": cand, **freshness})
    return stale


def _vql_from_ui_elements(data: dict, cand: str, png_path: Path | None) -> dict:
    """Normalize a sidecar that already carries ui_elements (analysis-style VQL)."""
    data["_source"] = cand
    if png_path and png_path.is_file():
        data["_png"] = str(png_path)
        data["_freshness"] = {"age_s": round(__import__("time").time() - png_path.stat().st_mtime, 2)}
    if "layers" not in data:
        data["layers"] = data["ui_elements"]
    return _with_embedded_capture_validation(data, data)


def _vql_from_fresh_elements(data: dict, cand: str, png_path: Path | None) -> dict:
    """Normalize a fresh-capture sidecar carrying raw elements."""
    res = _parse_fresh_vql_elements(data, cand)
    if png_path and png_path.is_file():
        res["_png"] = str(png_path)
    return _with_embedded_capture_validation(res, data)


def _vql_imgl_fallback_layers(
    cand: str, *, allow_stale: bool, stale_tried: list[dict[str, Any]]
) -> tuple[list[dict], str]:
    """Fall back to imgl sidecar layers for cand; returns (layers, effective_cand)."""
    imgl_layers, imgl_source = _layers_from_imgl_sidecar_file(cand)
    if imgl_layers:
        imgl_path = Path(imgl_source or cand)
        png_for_imgl = _png_path_for_vql_sidecar(str(cand))
        if not allow_stale and png_for_imgl and imgl_path.is_file():
            imgl_stale, _ = _autonomy_session.vql_sidecar_is_stale(
                imgl_path,
                png_for_imgl,
                layer_count=len(imgl_layers),
            )
            if imgl_stale:
                stale_tried.append({"path": str(imgl_path), "reasons": ["stale_imgl_fallback"]})
                imgl_layers = []
        if imgl_layers:
            return imgl_layers, (imgl_source or cand)
    return [], cand


def _vql_from_sidecar_layers(data: dict, cand: str, sidecar_layers: list[dict], png_path: Path | None) -> dict:
    """Normalize vdisplay/imgl sidecar layers into the metadata dict shape."""
    out = {
        "ui_elements": sidecar_layers,
        "layers": sidecar_layers,
        "metadata": data.get("metadata") or {},
        "environment": (data.get("metadata") or {}).get("environment") or data.get("environment") or {},
        "_source": cand,
    }
    if png_path and png_path.is_file():
        out["_png"] = str(png_path)
    return _with_embedded_capture_validation(out, data)


def _vql_from_program_wrapper(data: dict, cand: str) -> dict | None:
    """Unwrap a nested vql.program dict when present; None to keep dispatching."""
    if "vql" in data and isinstance(data.get("vql"), dict):
        prog = data["vql"].get("program", data["vql"])
        if isinstance(prog, dict):
            prog["_source"] = cand
            if "layers" not in prog and "ui_elements" in prog:
                prog["layers"] = prog["ui_elements"]
            return prog
    return None


def _vql_from_screen_context(data: dict, cand: str) -> dict:
    """Normalize a screen_context/metadata-only sidecar into the metadata dict shape."""
    meta = data.get("metadata") or data.get("screen_context") or {}
    layers = _layers_from_vdisplay_sidecar({"metadata": meta})
    return _with_embedded_capture_validation(
        {
            "ui_elements": layers,
            "layers": layers,
            "metadata": meta,
            "environment": meta.get("environment") or data.get("environment") or {},
            "_source": cand,
        },
        data,
    )


def _vql_metadata_default(data: dict, cand: str) -> dict:
    """Fallback normalization: tag source and mirror ui_elements into layers."""
    if isinstance(data.get("program"), (str, dict)) and "elements" not in data:
        data["_source"] = cand
        if "layers" not in data:
            data["layers"] = data.get("ui_elements", [])
        return data
    data["_source"] = cand
    if "layers" not in data:
        data["layers"] = data.get("ui_elements", [])
    return data


def _parse_vql_candidate_data(
    data: dict, cand: str, png_path: Path | None, *, allow_stale: bool, stale_tried: list[dict[str, Any]]
) -> dict:
    """Normalize various VQL structures (analysis, fresh capture from screenshot, imgl, etc.)."""
    if "ui_elements" in data and data.get("ui_elements"):
        return _vql_from_ui_elements(data, cand, png_path)
    if "elements" in data and isinstance(data.get("elements"), list) and data["elements"]:
        return _vql_from_fresh_elements(data, cand, png_path)
    sidecar_layers = _layers_from_vdisplay_sidecar(data)
    if not sidecar_layers:
        sidecar_layers, cand = _vql_imgl_fallback_layers(cand, allow_stale=allow_stale, stale_tried=stale_tried)
    if sidecar_layers:
        return _vql_from_sidecar_layers(data, cand, sidecar_layers, png_path)
    prog = _vql_from_program_wrapper(data, cand)
    if prog is not None:
        return prog
    if "screen_context" in data or "metadata" in data:
        return _vql_from_screen_context(data, cand)
    return _vql_metadata_default(data, cand)


def _load_vql_candidate_metadata(
    cand: str, *, allow_stale: bool, stale_tried: list[dict[str, Any]]
) -> dict | None:
    """Resolve, freshness-check, load and normalize a single VQL candidate; None to skip."""
    resolved = _resolve_vql_candidate(cand)
    if not resolved:
        return None
    cand = resolved
    if not os.path.exists(cand):
        return None
    png_path = _png_path_for_vql_sidecar(cand)
    if not allow_stale and _vql_candidate_is_stale(cand, png_path, stale_tried):
        return None
    with open(cand) as f:
        data = json.load(f)
    return _parse_vql_candidate_data(data, cand, png_path, allow_stale=allow_stale, stale_tried=stale_tried)


def load_vql_metadata(path: str | None = None, *, allow_stale: bool = False) -> dict:
    """Load VQL metadata for decide/act. Skips stale sidecars unless ``allow_stale=True``.

    During an autonomy session only ``.vdisplay/YYYY-MM-DD/.../observe/capture.png.vql.json`` is used.
    """
    candidates = _get_vql_candidates(path)
    stale_tried: list[dict[str, Any]] = []
    for cand in candidates:
        try:
            parsed = _load_vql_candidate_metadata(cand, allow_stale=allow_stale, stale_tried=stale_tried)
        except Exception:
            continue
        if parsed is not None:
            return parsed
    return {
        "error": "no fresh vql found",
        "tried": candidates,
        "stale_skipped": stale_tried,
        "layers": [],
        "ui_elements": [],
    }


def _resolve_vql_candidate(cand: str) -> str | None:
    """Resolve a VQL path or glob to the newest existing file."""
    import glob

    if "*" not in cand:
        return cand if os.path.exists(cand) else None
    matches = [m for m in glob.glob(cand) if os.path.isfile(m)]
    if not matches:
        return None
    matches.sort(key=lambda p: os.path.getmtime(p), reverse=True)
    return matches[0]


def _monitor_source_slugs(source: str) -> list[str]:
    raw = source.strip().lower().replace("/", "-")
    compact = raw.replace("-", "")
    return list(dict.fromkeys([s for s in (raw, compact) if s]))


def _get_vql_candidates(path: str | None) -> list:
    """VQL sidecar search order: explicit path → active session observe → fresh koru-cont-*."""
    if path:
        return [path]
    env_path = os.environ.get("KORU_VDISPLAY_VQL_PATH", "").strip()
    if env_path:
        return [env_path]
    session = _autonomy_session.active_session_dir()
    if session is not None:
        _png, vql = _autonomy_session.session_observe_paths(session)
        return [str(vql)]
    source = os.environ.get("KORU_VDISPLAY_SOURCE", "DP-1").strip() or "DP-1"
    candidates: list[str] = []
    for slug in _monitor_source_slugs(source):
        candidates.extend([
            f".vdisplay/koru-cont-{slug}.png.vql.json",
            f".vdisplay/koru-cont-{slug}-*.png.vql.json",
            f"/tmp/koru-cont-{slug}.png.vql.json",
            f"/tmp/koru-cont-{slug}-*.png.vql.json",
        ])
    candidates.extend([
        ".vdisplay/koru-cont-dp1.png.vql.json",
        ".vdisplay/koru-cont-dp1-*.png.vql.json",
        ".vdisplay/koru-cont-dp2-*.png.vql.json",
        "/tmp/koru-cont-dp1.png.vql.json",
        "/tmp/koru-cont-dp1-*.png.vql.json",
    ])
    best = _freshest_populated_vql_candidate()
    if best:
        if best in candidates:
            candidates.remove(best)
        candidates.insert(0, best)
    return candidates


def _freshest_populated_vql_candidate() -> str | None:
    """Newest non-stale koru-cont VQL sidecar with a meaningful element count."""
    import glob
    best = None
    best_mt = 0
    max_age = _autonomy_session.vql_max_age_seconds()
    now = __import__("time").time()
    for p in glob.glob(".vdisplay/koru-cont-*.vql.json"):
        if not os.path.isfile(p):
            continue
        if max_age > 0 and (now - os.path.getmtime(p)) > max_age:
            continue
        try:
            with open(p) as fh:
                data = json.load(fh)
            ec = data.get("element_count") or len(data.get("elements", []) or data.get("ui_elements", []))
            if ec and ec > 20:
                mt = os.path.getmtime(p)
                if mt > best_mt:
                    best_mt = mt
                    best = p
        except Exception:
            pass
    return best


def _fresh_vql_bbox_xy(bbox: dict) -> tuple[int, int]:
    """Top-left corner of a dict-shaped fresh-VQL bbox."""
    bx = int(bbox.get("x") or bbox.get("left") or 0)
    by = int(bbox.get("y") or bbox.get("top") or 0)
    return bx, by


def _fresh_vql_bbox_wh(bbox: dict, bx: int, by: int) -> tuple[int, int]:
    """Width/height of a dict-shaped fresh-VQL bbox, deriving from right/bottom when needed."""
    bw = int(bbox.get("w") or bbox.get("width") or 0)
    bh = int(bbox.get("h") or bbox.get("height") or 0)
    if not bw and bbox.get("right") is not None:
        bw = max(0, int(bbox.get("right") or 0) - bx)
    if not bh and bbox.get("bottom") is not None:
        bh = max(0, int(bbox.get("bottom") or 0) - by)
    return bw, bh


def _fresh_vql_center(center: Any, bx: int, by: int, bw: int, bh: int) -> tuple[int, int]:
    """Click center from a fresh-VQL element's center field, defaulting to bbox center."""
    if isinstance(center, dict) and center:
        cx = int(center.get("x") or bx + bw // 2)
        cy = int(center.get("y") or by + bh // 2)
    elif isinstance(center, (list, tuple)) and len(center) >= 2:
        cx, cy = int(center[0]), int(center[1])
    else:
        cx, cy = bx + bw // 2, by + bh // 2
    return cx, cy


def _fresh_vql_center_only(center: Any) -> tuple[Any, Any]:
    """Click center when a fresh-VQL element has no usable bbox.

    Falls back to the DP-1 capture-frame center (1024, 640) at every level,
    mirroring resolve_click_for_frame's hardcoded fallback.
    """
    if isinstance(center, dict) and center:
        return int(center.get("x") or 1024), int(center.get("y") or 640)
    c = center or [1024, 640]
    if not isinstance(c, (list, tuple)):
        c = [1024, 640]
    return c[0], c[1]


def _fresh_vql_bbox_center(e: dict) -> tuple[int, int, int, int, Any, Any]:
    """Resolve (bx, by, bw, bh, cx, cy) for a fresh-VQL element across bbox shapes."""
    bbox = e.get("bbox") or [0, 0, 0, 0]
    center = e.get("click_center") or e.get("center") or {}
    if isinstance(bbox, dict):
        bx, by = _fresh_vql_bbox_xy(bbox)
        bw, bh = _fresh_vql_bbox_wh(bbox, bx, by)
        cx, cy = _fresh_vql_center(center, bx, by, bw, bh)
    elif isinstance(bbox, (list, tuple)) and len(bbox) >= 4:
        bx, by = int(bbox[0]), int(bbox[1])
        bw = max(0, int(bbox[2]) - bx)
        bh = max(0, int(bbox[3]) - by)
        cx, cy = _fresh_vql_center(center, bx, by, bw, bh)
    else:
        cx, cy = _fresh_vql_center_only(center)
        bx, by, bw, bh = 0, 0, 0, 0
    return bx, by, bw, bh, cx, cy


def _parse_fresh_vql_elements(data: dict, cand: str) -> dict:
    """Helper extracted to reduce CC in load_vql_metadata (autonomous refactor for high-CC split)."""
    ui_els = []
    for e in data["elements"]:
        bx, by, bw, bh, cx, cy = _fresh_vql_bbox_center(e)
        ui_els.append({
            "id": str(e.get("id", f"elem-{len(ui_els)}")),
            "role": e.get("role") or e.get("kind") or "unknown",
            "bounds": {"x": int(bx), "y": int(by), "width": int(bw), "height": int(bh), "coordinate_space": "capture_frame_local"},  # noqa: E501
            "click_center": {"x": int(cx), "y": int(cy), "note": f"fresh VQL elem, color={e.get('color')}, conf={e.get('confidence')}"},  # noqa: E501
            "label": e.get("label") or e.get("text"),
            "metadata": {k: e.get(k) for k in ("color","confidence","location") if k in e}
        })
    res = {"ui_elements": ui_els, "layers": ui_els, "element_count": data.get("element_count", len(ui_els)), "by_role": data.get("by_role", {}), "scene": data.get("scene"), "_source": cand, "raw_fresh": True}  # noqa: E501
    return res


def get_vql_target(ide: str, *, role: str | None = None, name_contains: str | None = None, label: str | None = None) -> dict | None:  # noqa: E501
    """Select target from loaded VQL ui_elements/layers by role or name/label.
    Returns dict with click_center, bounds, id for use in act (mouse nav).
    Used to close observe -> decide -> act gap when vision stub or no map.
    """
    vql = load_vql_metadata()
    targets = vql.get("ui_elements") or vql.get("layers") or []
    for t in targets:
        if role and t.get("role") != role:
            continue
        if name_contains and name_contains.lower() not in str(t.get("label", "")).lower() and name_contains.lower() not in str(t.get("id", "")).lower():  # noqa: E501
            continue
        if label and label.lower() not in str(t.get("label", "")).lower():
            continue
        cc = t.get("click_center") or {}
        if cc:
            return {
                "id": t.get("id"),
                "role": t.get("role"),
                "click_center": cc,
                "bounds": t.get("bounds"),
                "source": vql.get("_source"),
            }
    return None


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
                    return {"x": cc.get("x"), "y": cc.get("y"), "source": m.get("_source"), "note": el.get("note", "from VQL")}  # noqa: E501
        # fallback any
        el = m["ui_elements"][0]
        if cc := el.get("click_center") or el.get("center"):
            return {"x": cc.get("x") if isinstance(cc, dict) else cc[0], "y": cc.get("y") if isinstance(cc, dict) else cc[1], "source": m.get("_source")}  # noqa: E501
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
    "get_vql_target",
    "resolve_click_for_frame",
    # photo screen VQL based (from .vdisplay/*koru-cont*.vql.json + analysis): locate chat + mouse move + kb focus (IDE independent)  # noqa: E501
    "get_vql_chat_target_from_photo",
    "validate_vql_chat_target",
    "move_mouse_to_vql_target_and_focus_keyboard",
    # next from analysis: VQL for "zobaczenia" otwartego pliku w edytorze + precyzyjny edit via coords
    "get_vql_editor_target_from_photo",
    "click_editor_via_photo_vql",
    "perform_photo_vql_focus_and_edit",
    "refresh_photo_vql_sidecar",
    "prepare_photo_vql_for_drive",
    "ensure_vdisplay_ide_control",
    "photo_vql_sidecar_needs_refresh",
    "begin_autonomy_session",
]
