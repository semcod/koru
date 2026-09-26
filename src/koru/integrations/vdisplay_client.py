"""vdisplay semantic control fallback for koru autonomous / coru drive.

When simplified control paths fail (plugin socket, blind wtype/ydotool, coordinate
injectors), koru can delegate to vdisplay's control plane for full semantic
automation: AT-SPI / Playwright / terminal / X11 / vision routing with verify.
"""

from __future__ import annotations

import base64  # noqa: F401
import logging
import os
import urllib.error
import urllib.request
from typing import Any

logger = logging.getLogger(__name__)

from koru.integrations import autonomy_session as _autonomy_session  # noqa: E402
from koru.integrations.photo_vql_config import llm_vision_enabled  # noqa: E402,F401
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
        jetbrains_chat_corner_target_from_layers as _jetbrains_chat_corner_target_from_layers,  # noqa: F401
    )
    from koru.integrations.photo_vql_target import (
        jetbrains_chat_target_from_surface as _jetbrains_chat_target_from_surface,  # noqa: F401
    )
    from koru.integrations.photo_vql_target import (
        photo_vql_chat_input_candidates as _photo_vql_chat_input_candidates,  # noqa: F401
    )
    from koru.integrations.photo_vql_target import (
        vql_candidates_polluted as _vql_candidates_polluted,  # noqa: F401
    )
    from koru.integrations.photo_vql_validation import (
        VSCODE_FAMILY_TOP_CHAT_IDES,  # noqa: F401
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
from koru.integrations.photo_vql_guard import (  # noqa: E402,I001
    CaptureGuard,  # noqa: F401
)
from koru.integrations.photo_vql_guard import (  # noqa: E402
    allow_actuation_on_capture_mismatch as _allow_actuation_on_capture_mismatch,  # noqa: F401
)
from koru.integrations.photo_vql_guard import (  # noqa: E402
    allow_prepare_map_on_mismatch as _allow_prepare_map_on_mismatch,  # noqa: F401
)
from koru.integrations.photo_vql_guard import (  # noqa: E402
    allow_prepare_surface_on_capture_error as _allow_prepare_surface_on_capture_error,  # noqa: F401
)
from koru.integrations.photo_vql_guard import (  # noqa: E402
    competing_ide_label_from_warning as _competing_ide_label_from_warning,  # noqa: F401
)
from koru.integrations.photo_vql_guard import (  # noqa: E402
    drive_blocked_on_capture_mismatch as _drive_blocked_on_capture_mismatch,  # noqa: F401
)
from koru.integrations.photo_vql_guard import (  # noqa: E402
    ide_mismatch_allowed as _ide_mismatch_allowed,  # noqa: F401
)
from koru.integrations.photo_vql_validation import (  # noqa: E402
    capture_title_from_meta as _capture_title_from_meta,  # noqa: F401
)
from koru.integrations.photo_vql_validation import (  # noqa: E402
    validate_chat_coords_for_ide as _validate_chat_coords_for_ide,  # noqa: F401
)
from koru.integrations.photo_vql_validation import (  # noqa: E402
    validate_vql_chat_target,
)
from koru.integrations.photo_vql_validation import (  # noqa: E402
    window_titles_from_vql_meta as _window_titles_from_vql_meta,  # noqa: F401
)
from koru.integrations.vdisplay.env_session import (  # noqa: E402
    clear_stale_observe_session_env,  # noqa: F401
    dry_run_enabled as _dry_run,  # noqa: F401
    session_type as _session_type,  # noqa: F401
    sync_prepare_capture_flags_to_env,  # noqa: F401
)


from koru.integrations.vdisplay_readiness import (  # noqa: E402
    _VDISPLAY_DIRECT,
    _VDISPLAY_IMPORT_ERROR,
    _ensure_real_vdisplay_on_path,
    _ensure_vdisplay_runtime as _vr_ensure_vdisplay_runtime,
    _load_vdisplay_control as _vr_load_vdisplay_control,
    _real_vdisplay_src,
    _reload_vdisplay_direct as _vr_reload_vdisplay_direct,
    _vdisplay_control,  # noqa: F401
)

_ensure_real_vdisplay_on_path()


def _load_vdisplay_control() -> bool:
    if not _VDISPLAY_DIRECT:
        return False
    return _vr_load_vdisplay_control()


def _reload_vdisplay_direct() -> bool:
    return _load_vdisplay_control()


def _ensure_vdisplay_runtime() -> bool:
    if _VDISPLAY_DIRECT:
        return True
    from koru.deps_autorepair import ensure_vdisplay_runtime

    if not ensure_vdisplay_runtime(label="koru drive"):
        return False
    return _reload_vdisplay_direct()

# Optional: LLM vision decision layer on top of photo VQL (enable via env + .env OpenRouter key)
try:
    from koru.autonomy_strategy.openrouter import call_openrouter_vision
except Exception:
    call_openrouter_vision = None





from koru.integrations.vdisplay_readiness import (  # noqa: E402
    _agent_url,
    _canonical_ide,  # noqa: F401
    _probe_agent,
    vdisplay_available as _vr_vdisplay_available,
    vdisplay_missing_message as _vr_vdisplay_missing_message,
)


def vdisplay_available() -> bool:
    return _vr_vdisplay_available(
        direct=_VDISPLAY_DIRECT,
        load_control=_load_vdisplay_control,
        ensure_runtime=_ensure_vdisplay_runtime,
        agent_url_fn=_agent_url,
        probe_agent_fn=_probe_agent,
    )


def vdisplay_missing_message() -> str:
    return _vr_vdisplay_missing_message(
        agent_url_fn=_agent_url,
        import_error=_VDISPLAY_IMPORT_ERROR,
    )


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


from koru.integrations.vdisplay.control_policy import (  # noqa: E402,I001
    _photo_vql_code_edit_enabled,  # noqa: F401
    _send_chat_os_injector_enabled,  # noqa: F401
    _trusted_visual_target_id,  # noqa: F401
)
from koru.integrations.vdisplay_readiness import (  # noqa: E402
    _IDE_DEFAULT_SOURCE,  # noqa: F401
    _capture_matches_requested_ide as _vr_capture_matches_requested_ide,  # noqa: F401
    _prefer_photo_vql_chat as _vr_prefer_photo_vql_chat,  # noqa: F401
    _vdisplay_source as _vr_vdisplay_source,  # noqa: F401
    simplified_control_likely_insufficient,
    vdisplay_fallback_enabled as _vr_vdisplay_fallback_enabled,
)


def vdisplay_fallback_enabled(*, ide: str | None = None, plugin_connected: bool = False) -> bool:
    return _vr_vdisplay_fallback_enabled(
        ide=ide,
        plugin_connected=plugin_connected,
        available_fn=vdisplay_available,
    )







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


from koru.integrations.vdisplay_readiness import (  # noqa: E402
    _abort_on_desktop_probe_fail,  # noqa: F401
    _annotate_prepare_drive_readiness as _vr_annotate_prepare_drive_readiness,  # noqa: F401
    _map_source_mismatch_actuation_allowed,  # noqa: F401
    _resolve_vdisplay_source_for_ide as _vr_resolve_vdisplay_source_for_ide,  # noqa: F401
    _vdisplay_source_for_ide as _vr_vdisplay_source_for_ide,  # noqa: F401
)










from koru.integrations.vdisplay.photo_vql_meta import (  # noqa: E402,I001
    COMPETING_IDE_WINDOW_TOKENS as _COMPETING_IDE_WINDOW_TOKENS,  # noqa: F401
    IDE_WINDOW_TITLE_TOKENS as _IDE_WINDOW_TITLE_TOKENS,  # noqa: F401
    _capture_validation_from_meta,  # noqa: F401
    _photo_vql_overlay_labels,  # noqa: F401
    _photo_vql_portal_actor_detected,  # noqa: F401
    _photo_vql_share_prompt_detected,  # noqa: F401
    _photo_vql_system_overlay_warning,  # noqa: F401
    _type_text_plan_validation_warnings,  # noqa: F401
    photo_vql_capture_validation_failed_warning,  # noqa: F401
    photo_vql_expected_title_tokens,  # noqa: F401
    photo_vql_ide_window_warning,  # noqa: F401
    photo_vql_title_mismatch_warning,  # noqa: F401
)

# Split-out responsibility modules (ticket-236, the nxdo_discovery pattern):
# definitions moved verbatim; these re-export bindings keep every historical
# `from koru.integrations.vdisplay_client import X` and facade-level
# monkeypatch target working. Moved code reads them back through _vdc().
from koru.integrations.vdisplay.source_policy import (  # noqa: E402,F401,I001
    _capture_matches_requested_ide, _prefer_photo_vql_chat, _vdisplay_source,
    _annotate_prepare_drive_readiness, _resolve_vdisplay_source_for_ide, _vdisplay_source_for_ide,
    _prefer_ide_prompt_over_photo_vql, _auto_ide_control_enabled, _auto_open_ide_enabled,
)
from koru.integrations.vdisplay.vql_sidecar import (  # noqa: E402,F401,I001
    _photo_vql_metadata_root, _capture_confirmed_from_meta, _capture_provenance,
    _photo_vql_capture_validation_failed_warning, _photo_vql_expected_title_tokens, _photo_vql_title_mismatch_warning,
    _photo_vql_ide_window_warning, _photo_vql_ide_capture_mismatch, _observe_vql_sidecar_path,
    _annotate_png_artifact_state, _photo_png_from_vql_sidecar_path, _photo_png_from_vql_metadata,
    _resolve_photo_png_path_from_vql, _resolve_photo_png_path, _photo_vql_refresh_mode,
    photo_vql_sidecar_needs_refresh, _photo_vql_refresh_dry_run_out, _photo_vql_refresh_screenshot,
    _photo_vql_reload_sidecar_meta, _photo_vql_observe_when_empty, _photo_vql_refresh_annotate_observe,
    _photo_vql_refresh_finalize_out, _photo_vql_refresh_context, _photo_vql_refresh_observe_if_empty,
    _photo_vql_refresh_capture, _photo_vql_refresh_stale_out, refresh_photo_vql_sidecar,
    _vdisplay_capture_failure_hint, _refresh_vql_sidecar_via_vdisplay_observe,
)
from koru.integrations.vdisplay.imgl_loader import (  # noqa: E402,F401,I001
    _real_imgl_src, _ensure_real_imgl_on_path, _vdisplay_cli_candidates,
    _vdisplay_cli_path, _vdisplay_observe_python_candidates, _vdisplay_subprocess_env,
    _import_imgl_targets, _import_imgl_target_via_stdlib, _load_light_module,
    _install_imgl_source_packages, _import_imgl_target_from_source,
)
from koru.integrations.vdisplay.ide_control import (  # noqa: E402,F401,I001
    _focus_window_xdotool, _focus_window_xdotool_for_ide, _focus_window_gnome_shell,
    _focus_window_gnome_shell_for_ide, _click_map_region_center, _raise_alt_tab_enabled,
    _alt_tab_window_cycle, _attempt_focus_recovery_capture, _map_raise_targets_for_ide,
    _map_interior_targets_for_ide, _dismiss_gnome_overview, _ide_control_resolve_map,
    _ide_control_open_ide, _ide_control_raise_window, _ide_control_region_raise,
    _ide_control_alt_tab, _ide_control_window_focus, _ide_control_focus_fallback,
    _ide_control_focus_interior, _ide_control_outcome_flags, _ide_control_finalize_result,
    ensure_vdisplay_ide_control,
)
from koru.integrations.vdisplay.drive_prepare import (  # noqa: E402,F401,I001
    _prepare_photo_vql_map_mismatch, _prepare_photo_vql_probe_abort, _prepare_photo_vql_out_skeleton,
    _prepare_photo_vql_ide_control_attempt, _prepare_photo_vql_refresh_or_reuse,
    _prepare_photo_vql_handle_window_warning,
    _prepare_photo_vql_map_focus_fallback, _prepare_photo_vql_finalize_out, _prepare_photo_vql_apply_capture_guard,
    _prepare_photo_vql_drive_bootstrap, _pin_photo_vql_drive_env,
    _prepare_photo_vql_source_and_probe,
    _open_photo_vql_drive_session, _prepare_photo_vql_drive_prep, _prepare_photo_vql_confirm_capture_match,
    _prepare_photo_vql_attempt_outcome, _prepare_photo_vql_drive_attempt, _prepare_photo_vql_drive_attempts,
    _prepare_photo_vql_drive_out, prepare_photo_vql_for_drive, _normalize_photo_vql_drive_result,
)
from koru.integrations.vdisplay.chat_send import (  # noqa: E402,F401,I001
    _IDE_HINTS, _CHAT_INPUT_SELECTORS, _SUBMIT_BUTTON_SELECTORS,
    _persist_send_chat_drive_result, _finalize_send_chat, _ide_hints,
    _chat_selectors_for, _submit_selectors_for, _send_chat_preflight_ide_prompt,
    _send_chat_preflight_capture_blocked, _send_chat_preflight, _send_chat_try_photo_vql,
    _send_chat_dry_run, _send_chat_try_os_injector, _send_chat_try_ide_prompt_fallback,
    _send_chat_semantic_vdisplay, _send_chat_photo_vql_mouse_focus, _send_chat_resolve_chat_selector,
    _send_chat_selector_click_point, _send_chat_selector_write_kwargs, _send_chat_type_at_selector,
    _send_chat_submit_if_requested, send_chat,
)
from koru.integrations.vdisplay.input_actuation import (  # noqa: E402,F401,I001
    _agent_client, _controls_find, _control_focus,
    _control_set_value, _control_click, _find_first_selector,
    _effective_submit_enabled, _submit_via_keyboard, _photo_vql_submit_chat,
    _ide_prompt_app_id, _resolve_ide_prompt_map, _ide_map_message_target,
    _type_text_via_ide_map_fallback, send_chat_via_ide_prompt, _ydotool_click_capture_local,
    _type_text_blocking_warnings, _type_text_blocked_result, _type_text_dry_run_result,
    _type_text_try_atspi_set_value, _type_text_must_click, _type_text_fallback_click,
    _type_text_paste_or_type, _type_text_prepare_click_context, _type_text_at_vql_coords,
)
from koru.integrations.vdisplay.chat_target import (  # noqa: E402,F401,I001
    _resolve_vql_chat_target, _find_vql_chat_target, _extract_vql_click_from_target,
    _get_pycharm_vql_editor_center, _get_jetbrains_pycharm_chat_center, _photo_vql_elements,
    _live_surface_capture_meta, _jetbrains_surface_chat_target, _chat_target_validation_accepts,
    _vql_file_for_positioning, _photo_vql_jetbrains_chat_flow, _photo_vql_vscode_chat_flow,
    _try_ocr_anchor_chat_target, _vql_chat_canonical_ide, _vql_chat_source_name,
    _vql_chat_selection_context, _log_vql_chat_candidates, _surface_trusted_validation_patch,
    _finalize_vql_chat_target, _try_llm_vision_chat_detect, _vql_chat_target_hardened_fallback,
    _vql_chat_target_generic_flow, get_vql_chat_target_from_photo,
)
from koru.integrations.vdisplay.map_pointer import (  # noqa: E402,F401,I001
    _photo_vql_needs_vision_or_map, _jetbrains_map_selection_method, _jetbrains_map_selection_stage,
    get_vql_editor_target_from_photo, click_editor_via_photo_vql, _photo_capture_meta_for_source,
    _matching_ide_map_capture_meta, _enrich_capture_meta_for_pointer, _map_chat_input_candidate_keys,
    _map_chat_pointer_meta, _map_chat_element_local_point, _map_chat_target_entry,
    _map_chat_bottom_right_target, _map_chat_nonnegative_target, _map_chat_target_capture_local,
    _global_coords_from_vql_local,
)
from koru.integrations.vdisplay.command_plan import (  # noqa: E402,F401,I001
    _vql_plan_warnings, _vql_plan_data_mtime, _vql_plan_selection_method,
    _vql_plan_capture_flags, _vql_plan_commands, _llm_target_verified,
    _vql_plan_resolve_validation, _vql_plan_inference_flags, _vql_plan_payload,
    _build_vql_command_plan, _cursor_record_vql_validation, _log_vql_cursor_positioning_at_command,
    _resolve_photo_vql_llm_coords, _resolve_photo_vql_llm_coords_via_koru_detector, _llm_detection_decision_from_target,
    _photo_vql_map_paste_fallback,
)
from koru.integrations.vdisplay.capture_gates import (  # noqa: E402,F401,I001
    _mismatch_shows_competing_ide, _vision_overrides_capture_mismatch, _photo_vql_capture_mismatch_blocks,
    _surface_only_fallback_active, _surface_bounds_target_trusted, _surface_bounds_target_safe_for_actuation,
    _photo_vql_capture_mismatch_error, _target_selection_method, _selection_method_is_map,
    _map_target_can_clear_capture_mismatch, _is_jetbrains_map_target, _map_mismatch_allowed_for_target,
    _map_capture_mismatch_for_target, _map_capture_mismatch_for_ide, _photo_vql_map_source_mismatch_error,
    _surface_target_can_clear_capture_mismatch, _surface_mismatch_allowed_for_target,
    _photo_vql_should_block_unverified_chat, _photo_vql_unverified_chat_blocked,
)
from koru.integrations.vdisplay.focus_edit import (  # noqa: E402,F401,I001
    _photo_vql_focus_target, _photo_vql_edit_result, _photo_vql_stale_gate_override_ok,
    _photo_vql_stale_metadata_gate, _photo_vql_capture_mismatch_gate, _photo_vql_map_source_preflight_gate,
    _photo_vql_target_map_mismatch_gate, _photo_vql_maybe_clear_mismatch, _photo_vql_refined_target,
    _photo_vql_command_plan_pre_act, _photo_vql_unverified_chat_gate, _photo_vql_edit_mismatch_allowances,
    _photo_vql_combined_ok_after_edit, _photo_vql_run_paste_verification, _photo_vql_post_paste_verification,
    _photo_vql_submit_step, _photo_vql_assemble_combined, _photo_vql_persist_drive_result,
    _photo_vql_entry_gate_blocker, _photo_vql_selected_target, _photo_vql_refined_plan,
    _photo_vql_edit_stages, _photo_vql_edit_pipeline, perform_photo_vql_focus_and_edit,
    move_mouse_to_vql_target_and_focus_keyboard, _move_mouse_attempt_focus_and_click, _move_mouse_click_outcome,
)
from koru.integrations.vdisplay.vql_metadata import (  # noqa: E402,F401,I001
    _vql_candidate_is_stale, _vql_imgl_fallback_layers, _parse_vql_candidate_data,
    _load_vql_candidate_metadata, load_vql_metadata, _resolve_vql_candidate,
    _monitor_source_slugs, _get_vql_candidates, _freshest_populated_vql_candidate,
    get_vql_target, resolve_click_for_frame, _vdisplay_vql,
    _png_path_for_vql_sidecar, _main_vql_layer_count, _imgl_sidecar_path_for_vql,
    _layers_from_imgl_sidecar_file, _layers_from_vdisplay_sidecar, _with_embedded_capture_validation,
    _vql_from_ui_elements, _vql_from_fresh_elements, _vql_from_sidecar_layers,
    _vql_from_program_wrapper, _vql_from_screen_context, _vql_metadata_default,
    _parse_fresh_vql_elements,
)













































from koru.integrations.vdisplay import window_focus as _window_focus  # noqa: E402,F401
















































































































































































































































































































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




























