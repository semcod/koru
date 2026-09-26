"""Capture-mismatch and unverified-chat gating rules extracted from
``vdisplay_client``.

Moved verbatim from the historical ``vdisplay_client`` monolith; the
facade re-exports every name, so ``from koru.integrations.vdisplay_client
import X`` keeps working. References that were ``vdisplay_client`` module
globals resolve through the facade at call time (``_vdc()``) so
``monkeypatch.setattr(vdisplay_client, ...)`` keeps steering the pipeline.
"""

from __future__ import annotations

import os
from typing import Any


def _vdc():
    """The vdisplay_client facade (imported lazily: it imports this module)."""
    import koru.integrations.vdisplay_client as m

    return m


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
    competing = _vdc()._COMPETING_IDE_WINDOW_TOKENS.get(_vdc()._canonical_ide(ide), ())
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
        and not _vdc()._mismatch_shows_competing_ide(mismatch, ide=ide)
    )


def _photo_vql_capture_mismatch_blocks(
    *,
    mismatch: dict[str, Any] | None,
    ide: str,
    is_code_edit: bool,
) -> bool:
    return bool(
        mismatch
        and not _vdc()._dry_run()
        and _vdc()._canonical_ide(ide) in {"jetbrains", "pycharm", "idea"}
        and not _vdc()._allow_actuation_on_capture_mismatch()
        # A confirmed right-docked chat panel (Qoder / AI Assistant) OCRs its
        # monitor's title as the editor, not "PyCharm"; when vision will decide
        # the coords, that non-competing mismatch is not a hard block for chat.
        and not (not is_code_edit and _vdc()._vision_overrides_capture_mismatch(mismatch, ide=ide))
        and not (not is_code_edit and _vdc()._allow_prepare_map_on_mismatch())
        and not (
            not is_code_edit
            and _vdc()._surface_only_fallback_active()
            and _vdc()._allow_prepare_surface_on_capture_error()
        )
        and not (is_code_edit and _vdc()._allow_prepare_map_on_mismatch())
    )


def _surface_only_fallback_active() -> bool:
    if not _vdc()._allow_prepare_surface_on_capture_error():
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
    if not _vdc()._surface_only_fallback_active():
        return False
    selected = method or _vdc()._target_selection_method(target or {})
    return selected == "jetbrains_surface_bounds"


def _surface_bounds_target_safe_for_actuation(
    *,
    target: dict[str, Any] | None = None,
    method: str | None = None,
    command_plan: dict[str, Any] | None = None,
) -> bool:
    """Surface bounds confirm the IDE window, but only clean validation confirms chat input."""
    if not _vdc()._surface_bounds_target_trusted(target=target, method=method):
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
        _vdc()._canonical_ide(ide) in {"jetbrains", "pycharm", "idea"}
        and (_vdc()._ide_mismatch_allowed() or _vdc()._allow_prepare_map_on_mismatch())
        and _vdc()._selection_method_is_map(_vdc()._target_selection_method(target))
    )


def _is_jetbrains_map_target(*, target: dict[str, Any], ide: str) -> bool:
    return bool(
        str((target or {}).get("id") or "").startswith("map:")
        and _vdc()._canonical_ide(ide) in {"jetbrains", "pycharm", "idea"}
    )


def _map_mismatch_allowed_for_target(*, target: dict[str, Any], ide: str) -> bool:
    return _vdc()._is_jetbrains_map_target(target=target, ide=ide) and _vdc()._allow_prepare_map_on_mismatch()


def _map_capture_mismatch_for_target(
    *,
    target: dict[str, Any] | None,
    ide: str,
    source: str | None,
) -> dict[str, Any] | None:
    if not target or not _vdc()._is_jetbrains_map_target(target=target, ide=ide):
        return None
    map_path = target.get("source")
    if not isinstance(map_path, str) or not map_path.endswith(".json"):
        map_path = _vdc()._resolve_ide_prompt_map(_vdc()._ide_prompt_app_id(ide))
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
    if not source or _vdc()._canonical_ide(ide) not in {"jetbrains", "pycharm", "idea"}:
        return None
    map_path = _vdc()._resolve_ide_prompt_map(_vdc()._ide_prompt_app_id(ide))
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
        _vdc()._surface_only_fallback_active()
        and _vdc()._canonical_ide(ide) in {"jetbrains", "pycharm", "idea"}
        and _vdc()._target_selection_method(target) == "jetbrains_surface_bounds"
        and _vdc()._allow_prepare_surface_on_capture_error()
        and _vdc()._surface_bounds_target_safe_for_actuation(target=target)
    )


def _surface_mismatch_allowed_for_target(*, target: dict[str, Any], ide: str) -> bool:
    return _vdc()._surface_target_can_clear_capture_mismatch(target=target, ide=ide)


def _photo_vql_should_block_unverified_chat(
    *,
    command_plan: dict[str, Any],
    is_code_edit: bool,
    map_mismatch_allowed: bool,
    surface_mismatch_allowed: bool = False,
) -> bool:
    return bool(
        not is_code_edit
        and not _vdc()._dry_run()
        and not command_plan.get("inference_ok")
        and not _vdc()._ide_mismatch_allowed()
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
