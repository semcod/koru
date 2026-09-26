"""VQL command plan building, cursor validation and LLM coordinate
resolution extracted from ``vdisplay_client``.

Moved verbatim from the historical ``vdisplay_client`` monolith; the
facade re-exports every name, so ``from koru.integrations.vdisplay_client
import X`` keeps working. References that were ``vdisplay_client`` module
globals resolve through the facade at call time (``_vdc()``) so
``monkeypatch.setattr(vdisplay_client, ...)`` keeps steering the pipeline.
"""

from __future__ import annotations

import datetime
import logging
import os
from pathlib import Path
from typing import Any

logger = logging.getLogger("koru.integrations.vdisplay_client")


def _vdc():
    """The vdisplay_client facade (imported lazily: it imports this module)."""
    import koru.integrations.vdisplay_client as m

    return m


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
    if capture_mismatch and not _vdc()._surface_bounds_target_trusted(target=target):
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
    surface_trusted = _vdc()._surface_bounds_target_trusted(target=target, method=selection)
    eff_mismatch = None if surface_trusted else capture_mismatch
    capture_confirmed = bool((capture_provenance or {}).get("capture_confirmed")) or (
        surface_trusted and _vdc()._surface_only_fallback_active()
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
            "app": (_vdc()._ide_hints(ide).get("app") if ide and ide != "auto" else None),
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
    return _vdc().validate_vql_chat_target(
        target,
        ide=ide,
        meta=_vdc().load_vql_metadata(allow_stale=True),
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
    llm_verified = bool(_vdc()._llm_target_verified(llm_decision))
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
    inference_ok, plan_capture_confirmed = _vdc()._vql_plan_inference_flags(
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
    gx, gy, mapping = _vdc()._global_coords_from_vql_local(x=x, y=y, source=source)
    validation = _vdc()._vql_plan_resolve_validation(
        target=target,
        ide=ide,
        x=x,
        y=y,
        is_code_edit=is_code_edit,
        capture_mismatch=capture_mismatch,
        vql_validation=vql_validation,
    )
    warnings, validation_errors = _vdc()._vql_plan_warnings(validation, capture_mismatch, target, llm_decision)
    vql_file = target.get("source")
    vql_mtime = _vdc()._vql_plan_data_mtime(vql_file)

    selection = _vdc()._vql_plan_selection_method(target, vql_file, llm_decision)
    capture_title, eff_mismatch, capture_confirmed = _vdc()._vql_plan_capture_flags(
        validation, capture_provenance, capture_mismatch, target, selection
    )

    commands: list[dict[str, Any]] = _vdc()._vql_plan_commands(ide=ide, x=x, y=y, gx=gx, gy=gy, prompt=prompt)

    return _vdc()._vql_plan_payload(
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
        gx, gy, _mapping = _vdc()._global_coords_from_vql_local(
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
        "warnings": _vdc()._validate_chat_coords_for_ide(
            x=int(final_local.get("x", 0)),
            y=int(final_local.get("y", 0)),
            ide=ide,
            target=target,
        ),
    }
    _vdc()._cursor_record_vql_validation(record, command_plan=command_plan, target=target)
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

    session = _vdc()._autonomy_session.active_session_dir()
    if session is not None:
        _vdc()._autonomy_session.append_session_jsonl(session, "act/cursor_positioning.jsonl", record)
        if command_plan is not None:
            _vdc()._autonomy_session.persist_autonomy_phase(session, "act", f"command_plan_{stage}", command_plan)

    return record


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

    canon = _vdc()._canonical_ide(ide)

    if not (_vdc().llm_vision_enabled() and image_path and os.path.exists(image_path)):
        return x, y, None

    try:
        png = Path(image_path).read_bytes()
        layers, _src = _vdc()._photo_vql_elements()
        candidates = _vdc()._photo_vql_chat_input_candidates(layers, limit=8, ide=canon)
        map_hint = (
            _vdc()._map_chat_target_capture_local(ide=canon, source=source)
            if canon in {"jetbrains", "pycharm", "idea"}
            else None
        )
        meta_for_title = _vdc().load_vql_metadata(allow_stale=True)
        capture_title = _vdc()._capture_title_from_meta(meta_for_title) or "unknown"

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
        fallback = _vdc()._resolve_photo_vql_llm_coords_via_koru_detector(
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
    llm_decision = llm_target.get("llm_decision") or _vdc()._llm_detection_decision_from_target(
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
    if _vdc()._canonical_ide(ide) not in {"jetbrains", "pycharm", "idea"}:
        return None
    app_id = _vdc()._ide_prompt_app_id(ide)
    map_path = _vdc()._resolve_ide_prompt_map(app_id)
    if not map_path:
        return None
    return _vdc()._type_text_via_ide_map_fallback(prompt, map_path=map_path, app_id=app_id, ide=ide)
