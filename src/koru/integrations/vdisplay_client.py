"""vdisplay semantic control fallback for koru autonomous / coru drive.

When simplified control paths fail (plugin socket, blind wtype/ydotool, coordinate
injectors), koru can delegate to vdisplay's control plane for full semantic
automation: AT-SPI / Playwright / terminal / X11 / vision routing with verify.
"""

from __future__ import annotations

import base64
import datetime
import json
import logging
import os
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

from koru.integrations.autonomy_session import begin_autonomy_session
from koru.integrations import autonomy_session as _autonomy_session

# Optional: LLM vision decision layer on top of photo VQL (enable via env + .env OpenRouter key)
try:
    from koru.autonomy_strategy.openrouter import call_openrouter_vision
except Exception:
    call_openrouter_vision = None

_VDISPLAY_DIRECT = False
_VDISPLAY_IMPORT_ERROR: str | None = None
_vdisplay_control = None

def _load_vdisplay_control():
    """Lazy load to avoid top-level crashes from vdisplay submodules (e.g. missing dataclass in some versions) and make autonomy robust."""
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

    from koru.deps_autorepair import ensure_vision_ocr

    if not ensure_vision_ocr(label="koru verify"):
        return {
            "ok": False,
            "verified": False,
            "mode": "ocr_contains",
            "error": "OCR verify deps missing (tesseract, Pillow, pytesseract)",
        }

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

    png, capture_meta, bounds = _capture_for_verify(chat_x, chat_y, map_path, ide)
    if not png:
        return {"ok": False, "verified": False, "mode": "ocr_contains", "error": "screenshot capture failed", "bounds": bounds.to_dict() if bounds else None, "ide": ide}

    return _ocr_verify(png, capture_meta, bounds, expected, ide, chat_x, chat_y)


def _capture_for_verify(chat_x, chat_y, map_path, ide):
    from vdisplay.control.models import ControlBounds, ControlNode, ControlRole
    from vdisplay.control.screenshot_verify import capture_control_screenshot
    from vdisplay.control.gui_map import load_gui_map
    from vdisplay.input.coords import global_pointer_coords

    bounds = None
    if chat_x is not None and chat_y is not None:
        bounds = ControlBounds(x=int(chat_x) - 360, y=int(chat_y) - 24, width=720, height=48)
        target = ControlNode(id="verify:chat-input", backend="vision", role=ControlRole.INPUT, name="chat-input", bounds=bounds)
        try:
            png, capture_meta = capture_control_screenshot(target=target)
            if not png:
                png, capture_meta = capture_control_screenshot(target=None)
            return png, capture_meta, bounds
        except Exception as exc:
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
        except Exception as exc:
            return None, None, None
    else:
        return None, None, None


def _ocr_verify(png, capture_meta, bounds, expected, ide, chat_x, chat_y):
    from vdisplay.control.vision_ocr import ocr_png
    from vdisplay.control.screenshot_verify import global_point_in_stream_bounds, stream_bounds_from_meta

    screenshot_path = str(capture_meta["path"]) if isinstance(capture_meta, dict) and capture_meta.get("path") else None

    stream_hint = None
    if isinstance(capture_meta, dict) and chat_x is not None and chat_y is not None:
        if not global_point_in_stream_bounds(int(chat_x), int(chat_y), capture_meta):
            stream = stream_bounds_from_meta(capture_meta)
            stream_hint = f"Chat focus ({chat_x},{chat_y}) is outside active ScreenCast stream {stream}. Restart screencast and pick All Screens or the monitor containing the IDE."

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


