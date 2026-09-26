"""Photo-VQL focus-and-edit pipeline and mouse move extracted from
``vdisplay_client``.

Moved verbatim from the historical ``vdisplay_client`` monolith; the
facade re-exports every name, so ``from koru.integrations.vdisplay_client
import X`` keeps working. References that were ``vdisplay_client`` module
globals resolve through the facade at call time (``_vdc()``) so
``monkeypatch.setattr(vdisplay_client, ...)`` keeps steering the pipeline.
"""

from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger("koru.integrations.vdisplay_client")


def _vdc():
    """The vdisplay_client facade (imported lazily: it imports this module)."""
    import koru.integrations.vdisplay_client as m

    return m


def _photo_vql_focus_target(
    *,
    target: dict[str, Any],
    ide: str,
    source: str,
    is_code_edit: bool,
    llm_decision: dict[str, Any] | None,
) -> dict[str, Any]:
    if is_code_edit and not llm_decision:
        return _vdc().click_editor_via_photo_vql(ide=ide, source=source)
    return _vdc().move_mouse_to_vql_target_and_focus_keyboard(target, ide=ide, source=source)


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
    if _vdc()._dry_run():
        return {
            "ok": True,
            "dry_run": True,
            "message": f"DRY: precise edit at VQL coords ({x},{y}) from foto target {target_desc}",
            "value": prompt,
        }
    if not _vdc().vdisplay_available():
        return {"ok": False, "error": "not attempted"}
    try:
        edit_res = _vdc()._type_text_at_vql_coords(
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
        map_fallback = _vdc()._photo_vql_map_paste_fallback(prompt, ide=ide)
        if map_fallback and map_fallback.get("ok"):
            edit_res = map_fallback
            edit_res["photo_vql_map_fallback"] = True
    return edit_res


def _photo_vql_stale_gate_override_ok(*, canon_probe: str, is_code_edit: bool) -> bool:
    """Whether map/surface fallbacks allow proceeding despite stale/errored VQL metadata."""
    map_mismatch_ok = (
        not is_code_edit
        and canon_probe in {"jetbrains", "pycharm", "idea"}
        and _vdc()._allow_prepare_map_on_mismatch()
    )
    surface_mismatch_ok = (
        not is_code_edit
        and canon_probe in {"jetbrains", "pycharm", "idea"}
        and _vdc()._surface_only_fallback_active()
        and _vdc()._allow_prepare_surface_on_capture_error()
    )
    code_edit_map_ok = (
        is_code_edit
        and canon_probe in {"jetbrains", "pycharm", "idea"}
        and _vdc()._allow_prepare_map_on_mismatch()
    )
    return map_mismatch_ok or surface_mismatch_ok or code_edit_map_ok


def _persist_blocked_gate_result(
    blocked: dict | None, *, phase: str, event: str
) -> dict | None:
    """Persist a gate's abort payload to the active autonomy session and return it.

    Single owner of the blocked-gate persist stanza so phase/event wiring for
    every focus-edit gate (stale metadata, capture mismatch, map-source
    preflight, per-target map mismatch, unverified chat) lives in one place.
    """
    session = _vdc()._autonomy_session.active_session_dir()
    if session is not None:
        _vdc()._autonomy_session.persist_autonomy_phase(session, phase, event, blocked)
    return blocked


def _photo_vql_stale_metadata_gate(*, ide: str, is_code_edit: bool) -> dict | None:
    """Abort dict when VQL metadata is stale/errored and no fallback allows it, else None."""
    meta_probe = _vdc().load_vql_metadata()
    if not meta_probe.get("error") or _vdc()._dry_run():
        return None
    stale_only = bool(meta_probe.get("stale_skipped"))
    session_active = _vdc()._autonomy_session.active_session_dir() is not None
    canon_probe = _vdc()._canonical_ide(ide)
    override_ok = _vdc()._photo_vql_stale_gate_override_ok(
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
    return _persist_blocked_gate_result(err, phase="decide", event="stale_abort")


def _photo_vql_capture_mismatch_gate(
    *, mismatch: dict[str, Any] | None, ide: str, is_code_edit: bool
) -> dict | None:
    """Abort dict when the IDE/capture mismatch blocks actuation, else None."""
    if not _vdc()._photo_vql_capture_mismatch_blocks(
        mismatch=mismatch,
        ide=ide,
        is_code_edit=is_code_edit,
    ):
        return None
    return _persist_blocked_gate_result(
        _vdc()._photo_vql_capture_mismatch_error(
            mismatch=mismatch or {},
            ide=ide,
            is_code_edit=is_code_edit,
        ),
        phase="decide",
        event="ide_capture_blocked",
    )


def _photo_vql_map_source_preflight_gate(
    *, ide: str, source: str, is_code_edit: bool
) -> dict | None:
    """Abort dict when the IDE prompt-map monitor mismatches the capture source, else None."""
    ide_map_source_mismatch = _vdc()._map_capture_mismatch_for_ide(ide=ide, source=source)
    if not ide_map_source_mismatch or _vdc()._map_source_mismatch_actuation_allowed():
        return None
    return _persist_blocked_gate_result(
        _vdc()._photo_vql_map_source_mismatch_error(
            map_mismatch=ide_map_source_mismatch,
            target={
                "id": "map:ide-prompt",
                "source": ide_map_source_mismatch.get("map_path"),
                "selection_method": "map_source_preflight",
            },
            ide=ide,
            source=source,
            is_code_edit=is_code_edit,
        ),
        phase="act",
        event="map_source_mismatch_preflight_blocked",
    )


def _photo_vql_target_map_mismatch_gate(
    t: dict[str, Any], *, ide: str, source: str, is_code_edit: bool
) -> tuple[dict | None, dict[str, Any] | None]:
    """Per-target map/capture mismatch gate: (abort dict | None, map_source_mismatch)."""
    map_source_mismatch = _vdc()._map_capture_mismatch_for_target(target=t, ide=ide, source=source)
    if map_source_mismatch and not _vdc()._map_source_mismatch_actuation_allowed():
        return _persist_blocked_gate_result(
            _vdc()._photo_vql_map_source_mismatch_error(
                map_mismatch=map_source_mismatch,
                target=t,
                ide=ide,
                source=source,
                is_code_edit=is_code_edit,
            ),
            phase="act",
            event="map_source_mismatch_blocked",
        ), map_source_mismatch
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
    if _vdc()._map_target_can_clear_capture_mismatch(target=t, ide=ide):
        mismatch = None
        t["_map_cleared_mismatch_for_actuation"] = True
    elif _vdc()._surface_target_can_clear_capture_mismatch(target=t, ide=ide):
        mismatch = None
        t["_surface_cleared_mismatch_for_actuation"] = True
    return mismatch


def _photo_vql_refined_target(
    *, prompt: str, t: dict[str, Any], source: str, image_path: str | None, ide: str
) -> tuple[dict[str, Any], int, int, dict[str, Any] | None]:
    """Resolve (possibly LLM-refined) coords and annotate the target: (t, x, y, llm_decision)."""
    x, y, llm_decision = _vdc()._resolve_photo_vql_llm_coords(
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
        session = _vdc()._autonomy_session.active_session_dir()
        if session is not None:
            _vdc()._autonomy_session.persist_autonomy_phase(
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
    command_plan = _vdc()._build_vql_command_plan(
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
        capture_provenance=_vdc()._capture_provenance(
            ide=ide,
            png_path=_vdc()._resolve_photo_png_path_from_vql(source=source),
            vql_path=_vdc()._observe_vql_sidecar_path(source=source),
            meta=_vdc().load_vql_metadata(allow_stale=True),
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
    session = _vdc()._autonomy_session.active_session_dir()
    if session is not None:
        _vdc()._autonomy_session.persist_autonomy_phase(
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
    map_mismatch_allowed = _vdc()._map_mismatch_allowed_for_target(target=t, ide=ide)
    surface_mismatch_allowed = _vdc()._surface_mismatch_allowed_for_target(target=t, ide=ide)
    if not _vdc()._photo_vql_should_block_unverified_chat(
        command_plan=command_plan,
        is_code_edit=is_code_edit,
        map_mismatch_allowed=map_mismatch_allowed,
        surface_mismatch_allowed=surface_mismatch_allowed,
    ):
        return None
    return _persist_blocked_gate_result(
        _vdc()._photo_vql_unverified_chat_blocked(
            command_plan=command_plan,
            target_desc=target_desc,
            target=t,
            x=x,
            y=y,
            ide=ide,
            mismatch=mismatch,
        ),
        phase="act",
        event="chat_actuation_blocked",
    )


def _photo_vql_edit_mismatch_allowances(*, t: dict[str, Any], ide: str) -> tuple[bool, bool]:
    """(map_mismatch_allowed, surface_mismatch_allowed) for combined_ok re-derivation."""
    is_jetbrains_map = str((t or {}).get("id") or "").startswith("map:") and _vdc()._canonical_ide(ide) in {"jetbrains", "pycharm", "idea"}  # noqa: E501
    map_mismatch_allowed = is_jetbrains_map and _vdc()._ide_mismatch_allowed()
    surface_mismatch_allowed = _vdc()._surface_mismatch_allowed_for_target(target=t, ide=ide)
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
    map_mismatch_allowed, surface_mismatch_allowed = _vdc()._photo_vql_edit_mismatch_allowances(
        t=t, ide=ide
    )
    if mismatch and not _vdc()._ide_mismatch_allowed() and not map_mismatch_allowed and not surface_mismatch_allowed:
        combined_ok = False
    if (
        not command_plan.get("inference_ok", True)
        and not _vdc()._ide_mismatch_allowed()
        and not _vdc()._dry_run()
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
        return _vdc().verify_chat_text_visible(prompt, ide=ide, map_path=map_path)
    return _vdc().verify_chat_text_visible(
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
        and not _vdc()._dry_run()
        and not is_code_edit
        and bool(edit_res.get("ok"))
        and not _vdc()._surface_bounds_target_safe_for_actuation(target=t, command_plan=command_plan)
    ):
        verification = _vdc()._photo_vql_run_paste_verification(
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
    if submit and combined_ok and not _vdc()._dry_run():
        import time

        time.sleep(float(os.environ.get("KORU_VDISPLAY_SUBMIT_DELAY_S", "0.25")))
        submit_result = _vdc()._photo_vql_submit_chat(ide=ide, source=source)
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
    session = _vdc()._autonomy_session.active_session_dir()
    if session is not None:
        _vdc()._autonomy_session.persist_autonomy_phase(
            session,
            "decide",
            "vql_target",
            {"target": t, "llm_decision": llm_decision, "mismatch": mismatch},
        )
        _vdc()._autonomy_session.persist_autonomy_phase(session, "act", "drive_result", combined)
        if verification is not None:
            _vdc()._autonomy_session.persist_autonomy_phase(session, "verify", "chat_text_visible", verification)
        try:
            _vdc().record_koru_drive_step(combined, profile_id=ide or "auto", text=prompt)
        except Exception:
            pass


def _photo_vql_entry_gate_blocker(
    *, ide: str, source: str, is_code_edit: bool, mismatch: dict[str, Any] | None
) -> dict | None:
    """Entry blockers for perform_photo_vql_focus_and_edit: stale metadata, capture mismatch, map-source preflight."""
    err = _vdc()._photo_vql_stale_metadata_gate(ide=ide, is_code_edit=is_code_edit)
    if err is None:
        err = _vdc()._photo_vql_capture_mismatch_gate(mismatch=mismatch, ide=ide, is_code_edit=is_code_edit)
    if err is None:
        err = _vdc()._photo_vql_map_source_preflight_gate(ide=ide, source=source, is_code_edit=is_code_edit)
    return err


def _photo_vql_selected_target(
    *, ide: str, source: str, is_code_edit: bool, image_path: str | None, mismatch: dict[str, Any] | None
) -> dict[str, Any]:
    """Select the photo VQL chat/editor target and resolve its mismatch/map-source context."""
    t = _vdc().get_vql_editor_target_from_photo() if is_code_edit else _vdc().get_vql_chat_target_from_photo(ide=ide)
    target_desc = "editor/open-file" if is_code_edit else "chat"
    blocked, map_source_mismatch = _vdc()._photo_vql_target_map_mismatch_gate(
        t, ide=ide, source=source, is_code_edit=is_code_edit
    )
    if blocked is not None:
        return {"blocked": blocked}
    return {
        "blocked": None,
        "t": t,
        "target_desc": target_desc,
        "map_source_mismatch": map_source_mismatch,
        "mismatch": _vdc()._photo_vql_maybe_clear_mismatch(t, ide=ide, mismatch=mismatch),
        "image_path": image_path if image_path is not None else _vdc()._resolve_photo_png_path_from_vql(source=source),
        "is_code_edit": is_code_edit,
    }


def _photo_vql_refined_plan(
    *, prompt: str, ide: str, source: str, mismatch: dict[str, Any] | None, selected: dict[str, Any]
) -> dict[str, Any]:
    """Refine the selected target (corner heuristics + optional LLM vision) and pre-check the command plan."""
    refined = _vdc()._photo_vql_refined_target(
        prompt=prompt, t=selected["t"], source=source, image_path=selected["image_path"], ide=ide
    )
    command_plan = _vdc()._photo_vql_command_plan_pre_act(
        t=refined[0],
        x=refined[1],
        y=refined[2],
        source=source,
        ide=ide,
        prompt=prompt,
        llm_decision=refined[3],
        is_code_edit=selected["is_code_edit"],
        mismatch=mismatch,
    )
    blocked = _vdc()._photo_vql_unverified_chat_gate(
        command_plan=command_plan,
        t=refined[0],
        target_desc=selected["target_desc"],
        x=refined[1],
        y=refined[2],
        ide=ide,
        mismatch=mismatch,
        is_code_edit=selected["is_code_edit"],
    )
    if blocked is not None:
        return {"blocked": blocked}
    return {
        "blocked": None,
        "t": refined[0],
        "x": refined[1],
        "y": refined[2],
        "llm_decision": refined[3],
        "command_plan": command_plan,
    }


def _photo_vql_edit_stages(
    *, prompt: str, ide: str, source: str, plan: dict[str, Any], selected: dict[str, Any]
) -> dict[str, Any]:
    """Run the focus, edit and post-paste verification stages of the photo VQL pipeline."""
    focus_res = _vdc()._photo_vql_focus_target(
        target=plan["t"],
        ide=ide,
        source=source,
        is_code_edit=selected["is_code_edit"],
        llm_decision=plan["llm_decision"],
    )
    edit_res = _vdc()._photo_vql_edit_result(
        prompt,
        x=plan["x"],
        y=plan["y"],
        target_desc=selected["target_desc"],
        source=source,
        ide=ide,
        focus_res=focus_res,
        target=plan["t"],
        command_plan=plan["command_plan"],
    )
    combined_ok = _vdc()._photo_vql_combined_ok_after_edit(
        edit_res=edit_res,
        t=plan["t"],
        ide=ide,
        mismatch=selected["mismatch"],
        command_plan=plan["command_plan"],
        is_code_edit=selected["is_code_edit"],
    )
    post_paste = _vdc()._photo_vql_post_paste_verification(
        prompt=prompt,
        t=plan["t"],
        command_plan=plan["command_plan"],
        combined_ok=combined_ok,
        edit_res=edit_res,
        is_code_edit=selected["is_code_edit"],
        ide=ide,
        x=plan["x"],
        y=plan["y"],
    )
    return {
        "focus_res": focus_res,
        "edit_res": edit_res,
        "verification": post_paste[0],
        "combined_ok": post_paste[1],
    }


def _photo_vql_edit_pipeline(
    *, prompt: str, ide: str, source: str, submit: bool, plan: dict[str, Any], selected: dict[str, Any]
) -> dict:
    """Execute the edit stages + submit step, then assemble and persist the combined photo VQL result."""
    stages = _vdc()._photo_vql_edit_stages(prompt=prompt, ide=ide, source=source, plan=plan, selected=selected)
    submit_step = _vdc()._photo_vql_submit_step(
        submit=submit, combined_ok=stages["combined_ok"], edit_res=stages["edit_res"], ide=ide, source=source
    )
    combined = _vdc()._photo_vql_assemble_combined(
        combined_ok=submit_step[2],
        target_desc=selected["target_desc"],
        t=plan["t"],
        focus_res=stages["focus_res"],
        edit_res=stages["edit_res"],
        x=plan["x"],
        y=plan["y"],
        prompt=prompt,
        ide=ide,
        is_code_edit=selected["is_code_edit"],
        llm_decision=plan["llm_decision"],
        submitted=submit_step[0],
        command_plan=plan["command_plan"],
        verification=stages["verification"],
        submit_result=submit_step[1],
        mismatch=selected["mismatch"],
        map_source_mismatch=selected["map_source_mismatch"],
    )
    _vdc()._photo_vql_persist_drive_result(
        combined,
        t=plan["t"],
        llm_decision=plan["llm_decision"],
        mismatch=selected["mismatch"],
        verification=stages["verification"],
        ide=ide,
        prompt=prompt,
    )
    return combined


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
    mismatch = _vdc()._photo_vql_ide_capture_mismatch(ide=ide) if ide and ide != "auto" else None

    err = _vdc()._photo_vql_entry_gate_blocker(ide=ide, source=source, is_code_edit=is_code_edit, mismatch=mismatch)
    if err is not None:
        return err

    selected = _vdc()._photo_vql_selected_target(
        ide=ide, source=source, is_code_edit=is_code_edit, image_path=image_path, mismatch=mismatch
    )
    if selected["blocked"] is not None:
        return selected["blocked"]

    plan = _vdc()._photo_vql_refined_plan(
        prompt=prompt, ide=ide, source=source, mismatch=selected["mismatch"], selected=selected
    )
    if plan["blocked"] is not None:
        return plan["blocked"]

    return _vdc()._photo_vql_edit_pipeline(
        prompt=prompt, ide=ide, source=source, submit=submit, plan=plan, selected=selected
    )


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
        target = _vdc().get_vql_chat_target_from_photo(ide=ide)
    cc = (target or {}).get("click_center") or {"x": 1024, "y": 640}
    x = int(cc.get("x", 1024))
    y = int(cc.get("y", 640))
    hints = _vdc()._ide_hints(ide) if ide and ide != "auto" else {}
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
    _vdc()._log_vql_cursor_positioning_at_command(
        target,
        stage="move_to_chat_for_write_command",
        ide=ide,
        source=source,
        final_local={"x": x, "y": y},
        vql_file=vql_file,
        command_plan=target.get("vql_command_plan"),
    )

    if _vdc()._dry_run() or not _vdc().vdisplay_available():
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
    click_res, focus_res, last_err = _vdc()._move_mouse_attempt_focus_and_click(
        result, hints=hints, x=x, y=y, source=source
    )
    return _vdc()._move_mouse_click_outcome(
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
        focus_res = _vdc()._control_focus(**focus_payload)
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
            click_res = _vdc()._control_click(**payload)
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