def _photo_vql_code_edit_enabled() -> bool:
    """When set, send_chat routes to perform_photo_vql_focus_and_edit(is_code_edit=True)."""
    return os.environ.get("KORU_VDISPLAY_PHOTO_VQL_CODE_EDIT", "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def _prefer_photo_vql_chat(*, ide: str = "auto") -> bool:
    """When set, send_chat uses photo VQL mouse+focus path before os_injector/ide_prompt."""
    raw = os.environ.get("KORU_VDISPLAY_PREFER_PHOTO_VQL", "").strip().lower()
    if raw in {"1", "true", "yes", "on"}:
        return True
    if raw in {"0", "false", "no", "off"}:
        return False
    if raw == "auto":
        canon = _canonical_ide(ide)
        if canon in {"jetbrains", "pycharm", "idea"}:
            return _capture_matches_requested_ide(ide)
        return True
    return False


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
    return os.environ.get("KORU_VDISPLAY_SOURCE", "DP-1").strip() or "DP-1"


_IDE_DEFAULT_SOURCE: dict[str, str] = {
    "cursor": "DP-1",
    "windsurf": "DP-1",
    "antigravity": "DP-1",
    "vscode": "DP-1",
    "jetbrains": "DP-1",
    "pycharm": "DP-1",
    "idea": "DP-1",
}

_IDE_PROCESS_PATTERNS: dict[str, tuple[str, ...]] = {
    "cursor": ("cursor",),
    "windsurf": ("windsurf",),
    "vscode": ("code", "vscode", "vscodium"),
    "antigravity": ("antigravity",),
    "jetbrains": ("pycharm", "idea", "webstorm", "goland", "clion", "rider", "jetbrains"),
    "pycharm": ("pycharm", "jetbrains"),
    "idea": ("idea", "intellij", "jetbrains"),
}


def _probe_ide_processes(ide: str) -> list[dict[str, Any]]:
    """Best-effort process list for target IDE (includes native Wayland not in X11 window list)."""
    import subprocess

    patterns = _IDE_PROCESS_PATTERNS.get(_canonical_ide(ide), (_canonical_ide(ide),))
    found: list[dict[str, Any]] = []
    try:
        proc = subprocess.run(
            ["ps", "-eo", "pid,comm,args"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        for line in proc.stdout.splitlines()[1:]:
            low = line.lower()
            if not any(p in low for p in patterns):
                continue
            parts = line.split(None, 2)
            if len(parts) < 2:
                continue
            try:
                pid = int(parts[0])
            except ValueError:
                continue
            found.append(
                {
                    "pid": pid,
                    "comm": parts[1],
                    "cmdline": parts[2] if len(parts) > 2 else "",
                }
            )
    except Exception as exc:
        return [{"error": str(exc)}]
    return found


def _desktop_probe(*, ide: str, source: str | None = None) -> dict[str, Any]:
    """Preflight: connected monitors, X11 windows, target IDE processes, optional source check."""
    out: dict[str, Any] = {"ok": True, "ide": ide, "requested_source": source}
    try:
        from vdisplay.application.services.discovery import list_monitors_local, list_windows_local

        mon_payload = list_monitors_local()
        monitors = mon_payload.get("monitors") or []
        monitor_names = [str(m.get("name")) for m in monitors if m.get("name")]
        out["monitors"] = monitors
        out["monitor_names"] = monitor_names
        out["monitor_count"] = mon_payload.get("monitor_count")
        try:
            win_payload = list_windows_local(apps_only=True)
            out["windows"] = win_payload.get("windows") or []
            out["window_count"] = win_payload.get("window_count")
            out["window_hint"] = win_payload.get("hint")
        except Exception as exc:
            out["windows_error"] = str(exc)
    except Exception as exc:
        out["ok"] = False
        out["discovery_error"] = str(exc)
        out["monitor_names"] = []

    out["ide_processes"] = _probe_ide_processes(ide)
    names = set(out.get("monitor_names") or [])
    if source:
        out["source_available"] = source in names
        if source not in names and names:
            out["ok"] = False
            out["error"] = (
                f"requested monitor {source!r} not connected "
                f"(available: {sorted(names)})"
            )
    return out


def _resolve_vdisplay_source_for_ide(
    ide: str,
    *,
    probe: dict[str, Any] | None = None,
) -> tuple[str, dict[str, Any]]:
    """Pick capture monitor: explicit env > IDE default > DP-* > primary > first connected."""
    explicit = os.environ.get("KORU_VDISPLAY_SOURCE", "").strip()
    canon = _canonical_ide(ide)
    preferred = explicit or _IDE_DEFAULT_SOURCE.get(canon, "DP-1")
    if probe is None:
        probe = _desktop_probe(ide=ide, source=preferred)
    names = set(probe.get("monitor_names") or [])

    if explicit and explicit not in names and names:
        failed_probe = {
            **probe,
            "requested_source": explicit,
            "resolved_source": explicit,
            "source_available": False,
            "ok": False,
            "error": (
                f"requested monitor {explicit!r} not connected "
                f"(available: {sorted(names)})"
            ),
        }
        return explicit, failed_probe

    candidates: list[str] = []
    for value in (explicit, preferred):
        if value and value not in candidates:
            candidates.append(value)
    for monitor in probe.get("monitors") or []:
        name = str(monitor.get("name") or "")
        if name.startswith("DP-") and name not in candidates:
            candidates.append(name)
    for monitor in probe.get("monitors") or []:
        if monitor.get("primary") and monitor.get("name"):
            name = str(monitor["name"])
            if name not in candidates:
                candidates.append(name)
    for name in sorted(names):
        if name not in candidates:
            candidates.append(name)

    chosen = preferred
    for candidate in candidates:
        if candidate in names:
            chosen = candidate
            break

    resolved_probe = {
        **probe,
        "requested_source": preferred,
        "resolved_source": chosen,
        "source_available": chosen in names if names else None,
    }
    if names and chosen not in names:
        resolved_probe["ok"] = False
        resolved_probe["error"] = (
            f"no connected monitor for {preferred!r} "
            f"(available: {sorted(names)})"
        )
    elif chosen != preferred:
        resolved_probe["source_auto_resolved"] = True
        resolved_probe["source_was"] = preferred
        resolved_probe["ok"] = True
        resolved_probe["source_available"] = True
        resolved_probe.pop("error", None)
    else:
        resolved_probe["ok"] = bool(resolved_probe.get("ok", True))
        resolved_probe["source_available"] = chosen in names if names else None
    return chosen, resolved_probe


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
    canon = _canonical_ide(ide)
    return _IDE_DEFAULT_SOURCE.get(canon, "DP-1")


def _photo_vql_metadata_root() -> Path:
    from pathlib import Path

    return Path(os.environ.get("VDISPLAY_METADATA_DIR", ".vdisplay")).expanduser()


_IDE_WINDOW_TITLE_TOKENS: dict[str, tuple[str, ...]] = {
    "cursor": ("cursor",),
    "windsurf": ("windsurf",),
    "vscode": ("visual studio code", "vscode"),
    "vscodium": ("vscodium",),
    "antigravity": ("antigravity",),
    "zed": ("zed",),
    "jetbrains": ("jetbrains", "pycharm", "intellij", "idea", "webstorm", "goland", "clion", "rider"),
    "pycharm": ("pycharm", "jetbrains"),
    "idea": ("intellij", "idea", "jetbrains"),
}

# Window-title tokens that invalidate a capture for the requested IDE (avoid breadcrumb false positives).
_COMPETING_IDE_WINDOW_TOKENS: dict[str, tuple[str, ...]] = {
    "jetbrains": ("cursor", "visual studio code", "vscode", "windsurf", "vscodium", "antigravity", "zed"),
    "pycharm": ("cursor", "visual studio code", "vscode", "windsurf"),
    "idea": ("cursor", "visual studio code", "vscode", "windsurf"),
    "cursor": ("pycharm", "intellij", "jetbrains", "webstorm"),
    "windsurf": ("pycharm", "intellij", "jetbrains"),
    "vscode": ("pycharm", "intellij", "jetbrains", "cursor"),
}


def _window_titles_from_vql_meta(meta: dict) -> list[str]:
    titles: list[str] = []
    for layer in meta.get("ui_elements") or meta.get("layers") or []:
        if not isinstance(layer, dict):
            continue
        role = str(layer.get("role") or layer.get("kind") or "").lower()
        if role != "window":
            continue
        title = str(layer.get("label") or layer.get("text") or layer.get("title") or "").strip()
        if title:
            titles.append(title)
    if not titles:
        # When structural layers empty (no imgl / no window role), still try to recover title
        # from capture_validation (vdisplay side) only. Avoid polluting titles list with full
        # nl/img2nl paragraphs (those can contain cross-IDE mentions from prior sessions and
        # cause false competing detection in tests or mixed .vdisplay dirs).
        # body_ide_mentions + explicit window_titles in cv are short and safe.
        cv = meta.get("capture_validation") or {}
        if isinstance(cv, dict):
            for k in ("window_titles", "title", "capture_title"):
                val = cv.get(k)
                if isinstance(val, str) and val.strip():
                    titles.append(val.strip())
                elif isinstance(val, list):
                    titles.extend([str(x).strip() for x in val if str(x).strip()])
            bod = cv.get("body_ide_mentions") or []
            if isinstance(bod, list):
                titles.extend([str(x).strip() for x in bod if str(x).strip()])
        # Do NOT inject raw nl here; the vdisplay-side capture_validation + its reasons are
        # authoritative for "confirmed" when layers==0. Koru mismatch logic + empty_layers
        # guard in get_vql already force map for jetbrains on empty.
    # de-dup preserve order
    seen = set()
    uniq = []
    for t in titles:
        lt = t.lower()
        if lt not in seen:
            seen.add(lt)
            uniq.append(t)
    return uniq


def _capture_title_from_meta(meta: dict | None) -> str | None:
    titles = _window_titles_from_vql_meta(meta or {})
    return titles[0] if titles else None


_VQL_TERMINAL_LABEL_NOISE = (".py", ".ts", "session", "metadata", "vdisplay", "automation", "env", "KORU", "DRY_RUN", "PREFER", "LLM", " --source", "po clear", "recznie", "wpisz", "to do", "drive after", "Re-run", "audit", "cursor_positioning", "Explored", "passed", "Clear", "folder", "Gap Analysis", "Monitored", "screenshot", "act/", "ts - Cursor", "File Edit Selection", "Go Run Terminal", "Publish v", "247K", "Path(str(vql_path)", "imgl_path", "sidecar older than", "reasons.append", "You have folder", "faster responses")
_VQL_CHAT_LABEL_HINTS = ("ask", "prompt", "message", "chat", "composer", "type")


def validate_vql_chat_target(
    target: dict[str, Any],
    *,
    ide: str,
    meta: dict | None = None,
    capture_mismatch: dict[str, Any] | None = None,
    selection_method: str | None = None,
    is_code_edit: bool = False,
    x: int | None = None,
    y: int | None = None,
) -> dict[str, Any]:
    """Hard validation of a VQL/map chat target before actuation (audit + inference_ok)."""
    meta = meta or {}
    method = str(selection_method or target.get("selection_method") or "")
    is_map = method.startswith("map_") or str(target.get("id") or "").startswith("map:")
    cc = target.get("click_center") or {}
    lx = int(x if x is not None else cc.get("x") or 0)
    ly = int(y if y is not None else cc.get("y") or 0)
    capture_title = _capture_title_from_meta(meta)
    app_match = capture_mismatch is None
    bounds = target.get("bounds") or {}
    bw = int(bounds.get("w") or bounds.get("width") or 0)
    bh = int(bounds.get("h") or bounds.get("height") or 0)
    label = str(target.get("label") or target.get("note") or "").lower()
    area = bw * bh if bw > 0 and bh > 0 else 0
    has_bounds = bw > 0 and bh > 0
    vql_element_size_ok = (not has_bounds) or (bw >= 200 and bh >= 25)
    if label == "background":
        label_ok = False
    elif not label:
        label_ok = not has_bounds or (bw >= 200 and bh >= 25)
    else:
        label_ok = any(h in label for h in _VQL_CHAT_LABEL_HINTS)

    validation_errors: list[str] = []
    coord_warnings = _validate_chat_coords_for_ide(
        x=lx, y=ly, ide=ide, target=target, is_code_edit=is_code_edit
    )

    if not is_code_edit:
        if not app_match:
            validation_errors.append("vql_invalid_for_chat_capture_mismatch")
        if is_map and capture_mismatch:
            validation_errors.append("used_map_because_mismatch_or_bad_element")
        elif is_map and method == "map_fallback_after_bad_corner":
            validation_errors.append("used_map_because_mismatch_or_bad_element")
        elif not is_map:
            if has_bounds and not vql_element_size_ok:
                validation_errors.append(f"vql_element_too_small_for_chat_composer_{bw}x{bh}")
            if label == "background" or (label in {"", "background"} and has_bounds and area < 5000):
                validation_errors.append("vql_label_background_not_composer")
            if any(term in label for term in _VQL_TERMINAL_LABEL_NOISE):
                validation_errors.append(f"vql_label_terminal_noise:{label[:40]}")
            shell_pollution_tokens = ("KORU_", "DRY_RUN", "PREFER LLM", " --source", "po clear", "recznie", "wpisz", "to do", "drive after", "Re-run", "audit", "cursor_positioning", "Explored", "passed", "Clear", "Gap Analysis", "Monitored", "screenshot", "act/", "ts - Cursor", "File Edit", "Go Run Terminal", "Publish v", "247K", "automation-gap")
            if any(tok.lower() in label for tok in shell_pollution_tokens):
                validation_errors.append("vql_label_shell_pollution_from_terminal_text")
            if not label_ok and has_bounds:
                validation_errors.append("vql_label_not_chat_composer")
            confidence = target.get("confidence")
            if isinstance(confidence, (int, float)) and float(confidence) < 0.25:
                validation_errors.append("vql_confidence_too_low")

    vql_valid = True
    if not is_code_edit and not is_map:
        if validation_errors:
            vql_valid = False

    return {
        "ok": vql_valid and app_match and not coord_warnings,
        "vql_valid": vql_valid,
        "vql_element_size_ok": vql_element_size_ok,
        "app_match": app_match,
        "capture_title": capture_title,
        "selection_method": method or None,
        "is_map_target": is_map,
        "validation_errors": validation_errors,
        "coord_warnings": coord_warnings,
        "bounds": {"w": bw, "h": bh} if has_bounds else None,
        "label": label[:80] if label else None,
        "used_map_because_mismatch_or_bad_element": is_map
        and (
            bool(capture_mismatch)
            or method in {"map_fallback_after_bad_corner", "map_calibrated_on_mismatch"}
        ),
    }


def _capture_validation_from_meta(meta: dict | None) -> dict[str, Any] | None:
    if not meta:
        return None
    cv = meta.get("capture_validation")
    if isinstance(cv, dict):
        return cv
    nested = meta.get("metadata") if isinstance(meta.get("metadata"), dict) else {}
    cv = nested.get("capture_validation") if isinstance(nested, dict) else None
    return cv if isinstance(cv, dict) else None


def _capture_confirmed_from_meta(*, ide: str, meta: dict | None) -> bool:
    """Single source of truth: observe sidecar only (never map file mtime)."""
    meta = meta or {}
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


def _allow_actuation_on_capture_mismatch() -> bool:
    """When false (default), abort drive instead of map/photo actuation on wrong IDE capture."""
    if _ide_mismatch_allowed():
        return True
    return os.environ.get("KORU_VDISPLAY_ALLOW_MAP_ON_MISMATCH", "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def _competing_ide_label_from_warning(mismatch: dict[str, Any]) -> str | None:
    """Return a human-readable competing IDE name from capture validation (e.g. Cursor)."""
    titles = mismatch.get("window_titles") or []
    joined = " | ".join(str(t) for t in titles).lower()
    for token in mismatch.get("competing_detected") or ():
        tok = str(token).strip().lower()
        if tok and tok in joined:
            return tok.title() if tok == "cursor" else tok
    for name in ("cursor", "vscode", "visual studio code", "windsurf", "zed"):
        if name in joined:
            return name.title() if name == "cursor" else name
    return None


def _drive_blocked_on_capture_mismatch(
    *,
    ide: str,
    mismatch: dict[str, Any],
    dry_run: bool = False,
) -> dict[str, Any] | None:
    if dry_run or _allow_actuation_on_capture_mismatch():
        return None
    competing = _competing_ide_label_from_warning(mismatch)
    focus_hint = (
        f"Minimize or move {competing} off the capture monitor, focus the target IDE, then retry."
        if competing
        else "Focus the target IDE on the capture monitor, confirm window title in observe/capture, then retry."
    )
    return {
        "ok": False,
        "backend": "vdisplay+capture-blocked",
        "capture_confirmed": False,
        "ide_window_warning": mismatch,
        "competing_ide": competing,
        "error": str(mismatch.get("message") or "capture does not match requested IDE"),
        "hint": (
            f"{focus_hint} "
            "Set KORU_VDISPLAY_ALLOW_MAP_ON_MISMATCH=1 to allow map-only fallback anyway."
        ),
        "ide": ide,
    }


def _photo_vql_ide_window_warning(*, ide: str, meta: dict) -> dict[str, Any] | None:
    """Warn when the captured **foreground window title** does not match the requested IDE.

    Uses the window layer only (not breadcrumb labels like ``PyCharm/JB`` inside another IDE).
    Prefers ``capture_validation`` embedded at VQL write time when present.
    """
    cv = _capture_validation_from_meta(meta)
    if isinstance(cv, dict):
        if cv.get("capture_confirmed") is True:
            return None
        embedded = cv.get("ide_window_warning")
        if isinstance(embedded, dict):
            return embedded
        if cv.get("capture_confirmed") is False:
            reasons = list(cv.get("reasons") or [])
            structure = cv.get("structure") if isinstance(cv.get("structure"), dict) else {}
            for item in structure.get("reasons") or []:
                if item not in reasons:
                    reasons.append(item)
            return {
                "ide": _canonical_ide(ide),
                "expected_tokens": list(_IDE_WINDOW_TITLE_TOKENS.get(_canonical_ide(ide), ())),
                "window_titles": list(cv.get("window_titles") or _window_titles_from_vql_meta(meta)),
                "capture_validation_failed": True,
                "reasons": reasons,
                "message": (
                    f"Photo VQL capture not confirmed for {_canonical_ide(ide)}: "
                    f"validation reasons={reasons!r}. Focus the target IDE and refresh observe."
                ),
            }

    canon = _canonical_ide(ide)
    if canon in {"", "auto"}:
        return None
    tokens = _IDE_WINDOW_TITLE_TOKENS.get(canon)
    if not tokens:
        hints = _ide_hints(canon)
        needle = str(hints.get("window_title_contains") or "").strip().lower()
        tokens = (needle,) if needle else ()
    if not tokens:
        return None
    titles = _window_titles_from_vql_meta(meta)
    if not titles:
        return None

    joined_titles = " | ".join(titles).lower()
    competing = _COMPETING_IDE_WINDOW_TOKENS.get(canon, ())
    if any(comp in joined_titles for comp in competing):
        return {
            "ide": canon,
            "expected_tokens": list(tokens),
            "window_titles": titles,
            "competing_detected": list(competing),
            "message": (
                f"Photo VQL capture foreground window looks like a different IDE than {canon}: "
                f"title(s)={titles!r}. Re-focus {canon} on the capture monitor and refresh observe."
            ),
        }
    if any(token in joined_titles for token in tokens):
        return None
    return {
        "ide": canon,
        "expected_tokens": list(tokens),
        "window_titles": titles,
        "message": (
            f"Photo VQL capture does not look like {canon}: "
            f"window title(s)={titles!r}. Focus the correct IDE on the target monitor before real drive."
        ),
    }


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


def _resolve_photo_png_path_from_vql(
    *,
    vql_path: str | None = None,
    source: str | None = None,
) -> str | None:
    """Resolve the screenshot PNG paired with a photo-VQL sidecar (for LLM vision)."""
    from pathlib import Path

    explicit = os.environ.get("KORU_VDISPLAY_PHOTO_PATH", "").strip()
    if explicit and os.path.isfile(explicit):
        return explicit

    cand_vql = (vql_path or os.environ.get("KORU_VDISPLAY_VQL_PATH", "")).strip()
    if cand_vql:
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


def _ide_mismatch_allowed() -> bool:
    return os.environ.get("KORU_VDISPLAY_ALLOW_IDE_MISMATCH", "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


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
    return os.environ.get("KORU_VDISPLAY_AUTO_IDE_CONTROL", "1").strip().lower() in {
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


def _focus_window_gnome_shell(*, title_contains: str) -> dict[str, Any]:
    """Best-effort raise via org.gnome.Shell.Eval (may be blocked on some GNOME builds)."""
    import re
    import subprocess

    needle = title_contains.replace("\\", "\\\\").replace("'", "\\'").lower()
    script = (
        "(() => {"
        "const needle = '" + needle + "';"
        "const actors = global.get_window_actors();"
        "for (const a of actors) {"
        "  const w = a.metaWindow;"
        "  const t = (w.get_title() || '').toLowerCase();"
        "  if (t.includes(needle)) { w.unminimize(); w.activate(global.get_current_time()); return w.get_title(); }"
        "}"
        "return null;"
        "})()"
    )
    try:
        proc = subprocess.run(
            [
                "gdbus",
                "call",
                "--session",
                "--dest",
                "org.gnome.Shell",
                "--object-path",
                "/org/gnome/Shell",
                "--method",
                "org.gnome.Shell.Eval",
                script,
            ],
            capture_output=True,
            text=True,
            timeout=3.0,
            check=False,
        )
        text = (proc.stdout or "").strip()
        match = re.search(r"\(\s*(true|false)\s*,\s*'([^']*)'\s*\)", text, flags=re.IGNORECASE)
        if match and match.group(1).lower() == "true" and match.group(2):
            return {"ok": True, "method": "gnome-shell-eval", "title": match.group(2)}
        return {"ok": False, "method": "gnome-shell-eval", "error": text or proc.stderr or "eval failed"}
    except Exception as exc:
        return {"ok": False, "method": "gnome-shell-eval", "error": str(exc)}


def _focus_window_gnome_shell_for_ide(*, ide: str) -> dict[str, Any]:
    """Try GNOME Shell raise with IDE-specific title needles (PyCharm, IntelliJ, …)."""
    hints = _ide_hints(ide)
    needles: list[str] = []
    for candidate in (
        str(hints.get("window_title_contains") or ""),
        _ide_prompt_app_id(ide),
        "pycharm",
        "intellij",
        "jetbrains",
        "webstorm",
        "goland",
    ):
        token = candidate.strip().lower()
        if token and token not in needles:
            needles.append(token)
    attempts: list[dict[str, Any]] = []
    for needle in needles:
        res = _focus_window_gnome_shell(title_contains=needle)
        attempts.append({"needle": needle, **res})
        if res.get("ok"):
            return {"ok": True, "method": "gnome-shell-eval", "title": res.get("title"), "needle": needle, "attempts": attempts}
    return {
        "ok": False,
        "method": "gnome-shell-eval",
        "error": "no window matched any title needle",
        "attempts": attempts,
    }


def _click_map_region_center(
    map_path: str,
    *,
    source: str,
    region_id: str = "pycharm.ai_chat",
) -> dict[str, Any]:
    """Click the center of a GUI map region (raises native Wayland window on that monitor)."""
    try:
        from vdisplay.control.gui_map import load_gui_map

        pack = load_gui_map(map_path)
        region = pack.regions.get(region_id)
        if region is None and pack.regions:
            region = next(iter(pack.regions.values()))
        if region is None:
            return {"ok": False, "error": f"region {region_id!r} not in map"}
        bounds = region.scope_bounds
        cx = int(bounds.x + bounds.width / 2)
        # Upper quarter of region — avoid bottom edge / GNOME hot corner on rotated DP-2.
        cy = int(bounds.y + min(max(bounds.height * 0.22, 48), bounds.height - 48))
        click = _control_click(
            backend="vision",
            x=cx,
            y=cy,
            source=source,
            map_path=map_path,
        )
        return {"ok": bool(click.get("ok", True)), "region_id": region.id, "coords": {"x": cx, "y": cy}, "click": click}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def _raise_alt_tab_enabled(*, ide: str = "auto") -> bool:
    raw = os.environ.get("KORU_VDISPLAY_RAISE_ALT_TAB", "").strip().lower()
    if raw in {"1", "true", "yes", "on"}:
        return True
    if raw in {"0", "false", "no", "off"}:
        return False
    return _canonical_ide(ide) in {"jetbrains", "pycharm", "idea"}


def _alt_tab_window_cycle(*, cycles: int = 1, ide: str = "auto") -> dict[str, Any]:
    """Optional ydotool Alt+Tab cycles to raise a background window."""
    if not _raise_alt_tab_enabled(ide=ide):
        return {"ok": False, "skipped": True}
    try:
        from vdisplay.input.resolve import resolve_pointer_input

        inp, method = resolve_pointer_input()
        hotkey = getattr(inp, "hotkey", None)
        if hotkey is None:
            return {"ok": False, "error": "hotkey unavailable"}
        for _ in range(max(1, cycles)):
            try:
                hotkey("alt", "Tab")
            except TypeError:
                hotkey("alt+Tab")
            import time

            time.sleep(0.35)
        return {"ok": True, "method": f"{method}-alt-tab", "cycles": cycles}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


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
    map_path = _resolve_ide_prompt_map(app_id)
    result["map_path"] = map_path

    if _auto_open_ide_enabled(ide=ide):
        try:
            from vdisplay.ide_prompt import open_desktop_app

            opened = open_desktop_app(app_id, wait_seconds=2.0)
            result["steps"].append({"open": opened})
        except Exception as exc:
            result["steps"].append({"open": {"ok": False, "error": str(exc)}})

    gnome_focus = _focus_window_gnome_shell_for_ide(ide=ide)
    result["steps"].append({"gnome_raise": gnome_focus})

    if map_path:
        region_click = _click_map_region_center(map_path, source=src)
        result["steps"].append({"region_raise": region_click})

    alt_tab = _alt_tab_window_cycle(
        cycles=int(os.environ.get("KORU_VDISPLAY_RAISE_ALT_TAB_CYCLES", "2")),
        ide=ide,
    )
    if not alt_tab.get("skipped"):
        result["steps"].append({"alt_tab": alt_tab})

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

    interior_ok = False
    if map_path and not any(
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

    if focus_interior and map_path:
        import time

        from vdisplay.control.timing import control_focus_type_seconds

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

    result["steps"].append({"dismiss_overview": _dismiss_gnome_overview(reason="post-control")})

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
    # For JetBrains on rotated monitors (DP-2 etc), successful map/region/interior clicks bring the window forward
    # and focus the chat area (as seen in real DP-2 tests with ydotool + rotation mapping succeeding even when
    # strict window selector fails). Count as window_focused for better reporting and downstream logic.
    if not window_ok and (interior_ok or fallback_ok) and _canonical_ide(ide) in {"jetbrains", "pycharm", "idea"}:
        window_ok = True
    result["ok"] = interior_ok or window_ok or open_ok or bool(map_path and focus_interior)
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
    return result


def _import_imgl_targets(name: str):
    """Import ``resolve_*`` from semcod imgl even when koru ships minimal ``imgl`` stubs."""
    import importlib
    import importlib.util

    try:
        mod = importlib.import_module("imgl.targets")
        if hasattr(mod, name):
            return getattr(mod, name)
    except ImportError:
        pass

    imgl_src = os.environ.get("IMGL_SRC", str(Path.home() / "github/semcod/imgl")).strip()
    targets_path = Path(imgl_src).expanduser() / "imgl" / "targets.py"
    if targets_path.is_file():
        spec = importlib.util.spec_from_file_location("_semcod_imgl_targets", targets_path)
        if spec and spec.loader:
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            if hasattr(mod, name):
                return getattr(mod, name)
    return None


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


def refresh_photo_vql_sidecar(*, source: str | None = None, ide: str = "auto") -> dict[str, Any]:
    """Capture fresh screenshot + VQL sidecar for photo-VQL drive (observe via vdisplay CLI/agent)."""
    import subprocess

    src = source or _vdisplay_source_for_ide(ide)
    os.environ["KORU_VDISPLAY_SOURCE"] = src
    session = _autonomy_session.active_session_dir()
    png = _resolve_photo_png_path(src)
    vql = png.with_suffix(png.suffix + ".vql.json")
    png.parent.mkdir(parents=True, exist_ok=True)

    if _dry_run():
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

    cmd = [
        "vdisplay",
        "screenshot",
        "-o",
        str(png),
        "--source",
        src,
    ]
    env = os.environ.copy()
    canon = _canonical_ide(ide)
    if canon not in {"", "auto"}:
        env.setdefault("VDISPLAY_CAPTURE_VALIDATE_IDE", canon)
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120, check=False, env=env)
    except Exception as exc:
        return {"ok": False, "error": str(exc), "source": src, "png": str(png)}

    if proc.returncode != 0:
        return {
            "ok": False,
            "error": (proc.stderr or proc.stdout or "screenshot failed").strip(),
            "source": src,
            "png": str(png),
            "returncode": proc.returncode,
        }

    os.environ["KORU_VDISPLAY_VQL_PATH"] = str(vql)
    meta = load_vql_metadata(str(vql), allow_stale=True)
    elements = meta.get("ui_elements") or meta.get("layers") or []
    main_layers = _main_vql_layer_count(vql)
    if main_layers == 0 and png.is_file():
        try:
            from vdisplay.integrations.pipeline import observe_screen

            observe_screen(
                image_path=png,
                capture_meta={"path": str(png.resolve()), "source": src},
                write_sidecar=True,
            )
            meta = load_vql_metadata(str(vql), allow_stale=True)
            elements = meta.get("ui_elements") or meta.get("layers") or []
            main_layers = _main_vql_layer_count(vql)
        except Exception as exc:
            out = {
                "ok": True,
                "source": src,
                "png": str(png.resolve()),
                "vql": str(vql.resolve()) if vql.is_file() else str(vql),
                "elements": len(elements),
                "main_vql_layers": main_layers,
                "observe_fallback_error": str(exc),
            }
            if session is not None:
                out["session_dir"] = str(session)
            return out

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
    return out


def prepare_photo_vql_for_drive(*, ide: str) -> dict[str, Any]:
    """Observe (if needed) + pin sidecar before koru drive / send_chat."""
    import time

    src, desktop_probe = _resolve_vdisplay_source_for_ide(ide)
    os.environ.setdefault("KORU_VDISPLAY_CONTROL_FALLBACK", "1")
    os.environ.setdefault("KORU_VDISPLAY_USE_VQL_MOUSE_FOCUS", "1")
    os.environ["KORU_VDISPLAY_SOURCE"] = src
    os.environ.pop("KORU_VDISPLAY_CAPTURE_MATCHES_IDE", None)

    session_dir = _autonomy_session.begin_autonomy_session(ide=ide, source=src)
    _autonomy_session.persist_autonomy_phase(session_dir, "decide", "desktop_probe", desktop_probe)

    if not desktop_probe.get("ok") and _abort_on_desktop_probe_fail():
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

    retries = max(1, int(os.environ.get("KORU_VDISPLAY_IDE_CONTROL_RETRIES", "3") or "3"))
    ide_control: dict[str, Any] | None = None
    out = {"ok": False, "source": src, "session_dir": str(session_dir), "desktop_probe": desktop_probe}
    loop_attempts = 0

    for attempt in range(retries):
        loop_attempts = attempt + 1
        if _auto_ide_control_enabled():
            ide_control = ensure_vdisplay_ide_control(ide=ide, source=src)
            if ide_control.get("map_actuation_ok") or ide_control.get("interior_focused"):
                import time

                time.sleep(
                    float(os.environ.get("KORU_VDISPLAY_POST_FOCUS_CAPTURE_DELAY_S", "0.8"))
                )
        if photo_vql_sidecar_needs_refresh(source=src, ide=ide):
            out = refresh_photo_vql_sidecar(source=src, ide=ide)
        else:
            png = _resolve_photo_png_path(src)
            vql = png.with_suffix(png.suffix + ".vql.json")
            meta = load_vql_metadata(str(vql))
            out = {
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
        if not out.get("ok"):
            break
        warn = out.get("ide_window_warning") or _photo_vql_ide_window_warning(
            ide=ide,
            meta=load_vql_metadata(str(out.get("vql") or "")),
        )
        if warn:
            out["ide_window_warning"] = warn
            out["capture_matches_ide"] = False
            os.environ.pop("KORU_VDISPLAY_CAPTURE_MATCHES_IDE", None)
            cv = out.get("capture_validation") or {}
            if isinstance(cv, dict) and cv.get("body_false_positive"):
                out["body_false_positive"] = True
            if (
                not _allow_actuation_on_capture_mismatch()
                and not out.get("_focus_recovery_tried")
                and _raise_alt_tab_enabled(ide=ide)
            ):
                out["_focus_recovery_tried"] = True
                recovery = _alt_tab_window_cycle(cycles=1, ide=ide)
                out["focus_recovery"] = recovery
                if recovery.get("ok"):
                    import time

                    time.sleep(float(os.environ.get("KORU_VDISPLAY_POST_FOCUS_CAPTURE_DELAY_S", "0.8")))
                    recovered = refresh_photo_vql_sidecar(source=src, ide=ide)
                    recovered["focus_recovery"] = recovery
                    out = recovered
                    warn = out.get("ide_window_warning") or _photo_vql_ide_window_warning(
                        ide=ide,
                        meta=load_vql_metadata(str(out.get("vql") or ""), allow_stale=True),
                    )
                    if not warn:
                        out["ide_window_warning"] = None
                        out["capture_matches_ide"] = True
                        os.environ["KORU_VDISPLAY_CAPTURE_MATCHES_IDE"] = "1"
                        if _canonical_ide(ide) in {"jetbrains", "pycharm", "idea"}:
                            os.environ.setdefault("KORU_VDISPLAY_PREFER_PHOTO_VQL", "auto")
                        break
                    out["ide_window_warning"] = warn
            if not _allow_actuation_on_capture_mismatch():
                break
        elif _capture_matches_requested_ide(ide):
            os.environ["KORU_VDISPLAY_CAPTURE_MATCHES_IDE"] = "1"
            out["capture_matches_ide"] = True
            if _canonical_ide(ide) in {"jetbrains", "pycharm", "idea"}:
                os.environ.setdefault("KORU_VDISPLAY_PREFER_PHOTO_VQL", "auto")
            break
        out["capture_matches_ide"] = False
        # On mismatch for JetBrains etc, do extra focus via map when map-only fallback is allowed,
        # then re-capture to get correct VQL for the target IDE on the source.
        if _allow_actuation_on_capture_mismatch():
            mp = None
            if ide_control:
                mp = ide_control.get("map_path")
            if not mp:
                mp = _resolve_ide_prompt_map(_ide_prompt_app_id(ide))
            if _canonical_ide(ide) in {"jetbrains", "pycharm", "idea"} and mp:
                try:
                    for t in _map_interior_targets_for_ide(_ide_prompt_app_id(ide), mp)[:1]:
                        _control_click(backend="vision", map_path=mp, map_target=t, source=src)
                    import time
                    time.sleep(0.4)
                    out = refresh_photo_vql_sidecar(source=src, ide=ide)
                except Exception:
                    pass
        if attempt + 1 < retries:
            time.sleep(float(os.environ.get("KORU_VDISPLAY_IDE_CONTROL_RETRY_DELAY_S", "0.6")))

    if ide_control is not None:
        out["ide_control"] = ide_control
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
            out["capture_confirmed"] = out["capture_provenance"].get("capture_confirmed")
        except Exception:
            pass
    confirmed = out.get("capture_confirmed")
    if confirmed is None:
        confirmed = not bool(out.get("ide_window_warning"))
    out["capture_ready"] = bool(confirmed)

    if (
        not confirmed
        and ide_control is not None
        and (ide_control.get("map_actuation_ok") or ide_control.get("interior_focused"))
        and _allow_actuation_on_capture_mismatch()
    ):
        out["capture_ready"] = True
        out["map_only_fallback"] = True
        if out.get("ide_window_warning"):
            out["ide_window_warning_map_fallback"] = out["ide_window_warning"]

    if ide_control and out.get("ide_window_warning"):
        ide_control["capture_confirmed"] = False
        ide_control["visual_guard_failed"] = True
        if ide_control.get("map_actuation_ok") or ide_control.get("interior_focused"):
            ide_control["confirmation_bias_risk"] = (
                "Map/interior actuation succeeded but observe capture still shows a different IDE."
            )
    elif ide_control is not None:
        ide_control["capture_confirmed"] = bool(confirmed)
        ide_control["visual_guard_failed"] = False

    if not confirmed and not out.get("map_only_fallback"):
        mismatch = out.get("ide_window_warning") or {}
        blocked = _drive_blocked_on_capture_mismatch(
            ide=ide,
            mismatch=mismatch if mismatch else {"message": "capture does not match requested IDE"},
        )
        if blocked:
            out["ok"] = False
            out["capture_ready"] = False
            out["error"] = blocked.get("error")
            out["hint"] = blocked.get("hint")
            if blocked.get("competing_ide"):
                out["competing_ide"] = blocked["competing_ide"]
    elif out.get("capture_ready"):
        out["ok"] = True
    out["desktop_probe"] = desktop_probe
    _autonomy_session.persist_autonomy_phase(session_dir, "observe", "prepare", out)
    return out


def _normalize_photo_vql_drive_result(photo_res: dict[str, Any], *, ide: str, submit: bool) -> dict[str, Any]:
    """Map perform_photo_vql_focus_and_edit output to send_chat response shape."""
    edit = photo_res.get("edit") or {}
    edit_message = edit.get("message")
    if not edit_message and edit.get("method"):
        edit_message = f"typed via {edit['method']}"
    out = {
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
    if photo_res.get("verified") is False:
        out["ok"] = False
    if photo_res.get("capture_confirmed") is False:
        out["ok"] = False
        out["capture_confirmed"] = False
    elif photo_res.get("capture_confirmed") is True:
        out["capture_confirmed"] = True
    plan = photo_res.get("vql_command_plan") or {}
    if plan.get("inference_ok") is False and not _allow_actuation_on_capture_mismatch():
        out["ok"] = False
    if photo_res.get("capture_provenance"):
        out["capture_provenance"] = photo_res.get("capture_provenance")
        if out.get("capture_confirmed") is None:
            out["capture_confirmed"] = out["capture_provenance"].get("capture_confirmed")
    if photo_res.get("verification"):
        out["verification"] = photo_res.get("verification")
        out["verified"] = photo_res.get("verified")
    out["submitted"] = bool(photo_res.get("submitted"))
    submit_result = photo_res.get("submit")
    if submit_result is not None:
        out["submit_result"] = submit_result
    if submit and out.get("submitted"):
        out["message"] = f"{out['message']} (submitted)"
    return out


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
    key = "ctrl+Return" if app_id in {"pycharm", "jetbrains", "idea"} or canon in {"cursor", "jetbrains", "pycharm", "idea"} else "Return"
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


def send_chat(
    prompt: str,
    *,
    ide: str,
    submit: bool,
    dry_run: bool | None = None,
) -> dict[str, Any]:
    """Semantic IDE chat drive via vdisplay control plane."""
    effective_dry = _dry_run() if dry_run is None else dry_run
    use_llm_vision = os.environ.get("KORU_VDISPLAY_LLM_VISION_DECISION", "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    is_code = _photo_vql_code_edit_enabled()

    # JetBrains + wrong IDE on capture: abort by default (avoid map/LLM confirmation bias).
    if not is_code:
        mismatch = _photo_vql_ide_capture_mismatch(ide=ide)
        blocked = _drive_blocked_on_capture_mismatch(
            ide=ide, mismatch=mismatch, dry_run=effective_dry
        ) if mismatch else None
        if blocked is not None:
            session = _autonomy_session.active_session_dir()
            if session is not None:
                _autonomy_session.persist_autonomy_phase(session, "decide", "capture_blocked", blocked)
            return blocked
        if _prefer_ide_prompt_over_photo_vql(ide=ide):
            if not effective_dry and vdisplay_available():
                ide_prompt = send_chat_via_ide_prompt(
                    prompt,
                    ide=ide,
                    submit=submit,
                    dry_run=False,
                )
                if ide_prompt is not None and ide_prompt.get("ok"):
                    if mismatch:
                        ide_prompt["ide_window_warning"] = mismatch
                        ide_prompt["photo_vql_skipped"] = True
                    return ide_prompt
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
                return out

    # Photo VQL + LLM OpenRouter when capture matches (or explicit PREFER=1 without mismatch).
    photo_prefer_chat = (
        _prefer_photo_vql_chat(ide=ide)
        or (use_llm_vision and _capture_matches_requested_ide(ide))
        or is_code
    )
    if photo_prefer_chat:
        if effective_dry:
            os.environ["KORU_VDISPLAY_DRY_RUN"] = "1"
        photo_res = perform_photo_vql_focus_and_edit(
            prompt,
            ide=ide,
            source=_vdisplay_source(),
            is_code_edit=is_code,
            submit=submit,
        )
        return _normalize_photo_vql_drive_result(photo_res, ide=ide, submit=submit)

    if effective_dry and not _prefer_photo_vql_chat(ide=ide):
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

    if _auto_ide_control_enabled() and _photo_vql_ide_capture_mismatch(ide=ide):
        ensure_vdisplay_ide_control(ide=ide, source=_vdisplay_source())

    # === Early preference for jetbrains/pycharm (os_injector or ide_prompt) to keep compatibility and test expectations ===
    # These paths are used when a map or calibrated profile exists; VQL photo focus is still available via the pure vdisplay semantic path below.
    canon = _canonical_ide(ide)
    if canon in {"jetbrains", "pycharm"}:
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

    ide_prompt = send_chat_via_ide_prompt(
        prompt,
        ide=ide,
        submit=submit,
        dry_run=False,
    )
    if ide_prompt is not None and ide_prompt.get("ok"):
        return ide_prompt

    # === send_chat semantic vdisplay body (VQL photo chat focus + selector/set_value) ===
    hints = _ide_hints(ide)
    focus_error: str | None = None
    photo_vql_target = None

    # NEW (user request): based on foto screen VQL (koru-cont-dp1-*.png 31 elems etc),
    # locate okno chat/panel, move mouse to its click_center from the photo, click to focus keyboard.
    # Only in the pure vdisplay semantic control path (after ide_prompt/os_injector prefs).
    # IDE independent (same VQL photo works for jetbrains, cursor, ...).
    # Always resolve photo target so we can fall back to its click_center for point-based set_value
    # even if no perfect "chat input" selector (panels from detection often don't have role=input).
    if not _dry_run() and os.environ.get("KORU_VDISPLAY_USE_VQL_MOUSE_FOCUS", "1").strip().lower() not in {"0", "false", "no", "off"}:
        try:
            photo_vql_target = get_vql_chat_target_from_photo()
            # Apply LLM OpenRouter vision analysis on the current screenshot + VQL target (if flag set).
            # This fulfills "na podstawie rzutu ekranu i analizy llm openrouter" for precise chat input location
            # (refines the coarse panel center from foto VQL to the actual prompt/composer field).
            use_llm_vision = os.environ.get("KORU_VDISPLAY_LLM_VISION_DECISION", "").strip().lower() in {"1", "true", "yes", "on"}
            if use_llm_vision:
                image_path = _resolve_photo_png_path_from_vql(source=_vdisplay_source())
                if image_path and os.path.exists(str(image_path)):
                    try:
                        rx, ry, rdec = _resolve_photo_vql_llm_coords(
                            prompt=prompt, target=photo_vql_target, source=_vdisplay_source(), image_path=image_path
                        )
                        if rdec:
                            photo_vql_target = {
                                **photo_vql_target,
                                "click_center": {"x": rx, "y": ry, "note": f"LLM refined from foto: {rdec.get('reason', '')[:60]}"},
                                "llm_refined": True,
                                "llm_decision": rdec,
                            }
                    except Exception:
                        pass
            mf = move_mouse_to_vql_target_and_focus_keyboard(photo_vql_target, ide=ide)
            if mf.get("ok"):
                focus_error = None
            else:
                focus_error = mf.get("error") or mf.get("message")
        except Exception as exc:
            focus_error = str(exc)
            photo_vql_target = get_vql_chat_target_from_photo()  # ensure we have it for fallback

    # Do NOT short-circuit here: after foto VQL (+ optional LLM) locate + mouse move + kb focus,
    # fall through so the prompt text gets typed at the (LLM-refined) click_point via vision backend.
    # This makes "wpisywanie" (insert prompt into JetBrains/Cursor chat) work based on screenshot + OpenRouter LLM.
    # The later click_point injection + _control_set_value(backend=vision, x=..., y=...) does the actual typing at the point.

    selector, found = _find_first_selector(ide=ide, selectors=_chat_selectors_for(ide))
    if selector is None:
        found = _resolve_vql_chat_target(ide, hints)
        if found:
            selector = {"role": "input", "name_contains": "Chat"}
        elif photo_vql_target and photo_vql_target.get("click_center"):
            # Fallback to photo VQL center from the focus we just performed.
            # This allows precise point-based set_value at the foto-derived chat area coords
            # (the move already focused the panel; typing at the center targets the input).
            cc = photo_vql_target["click_center"]
            found = {
                "ok": True,
                "count": 1,
                "selected": {
                    "id": photo_vql_target.get("id", "vql-photo-chat"),
                    "backend": "vql",
                    "role": photo_vql_target.get("role", "panel"),
                    "click_point": cc,
                    "note": "photo VQL fallback for cursor chat after focus move"
                }
            }
            selector = {"role": photo_vql_target.get("role", "panel")}
        else:
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
                "vql_mouse_focus_error": focus_error,
            }

    # If VQL provided a click_point (from photo layers), prefer coord-based action for robustness
    # (works even if AT-SPI/selector name match fails for custom IDE themes).
    selected = (found or {}).get("selected") if isinstance(found, dict) else None
    click_point = None
    if isinstance(selected, dict):
        click_point = selected.get("click_point") or selected.get("click_center")
        if isinstance(click_point, dict) and not selector:
            selector = {"role": "input", "name_contains": "vql"}

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
            "vql_click_point": click_point,
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
            "focus_error": focus_error,
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
    }


def _resolve_vql_chat_target(ide: str, hints: dict) -> dict | None:
    """Resolve chat target using VQL metadata for precise mouse nav on second monitor (DP-1).
    Used in autonomous PyCharm/JetBrains control via vdisplay + VQL centers (e.g. 1024,640).
    """
    vql_target = _find_vql_chat_target(ide)
    if not vql_target and ide in ("pycharm", "jetbrains"):
        vql_target = {"click_center": {"x": 1024, "y": 640, "note": "PyCharm/JetBrains editor area on DP-1 second monitor from VQL"}}
    if vql_target:
        return _extract_vql_click_from_target(vql_target)
    return None


def _find_vql_chat_target(ide: str) -> dict | None:
    """Helper extracted to reduce CC."""
    return get_vql_target(ide, role="input", name_contains="chat") or get_vql_target(ide, role="input") or get_vql_target(ide, label="chat")


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
    """PyCharm specific VQL target for editor on second monitor (DP-1), using VQL click 1024,640 as if clicked in PyCharm on DP-1."""
    return {"click_center": {"x": 1024, "y": 640, "note": "PyCharm editor area on DP-1 second monitor from VQL (autonomous click at 1024,640)"}}


def _get_jetbrains_pycharm_chat_center():
    """Shim: prefer photo VQL based locate for chat window + mouse + kb focus (see get_vql_chat_target_from_photo)."""
    # From current foto screen VQL (31 elems), main editor/chat area on DP-1
    return {"x": 1024, "y": 640, "note": "Chat window area from screen photo VQL (use move_mouse_to_vql_target_and_focus_keyboard for real mouse+focus)"}


def _photo_vql_elements() -> tuple[list[dict], str | None]:
    vql = load_vql_metadata()
    els = vql.get("ui_elements") or vql.get("layers") or []
    return els, vql.get("_source")


def get_vql_chat_target_from_photo(*, prefer_role: str | None = "panel", ide: str = "auto") -> dict:
    """Na podstawie foto screen VQL zlokalizuj okno/panel chat (deleguje do imgl.targets)."""
    els, src = _photo_vql_elements()
    candidates = _photo_vql_chat_input_candidates(els, limit=8)
    canon = _canonical_ide(ide)
    if canon in {"", "auto"}:
        canon = _canonical_ide(os.environ.get("KORU_DRIVE_IDE", "auto"))
    src_name = os.environ.get("KORU_VDISPLAY_SOURCE", "DP-1")

    # Detect terminal pollution in VQL (common on DP-2 when control terminal text is visible in screenshot).
    # If many candidates look like shell/env/command history (from the log's fake "PREFER LLM", "KORU_*", "po clear" etc.),
    # treat as polluted and force map for jetbrains (VQL is unreliable).
    polluted_count = 0
    pollution_tokens = ("KORU_", "DRY_RUN", "PREFER LLM", "po clear", "recznie", "wpisz", "to do", "drive after", "Re-run", "audit", "cursor_positioning", "Explored", "You have folder", "faster responses", "Path(str(vql_path)", "imgl_path", "sidecar older", "reasons.append")
    for c in candidates:
        lab = str(c.get("label") or "").lower()
        if any(tok.lower() in lab for tok in pollution_tokens):
            polluted_count += 1
    is_polluted = len(candidates) > 0 and polluted_count >= max(1, len(candidates) // 2)

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
        cc = out.get("click_center") or {}
        vql_meta = load_vql_metadata(allow_stale=True)
        validation = validate_vql_chat_target(
            out,
            ide=canon,
            meta=vql_meta,
            capture_mismatch=mismatch,
            selection_method=method,
        )
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

    mismatch = _photo_vql_ide_capture_mismatch(ide=canon) if canon in {"jetbrains", "pycharm", "idea"} else None
    empty_layers = len(els) == 0

    if canon in {"jetbrains", "pycharm", "idea"}:
        if mismatch or empty_layers or is_polluted:
            # If capture title doesn't match requested IDE (e.g. Cursor capture during jetbrains drive),
            # or VQL layers empty (imgl not installed / observe produced no ui_elements),
            # or heavily polluted by terminal text (fake inputs from control commands visible on DP-2),
            # distrust VQL layers and prefer calibrated map target ("prompt" preferred for sane coords).
            # This prevents "błędy wnioskowania" from bad/empty VQL data.
            # The log and plan will reflect "map_on_mismatch" or "map_on_empty_vql" so reality is visible in audit.
            map_target = _map_chat_target_capture_local(ide=canon, source=src_name)
            if map_target:
                method = "map_calibrated_on_empty_vql" if empty_layers else "map_calibrated_on_mismatch"
                stage = "vql_target_selection_jetbrains_map_on_empty_vql" if empty_layers else "vql_target_selection_jetbrains_map_on_mismatch"
                map_target = _finalize(map_target, method=method)
                _log_vql_cursor_positioning_at_command(
                    map_target,
                    stage=stage,
                    ide=canon,
                    source=src_name,
                    final_local=map_target.get("click_center", {}),
                    final_global=map_target.get("map_global"),
                    vql_file=src if isinstance(src, str) and str(src).endswith(".vql.json") else None,
                )
                return map_target
        corner = _jetbrains_chat_corner_target_from_layers(els, source=src)
        if corner:
            # Additional post-heuristic validation: even if corner picked, if the element is too small or bad label,
            # it may still be chrome from wrong app VQL. In that case, prefer map.
            cc = corner.get("click_center") or {}
            bounds = corner.get("bounds") or {}
            bw = int(bounds.get("w") or bounds.get("width") or 0)
            bh = int(bounds.get("h") or bounds.get("height") or 0)
            label = str(corner.get("label") or "").lower()
            if (
                (bw > 0 and bh > 0 and (bw < 200 or bh < 25))
                or label == "background"
                or any(term in label for term in _VQL_TERMINAL_LABEL_NOISE)
            ):
                map_target = _map_chat_target_capture_local(ide=canon, source=src_name)
                if map_target:
                    map_target = _finalize(map_target, method="map_fallback_after_bad_corner")
                    _log_vql_cursor_positioning_at_command(
                        map_target,
                        stage="vql_target_selection_jetbrains_map_fallback_bad_vql",
                        ide=canon,
                        source=src_name,
                        final_local=map_target.get("click_center", {}),
                        final_global=map_target.get("map_global"),
                        vql_file=src if isinstance(src, str) and str(src).endswith(".vql.json") else None,
                    )
                    return map_target
            corner = _finalize(corner, method="jetbrains_corner_heuristic")
            _log_vql_cursor_positioning_at_command(
                corner,
                stage="vql_target_selection_jetbrains_corner",
                ide=canon,
                source=src_name,
                final_local=corner.get("click_center", {}),
                vql_file=src if isinstance(src, str) and str(src).endswith(".vql.json") else None,
            )
            return corner
        map_target = _map_chat_target_capture_local(ide=canon, source=src_name)
        if map_target:
            map_target = _finalize(map_target, method="map_calibrated")
            _log_vql_cursor_positioning_at_command(
                map_target,
                stage="vql_target_selection_jetbrains_map",
                ide=canon,
                source=src_name,
                final_local=map_target.get("click_center", {}),
                final_global=map_target.get("map_global"),
                vql_file=src if isinstance(src, str) and str(src).endswith(".vql.json") else None,
            )
            return map_target
    resolve_chat_target = _import_imgl_targets("resolve_chat_target")
    if resolve_chat_target is not None:
        resolved = resolve_chat_target(els, source=src)
        return _finalize(resolved, method="imgl_resolve_chat_target")
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
    """Użyj VQL z foto do zlokalizowania edytora (otwarty plik), kliknij center dla focus, przygotuj do precyzyjnego edit via coords.

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


def _enrich_capture_meta_for_pointer(meta: dict[str, Any], source: str) -> dict[str, Any]:
    """Fill portal stream region/rotation when screenshot sidecar only has a 0,0 crop."""
    enriched = dict(meta or {})
    try:
        from vdisplay.capture.screencast_stream_meta import enrich_screencast_stream_meta

        enriched = enrich_screencast_stream_meta(enriched)
    except Exception:
        try:
            from vdisplay.control.screenshot_verify import enrich_screencast_stream_meta

            enriched = enrich_screencast_stream_meta(enriched)
        except Exception:
            pass

    region = enriched.get("region") if isinstance(enriched.get("region"), dict) else {}
    origin_x = int(region.get("x") or 0)
    origin_y = int(region.get("y") or 0)
    if origin_x == 0 and origin_y == 0:
        app_id = _ide_prompt_app_id(source if source in {"pycharm", "jetbrains", "idea"} else "pycharm")
        map_path = _resolve_ide_prompt_map(app_id)
        if map_path and os.path.isfile(map_path):
            try:
                with open(map_path) as f:
                    map_data = json.load(f)
                mcap = map_data.get("capture_meta") if isinstance(map_data.get("capture_meta"), dict) else {}
                if str(mcap.get("source") or mcap.get("monitor_name") or "") in {source, "", "DP-2"}:
                    for key in ("region", "rotation", "screencast_stream", "screencast_full_frame", "width", "height"):
                        if mcap.get(key) is not None:
                            enriched[key] = mcap[key]
            except Exception:
                pass
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
    return enriched


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
        elems = (map_data.get("elements") or {})
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
        from vdisplay.input.coords import global_point_to_capture_local
        meta = _enrich_capture_meta_for_pointer(_photo_capture_meta_for_source(source), source)
        region = (meta or {}).get("region") or {}
        cap_w = int(region.get("width") or 2048)
        cap_h = int(region.get("height") or 1280)
        for key in candidates:
            element = elems.get(key) if isinstance(elems, dict) else None
            if not isinstance(element, dict):
                continue
            click = element.get("click_point") or {}
            gx = int(click.get("x") or 0)
            gy = int(click.get("y") or 0)
            if gx <= 0 or gy <= 0:
                continue
            lx, ly = global_point_to_capture_local(gx, gy, meta)
            lx_i = int(lx)
            ly_i = int(ly)
            # Sane for chat composer on rotated DP-2 / bottom-right area: positive, not tiny y, not left panel.
            if ly_i < 0 or lx_i < 0:
                continue
            if ly_i < 700 or (ly_i > cap_h + 100):
                # still record but prefer better; if no better we'll take the first non-neg
                pass
            # Accept if y looks like bottom panel area for composer (or at least non-negative inside-ish bounds)
            if ly_i >= 0 and lx_i >= 0:
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
        # Last resort: take the first valid element even if y low (will get coord warning later)
        # But still refuse to return a negative local y (safer than feeding garbage coords to ydotool plan).
        for key in candidates:
            element = elems.get(key) if isinstance(elems, dict) else None
            if not isinstance(element, dict):
                continue
            click = element.get("click_point") or {}
            gx = int(click.get("x") or 0)
            gy = int(click.get("y") or 0)
            if gx <= 0 or gy <= 0:
                continue
            lx, ly = global_point_to_capture_local(gx, gy, meta)
            lx_i, ly_i = int(lx), int(ly)
            if ly_i < 0 or lx_i < 0:
                continue
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
        return None
    except Exception:
        return None


def _photo_vql_chat_input_candidates(layers: list[dict[str, Any]], *, limit: int = 8) -> list[dict[str, Any]]:
    cands: list[tuple[float, dict[str, Any]]] = []
    for layer in layers:
        if str(layer.get("role") or "").lower() != "input":
            continue
        cc = layer.get("click_center") or {}
        if not isinstance(cc, dict) or "x" not in cc or "y" not in cc:
            continue
        cx = int(cc.get("x") or 0)
        cy = int(cc.get("y") or 0)
        label = str(layer.get("label") or layer.get("text") or "").lower()
        bounds = layer.get("bounds") or layer.get("bbox") or {}
        bw = int(bounds.get("w") or bounds.get("width") or 0)
        bh = int(bounds.get("h") or bounds.get("height") or 0)
        area = bw * bh if bw > 0 and bh > 0 else 0
        # base corner score
        score = float(cy) + (400.0 if cx > 1400 else 0.0) + (200.0 if cx > 1100 else 0.0)
        if cy < 700:
            score -= 800.0
        # prefer larger reasonable composer inputs (chat fields are wide/tall enough, not tiny chrome)
        if area > 0:
            if bw >= 250 and bh >= 28:
                score += 500.0
            elif bw >= 200 and bh >= 25:
                score += 300.0
            elif bw < 180 or bh < 22:
                score -= 900.0
            elif bw < 200 or bh < 25:
                score -= 500.0
        # penalize generic UI chrome / terminal inputs
        if label in {"background", ""} and area > 0 and (bw < 200 or bh < 25):
            score -= 900.0
        if any(term in label for term in _VQL_TERMINAL_LABEL_NOISE):
            score -= 1200.0
        # extra heavy penalty for labels that look like the control terminal text / command history / env vars
        # (common when the screenshot captures the user's terminal running the drive commands)
        shell_pollution_tokens = ("KORU_", "DRY_RUN", "PREFER LLM", " --source", "po clear", "recznie vdisplay", "wpisz", "to do", "drive after", "Re-run", "audit-last", "cursor_positioning", "Explored", "passed", "Clear", "Gap Analysis", "Monitored", "screenshot", "act/", "ts - Cursor", "File Edit", "Go Run Terminal", "Publish v", "247K", "automation-gap", "Path(str(vql_path)", "imgl_path", "sidecar older", "reasons.append", "You have folder", "faster responses")
        if any(tok.lower() in label for tok in shell_pollution_tokens):
            score -= 1500.0
        cands.append(
            (
                score,
                {
                    "id": layer.get("id"),
                    "role": layer.get("role"),
                    "label": label[:80],
                    "click_center": {"x": cx, "y": cy},
                    "bounds": bounds,
                },
            )
        )
    cands.sort(key=lambda item: -item[0])
    return [item[1] for item in cands[:limit]]


def _validate_chat_coords_for_ide(
    *,
    x: int,
    y: int,
    ide: str,
    target: dict[str, Any],
    is_code_edit: bool = False,
) -> list[str]:
    """Heuristic warnings when VQL-derived chat coords look like editor/toolbar, not composer."""
    warnings: list[str] = []
    canon = _canonical_ide(ide)
    src = str(target.get("source") or "")
    if src in {"vql-analysis-fallback", ""} or "fallback" in str(target.get("note") or "").lower():
        warnings.append("target_not_from_live_vql_layers_using_fallback_center")
    bounds = target.get("bounds") or {}
    bw = int(bounds.get("w") or bounds.get("width") or 0)
    bh = int(bounds.get("h") or bounds.get("height") or 0)
    if bw > 0 and bh > 0 and (bw < 150 or bh < 25):
        warnings.append(f"bounds_{bw}x{bh}_too_small_for_chat_composer")
    label = str(target.get("label") or target.get("note") or "").lower()
    if label == "background":
        warnings.append("label_background_not_chat_composer")
    if any(term in label for term in {".py", ".ts"}):
        warnings.append(f"label_{label}_looks_like_code_file_not_chat")
    if label.startswith("session") or label.startswith("metadata"):
        warnings.append(f"label_{label}_looks_like_terminal_not_chat")
    if "vdisplay_metadata_dir" in label.replace("_", "").replace("=", "").replace(".", ""):
        warnings.append(f"label_{label}_looks_like_env_var_not_chat")
    shell_pollution_tokens = ("KORU_", "DRY_RUN", "PREFER LLM", " --source", "po clear", "recznie", "wpisz", "to do", "drive after", "Re-run", "audit", "cursor_positioning", "Explored", "passed", "Clear", "Gap Analysis", "Monitored", "screenshot", "act/", "ts - Cursor", "File Edit", "Go Run Terminal", "Publish v", "247K", "automation-gap")
    if any(tok.lower() in label for tok in shell_pollution_tokens):
        warnings.append("label_looks_like_terminal_command_history_or_env_pollution")
    if not is_code_edit and canon in {"jetbrains", "pycharm", "idea"}:
        if y < 850:
            warnings.append(f"chat_local_y={y}_below_850_likely_editor_not_bottom_right_composer")
        if x < 1100:
            warnings.append(f"chat_local_x={x}_below_1100_likely_left_panel_not_chat_corner")
    if "pycharm/jb" in label and y < 850:
        warnings.append("breadcrumb_pycharm_jb_label_but_y_too_high_for_chat_composer")
    return warnings


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
    meta_for_val = load_vql_metadata(allow_stale=True)
    validation = vql_validation or target.get("vql_validation") or validate_vql_chat_target(
        target,
        ide=ide,
        meta=meta_for_val,
        capture_mismatch=capture_mismatch,
        selection_method=str(target.get("selection_method") or ""),
        is_code_edit=is_code_edit,
        x=x,
        y=y,
    )
    warnings = list(validation.get("coord_warnings") or [])
    validation_errors = list(validation.get("validation_errors") or [])
    if validation_errors:
        warnings.extend(validation_errors)
    if capture_mismatch:
        warnings.append("capture_ide_mismatch")
        if llm_decision:
            warnings.append("llm_refined_on_unconfirmed_ide_capture")
    vql_file = target.get("source")
    vql_mtime: str | None = None
    if isinstance(vql_file, str) and os.path.isfile(vql_file):
        try:
            vql_mtime = datetime.datetime.fromtimestamp(os.path.getmtime(vql_file)).isoformat()
        except Exception:
            pass

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
    capture_title = validation.get("capture_title") or (capture_provenance or {}).get("capture_title")

    commands: list[dict[str, Any]] = [
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
        "inference_ok": bool(validation.get("ok"))
        and capture_mismatch is None
        and bool((capture_provenance or {}).get("capture_confirmed")),
        "capture_confirmed": bool((capture_provenance or {}).get("capture_confirmed"))
        and capture_mismatch is None
        and bool(validation.get("ok")),
        "capture_title": capture_title,
        "vql_element_size_ok": validation.get("vql_element_size_ok"),
        "app_match": validation.get("app_match"),
        "vql_validation": validation,
        "used_map_because_mismatch_or_bad_element": validation.get(
            "used_map_because_mismatch_or_bad_element"
        ),
        "capture_provenance": capture_provenance,
    }


def _jetbrains_chat_corner_target_from_layers(
    layers: list[dict[str, Any]],
    *,
    source: str | None = None,
) -> dict[str, Any] | None:
    """Prefer bottom-right composer inputs for JetBrains AI chat on rotated DP-2."""
    cands = _photo_vql_chat_input_candidates(layers, limit=1)
    if not cands:
        return None
    best = cands[0]
    cc = best.get("click_center") or {}
    if int(cc.get("y") or 0) < 850:
        return None
    bounds = best.get("bounds") or {}
    bw = int(bounds.get("w") or bounds.get("width") or 0)
    bh = int(bounds.get("h") or bounds.get("height") or 0)
    if bw > 0 and bh > 0 and (bw < 200 or bh < 25):
        return None
    label = str(best.get("label") or "").lower()
    if label == "background":
        return None
    if any(term in label for term in _VQL_TERMINAL_LABEL_NOISE):
        return None
    shell_pollution_tokens = ("KORU_", "DRY_RUN", "PREFER LLM", " --source", "po clear", "recznie", "wpisz", "to do", "drive after", "Re-run", "audit", "cursor_positioning", "Explored", "passed", "Clear", "Gap Analysis", "Monitored", "screenshot", "act/", "ts - Cursor", "File Edit", "Go Run Terminal", "Publish v", "247K", "automation-gap")
    if any(tok.lower() in label for tok in shell_pollution_tokens):
        return None
    return {
        "click_center": cc,
        "id": best.get("id"),
        "role": best.get("role") or "input",
        "bounds": best.get("bounds"),
        "note": f"JetBrains chat corner heuristic (bottom-right input; {source})",
        "source": source,
    }


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


def _ydotool_click_capture_local(*, x: int, y: int, source: str) -> dict[str, Any]:
    """Direct ydotool move+click when vdisplay vision point click fails."""
    try:
        from vdisplay.input.coords import global_pointer_coords
        from vdisplay.input.linux_ydotool import LinuxYdotoolInput

        capture_meta = _enrich_capture_meta_for_pointer(_photo_capture_meta_for_source(source), source)
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

    if _dry_run() or not vdisplay_available():
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

    # After AT-SPI window focus, try set_value on the focused element first (GNOME Wayland).
    click_target = (focus_res or {}).get("click_res") or {}
    element_id = click_target.get("element_id")
    target_caps = ((click_target.get("target") or {}).get("capabilities") or {})
    if focus_ok and element_id and target_caps.get("text_write"):
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
                return result
        except Exception as exc:
            result["atspi_error"] = str(exc)

    click_res = None
    if must_click:
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
            click_res = ydotool_click
            result["click_res"] = click_res
            logger.info(
                "VQL_CHAT_WRITE_CLICK_OK local=(%s,%s) global=(%s,%s) method=%s",
                x,
                y,
                ydotool_click.get("x"),
                ydotool_click.get("y"),
                ydotool_click.get("method"),
            )
        else:
            logger.warning(
                "VQL_CHAT_WRITE_CLICK_FAILED local=(%s,%s) error=%s",
                x,
                y,
                ydotool_click.get("error"),
            )
    if click_res is None and not focus_ok:
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
    llm_decision: dict[str, Any] | None = None
    canon = _canonical_ide(ide)

    use_llm_vision = os.environ.get("KORU_VDISPLAY_LLM_VISION_DECISION", "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    if not (
        use_llm_vision
        and image_path
        and os.path.exists(image_path)
        and call_openrouter_vision is not None
    ):
        return x, y, None

    try:
        with open(image_path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode("ascii")
        data_url = f"data:image/png;base64,{b64}"

        img_w, img_h = 2048, 1280
        try:
            from PIL import Image

            with Image.open(image_path) as img:
                img_w, img_h = img.size
        except Exception:
            meta = _photo_capture_meta_for_source(source)
            img_w = int(meta.get("width") or img_w)
            img_h = int(meta.get("height") or img_h)

        layers, _src = _photo_vql_elements()
        candidates = _photo_vql_chat_input_candidates(layers, limit=8)
        map_hint = _map_chat_target_capture_local(ide=canon, source=source) if canon in {"jetbrains", "pycharm", "idea"} else None

        vql_excerpt = json.dumps(
            {
                "id": target.get("id"),
                "role": target.get("role"),
                "click_center": target.get("click_center"),
                "bounds": target.get("bounds"),
                "note": target.get("note"),
            }
        )
        meta_for_title = load_vql_metadata(allow_stale=True)
        capture_title = _capture_title_from_meta(meta_for_title) or "unknown"
        mismatch = _photo_vql_ide_capture_mismatch(ide=canon) if canon in {"jetbrains", "pycharm", "idea"} else None
        task_hint = (
            "Focus the JetBrains/PyCharm AI chat composer input (bottom-right panel, placeholder like 'Ask' or empty message box). "
            "Do NOT click the main code editor, terminal, or file tabs."
            if canon in {"jetbrains", "pycharm", "idea"}
            else "Focus the IDE chat/composer input to type the user prompt."
        )
        reject_rules = (
            "REJECT and lower confidence if: capture title does not match the expected IDE; "
            "element width<200 or height<25; label is 'background' or a terminal/file tab (.py, session, vdisplay); "
            "coords look like main editor (y<850 on DP-2) not bottom-right chat panel. "
            "Only confirm when the element matches the expected IDE and looks like a real Ask/Prompt composer in the image."
        )
        text_prompt = (
            f"Current user task/prompt: {prompt}\n\n"
            f"Capture foreground window title: {capture_title!r}\n"
            f"Expected IDE: {canon}. Capture IDE mismatch: {bool(mismatch)}.\n"
            f"Attached screenshot size: {img_w}x{img_h} pixels (origin top-left).\n"
            f"Monitor/source: {source}.\n"
            f"{task_hint}\n"
            f"{reject_rules}\n\n"
            f"Primary VQL target from OCR/layout analysis: {vql_excerpt}\n\n"
            f"Other input candidates (PNG-local coords): {json.dumps(candidates)}\n\n"
            f"Map-calibrated chat hint (if present): {json.dumps(map_hint.get('click_center') if map_hint else None)}\n\n"
            f"Return the SINGLE best click_center {{x, y}} IN PNG PIXEL COORDINATES (0..{img_w - 1}, 0..{img_h - 1}) "
            f"inside the editable chat input field.\n"
            f"Also provide strategy and confidence. Return ONLY JSON: "
            f'{{"click_center": {{"x": int, "y": int}}, "strategy": str, "confidence": float, "reason": str}}'
        )

        llm_res = call_openrouter_vision(text_prompt, data_url)
        if not llm_res.ok:
            return x, y, None
        raw = llm_res.content.strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1].rsplit("\n", 1)[0] if "\n" in raw else raw.strip("`")
        decision = json.loads(raw)
        if not isinstance(decision, dict) or "click_center" not in decision:
            return x, y, None
        conf = float(decision.get("confidence", 0.0))
        if conf < 0.35:
            return x, y, None
        new_cc = decision["click_center"]
        if not isinstance(new_cc, dict) or "x" not in new_cc or "y" not in new_cc:
            return x, y, None
        x = max(0, min(int(new_cc["x"]), img_w - 1))
        y = max(0, min(int(new_cc["y"]), img_h - 1))
        if canon in {"jetbrains", "pycharm", "idea"} and y < 850:
            fallback = candidates[0]["click_center"] if candidates else (map_hint or {}).get("click_center")
            if isinstance(fallback, dict) and fallback.get("x") is not None:
                x = int(fallback["x"])
                y = int(fallback["y"])
                decision["llm_coord_adjusted"] = True
                decision["reason"] = (
                    str(decision.get("reason") or "")
                    + " (adjusted to bottom-right chat candidate — LLM y too high on screen)"
                ).strip()
        llm_decision = decision
    except Exception:
        return x, y, None
    return x, y, llm_decision


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

    To realizuje "użyć VQL do 'zobaczenia' otwartego pliku w edytorze i precyzyjnego edit via coords" (następny task z analizy).
    Dla is_code_edit=True używa editor target (np. window_0 lub main panel z foto VQL).
    Dla chat (default) używa chat panel.

    Optional LLM vision layer (enable with KORU_VDISPLAY_LLM_VISION_DECISION=1):
    If .env has OPENROUTER_API_KEY and LLM_MODEL (vision model e.g. openrouter/google/gemini-3.1-flash-image-preview),
    we send base64(image_path) + VQL target excerpt + the prompt to the model.
    LLM should return JSON: {"click_center": {"x": int, "y": int}, "strategy": str, "confidence": float, "reason": str}.
    If successful and confidence reasonable, the LLM's click_center (and strategy) overrides the pure VQL one for this call.
    This adds "LLM decides exact coords/strategy on top of photo VQL" as additional layer.
    Always falls back to the VQL-derived coords if no key, no image_path, call fails, or low confidence.
    IDE independent (dane z foto, nie z pluginu).
    """
    mismatch = _photo_vql_ide_capture_mismatch(ide=ide) if ide and ide != "auto" else None
    use_llm_vision = os.environ.get("KORU_VDISPLAY_LLM_VISION_DECISION", "").strip().lower() in {"1", "true", "yes", "on"}

    meta_probe = load_vql_metadata()
    if meta_probe.get("error") and not _dry_run():
        stale_only = bool(meta_probe.get("stale_skipped"))
        session_active = _autonomy_session.active_session_dir() is not None
        if (stale_only or session_active) and not _dry_run():
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

    # Strict match mainly for is_code_edit (precise editor file edits need correct capture of the open file).
    # Chat on JetBrains also requires a matching capture unless explicitly overridden — LLM vision cannot
    # reliably locate PyCharm chat when the screenshot shows Cursor (wrong window layer / VQL inputs).
    if (
        mismatch
        and not _dry_run()
        and _canonical_ide(ide) in {"jetbrains", "pycharm", "idea"}
        and not _allow_actuation_on_capture_mismatch()
    ):
        err = {
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
        session = _autonomy_session.active_session_dir()
        if session is not None:
            _autonomy_session.persist_autonomy_phase(session, "decide", "ide_capture_blocked", err)
        return err

    if is_code_edit:
        t = get_vql_editor_target_from_photo()
        target_desc = "editor/open-file"
    else:
        t = get_vql_chat_target_from_photo(ide=ide)
        target_desc = "chat"

    # For JetBrains on DP-2 (rotated, often empty VQL layers or title mismatch from observe),
    # get_vql... deliberately returns a calibrated map target (e.g. "prompt" or "ai-chat-input").
    # The map is the trusted source for this IDE+monitor. Clear the observe-level mismatch
    # so that actuation (move/click/paste + --submit) is allowed and inference_ok reflects
    # the reliable map path rather than blocking the user drive. The plan/warnings still
    # record "used_map_because_mismatch_or_bad_element" + selection_method for full audit.
    canon_for_map = _canonical_ide(ide)
    if canon_for_map in {"jetbrains", "pycharm", "idea"}:
        tid = str(t.get("id") or "")
        sel = str(t.get("selection_method") or t.get("vql_validation", {}).get("selection_method") or "")
        if (
            _allow_actuation_on_capture_mismatch()
            and (
                tid.startswith("map:")
                or sel.startswith("map_")
                or sel
                in {
                    "map_calibrated_on_mismatch",
                    "map_calibrated_on_empty_vql",
                    "map_fallback_after_bad_corner",
                    "map_calibrated",
                }
            )
        ):
            mismatch = None  # map-only fallback explicitly allowed
            t["_map_cleared_mismatch_for_actuation"] = True

    if image_path is None:
        image_path = _resolve_photo_png_path_from_vql(source=source)

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

    if is_code_edit:
        if llm_decision:
            focus_res = move_mouse_to_vql_target_and_focus_keyboard(t, ide=ide, source=source)
        else:
            focus_res = click_editor_via_photo_vql(ide=ide, source=source)
    else:
        focus_res = move_mouse_to_vql_target_and_focus_keyboard(t, ide=ide, source=source)

    edit_res = {"ok": False, "error": "not attempted"}

    if _dry_run():
        edit_res = {
            "ok": True,
            "dry_run": True,
            "message": f"DRY: precise edit at VQL coords ({x},{y}) from foto target {target_desc}",
            "value": prompt,
        }
    elif vdisplay_available():
        focus_ok = bool(focus_res.get("ok"))
        try:
            edit_res = _type_text_at_vql_coords(
                prompt,
                x=int(x),
                y=int(y),
                source=source,
                ide=ide,
                focus_ok=focus_ok,
                focus_res=focus_res,
                force_point_click=True,
                vql_target=t,
                command_plan=command_plan,
            )
        except Exception as exc:
            edit_res = {"ok": False, "error": str(exc)}

        if not edit_res.get("ok"):
            map_fallback = _photo_vql_map_paste_fallback(prompt, ide=ide)
            if map_fallback and map_fallback.get("ok"):
                edit_res = map_fallback
                edit_res["photo_vql_map_fallback"] = True

    combined_ok = bool(edit_res.get("ok", False))
    is_jetbrains_map = str((t or {}).get("id") or "").startswith("map:") and _canonical_ide(ide) in {"jetbrains", "pycharm", "idea"}
    map_mismatch_allowed = is_jetbrains_map and _allow_actuation_on_capture_mismatch()
    if mismatch and not _allow_actuation_on_capture_mismatch() and not map_mismatch_allowed:
        combined_ok = False
    if not command_plan.get("inference_ok", True) and not _allow_actuation_on_capture_mismatch() and not _dry_run() and not map_mismatch_allowed:
        combined_ok = False

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
    ):
        global_coords = command_plan.get("final_global") or {}
        gx = global_coords.get("x")
        gy = global_coords.get("y")
        map_path = None
        if str(t.get("id") or "").startswith("map:"):
            src = t.get("source")
            if isinstance(src, str) and src.endswith(".json"):
                map_path = src
        verification = verify_chat_text_visible(
            prompt,
            ide=ide,
            chat_x=int(gx) if gx is not None else int(x),
            chat_y=int(gy) if gy is not None else int(y),
            map_path=map_path,
        )
        if verification.get("verified") is False:
            combined_ok = False

    submitted = False
    submit_result: dict[str, Any] | None = None
    if submit and combined_ok and not _dry_run():
        import time

        time.sleep(float(os.environ.get("KORU_VDISPLAY_SUBMIT_DELAY_S", "0.25")))
        submit_result = _photo_vql_submit_chat(ide=ide, source=source)
        submitted = bool(submit_result and submit_result.get("ok"))
        combined_ok = submitted

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

    return combined


def move_mouse_to_vql_target_and_focus_keyboard(target: dict | None = None, *, ide: str = "auto", source: str = "DP-1") -> dict:
    """Na podstawie foto screen: zlokalizuj okno chat (via get_vql_chat_target_from_photo), przenies mysz na click_center, click (dla focus keyboard).

    Dziala niezaleznie od IDE (jetbrains -> cursor itp.): VQL z aktualnego zrzutu ekranu daje centers/layers/data_locations.
    Po click na panel/input area, IDE dostaje keyboard focus w tym miejscu (chat composer lub editor).

    Uzywane w koru autonomy / send_chat (gdy KORU_VDISPLAY_USE_VQL_MOUSE_FOCUS=1) + recznie dla STARTER etc.
    Real action via vdisplay _control_click (vision + point) + _control_focus; dziala gdy agent/keeper aktywny na --source.
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
    vql_file = target.get("source") if isinstance(target.get("source"), str) and target.get("source", "").endswith(".vql.json") else None
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
            "message": f"DRY-RUN: mouse move to chat VQL center ({x},{y}) + click -> keyboard focus in {ide} (from current screen foto)",
        })
        return result

    # Real action: try to position mouse at exact VQL photo coords and click (to focus chat/input area).
    # The coords come from the capture frame (e.g. DP-1 portal stream local 0-2048x1280).
    # We try a few payload shapes because raw point clicks on multi-stream portal captures can be sensitive to backend/source.
    # We always also ensure window-level focus for keyboard.
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

    if click_res is not None or focus_res is not None:
        click_ok = bool(click_res.get("ok", True)) if isinstance(click_res, dict) else (click_res is not None)
        focus_ok = isinstance(focus_res, dict) and focus_res.get("ok", True)
        # Treat as success for the "keyboard focus" goal if window focus worked (brings kb to the IDE).
        # Mouse click at precise photo VQL center is attempted for the "przeniesiona mysz" part.
        # If low-level point click on the portal stream is not confirming, the coords are still the correct ones from the foto.
        overall_ok = focus_ok or click_ok
        result.update({
            "ok": overall_ok,
            "message": f"Photo VQL target used ({x},{y} from {target.get('id')}). Mouse click at chat center from screen photo attempted; window focus for keyboard. ide={ide}. (Point click may need fresh screencast --source {source} or vision-assisted click.)",
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
        bbox = layer.get("bbox") or {}
        center = layer.get("click_center") or layer.get("center") or {}
        if not center and isinstance(bbox, dict):
            w = int(bbox.get("w") or bbox.get("width") or 0)
            h = int(bbox.get("h") or bbox.get("height") or 0)
            if w > 0 and h > 0:
                center = {
                    "x": int(bbox.get("x") or 0) + w // 2,
                    "y": int(bbox.get("y") or 0) + h // 2,
                }
        ui.append(
            {
                "id": layer.get("id"),
                "role": layer.get("kind") or layer.get("role"),
                "label": layer.get("text") or layer.get("label"),
                "bounds": bbox,
                "click_center": center,
                "metadata": {k: layer.get(k) for k in ("confidence", "location") if k in layer},
            }
        )
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


def load_vql_metadata(path: str | None = None, *, allow_stale: bool = False) -> dict:
    """Load VQL metadata for decide/act. Skips stale sidecars unless ``allow_stale=True``.

    During an autonomy session only ``.vdisplay/YYYY-MM-DD/.../observe/capture.png.vql.json`` is used.
    """
    candidates = _get_vql_candidates(path)
    stale_tried: list[dict[str, Any]] = []
    for cand in candidates:
        try:
            resolved = _resolve_vql_candidate(cand)
            if not resolved:
                continue
            cand = resolved
            if not os.path.exists(cand):
                continue
            png_path = _png_path_for_vql_sidecar(cand)
            if not allow_stale:
                stale, freshness = _autonomy_session.vql_sidecar_is_stale(
                    Path(cand),
                    png_path,
                    layer_count=_main_vql_layer_count(cand),
                )
                if stale:
                    stale_tried.append({"path": cand, **freshness})
                    continue
            with open(cand) as f:
                data = json.load(f)
            # Normalize various VQL structures (analysis, fresh capture from screenshot, imgl, etc.)
            if "ui_elements" in data and data.get("ui_elements"):
                data["_source"] = cand
                if png_path and png_path.is_file():
                    data["_png"] = str(png_path)
                    data["_freshness"] = {"age_s": round(__import__("time").time() - png_path.stat().st_mtime, 2)}
                if "layers" not in data:
                    data["layers"] = data["ui_elements"]
                return _with_embedded_capture_validation(data, data)
            if "elements" in data and isinstance(data.get("elements"), list) and data["elements"]:
                res = _parse_fresh_vql_elements(data, cand)
                if png_path and png_path.is_file():
                    res["_png"] = str(png_path)
                return _with_embedded_capture_validation(res, data)
            sidecar_layers = _layers_from_vdisplay_sidecar(data)
            if not sidecar_layers:
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
                        sidecar_layers = imgl_layers
                        cand = imgl_source or cand
            if sidecar_layers:
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
            if "vql" in data and isinstance(data.get("vql"), dict):
                prog = data["vql"].get("program", data["vql"])
                if isinstance(prog, dict):
                    prog["_source"] = cand
                    if "layers" not in prog and "ui_elements" in prog:
                        prog["layers"] = prog["ui_elements"]
                    return prog
            if "screen_context" in data or "metadata" in data:
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
            if isinstance(data.get("program"), (str, dict)) and "elements" not in data:
                data["_source"] = cand
                if "layers" not in data:
                    data["layers"] = data.get("ui_elements", [])
                return data
            data["_source"] = cand
            if "layers" not in data:
                data["layers"] = data.get("ui_elements", [])
            return data
        except Exception:
            continue
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
    if best:
        if best in candidates:
            candidates.remove(best)
        candidates.insert(0, best)
    return candidates


def _parse_fresh_vql_elements(data: dict, cand: str) -> dict:
    """Helper extracted to reduce CC in load_vql_metadata (autonomous refactor for high-CC split)."""
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
    res = {"ui_elements": ui_els, "layers": ui_els, "element_count": data.get("element_count", len(ui_els)), "by_role": data.get("by_role", {}), "scene": data.get("scene"), "_source": cand, "raw_fresh": True}
    return res


def get_vql_target(ide: str, *, role: str | None = None, name_contains: str | None = None, label: str | None = None) -> dict | None:
    """Select target from loaded VQL ui_elements/layers by role or name/label.
    Returns dict with click_center, bounds, id for use in act (mouse nav).
    Used to close observe -> decide -> act gap when vision stub or no map.
    """
    vql = load_vql_metadata()
    targets = vql.get("ui_elements") or vql.get("layers") or []
    for t in targets:
        if role and t.get("role") != role:
            continue
        if name_contains and name_contains.lower() not in str(t.get("label", "")).lower() and name_contains.lower() not in str(t.get("id", "")).lower():
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
    "get_vql_target",
    "resolve_click_for_frame",
    # photo screen VQL based (from .vdisplay/*koru-cont*.vql.json + analysis): locate chat + mouse move + kb focus (IDE independent)
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
