"""Photo-VQL drive preparation pipeline extracted from ``vdisplay_client``.

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


def _prepare_photo_vql_map_mismatch(
    *, map_path: str | None, src: str, desktop_probe: dict[str, Any]
) -> dict[str, Any]:
    """Detect GUI-map vs capture-source monitor mismatch folded into the probe."""
    map_mismatch = None
    if map_path:
        from koru.integrations.photo_vql_monitor import map_capture_monitor_mismatch

        map_mismatch = map_capture_monitor_mismatch(map_path, source=src)
        if map_mismatch:
            desktop_probe = {**desktop_probe, "map_capture_mismatch": map_mismatch}
    return {"map_mismatch": map_mismatch, "desktop_probe": desktop_probe}


def _prepare_photo_vql_probe_abort(
    *, src: str, session_dir, desktop_probe: dict[str, Any]
) -> dict[str, Any] | None:
    """Abort out dict when the desktop probe failed and abort-on-fail is set, else None."""
    if desktop_probe.get("ok") or not _vdc()._abort_on_desktop_probe_fail():
        return None
    abort_out: dict[str, Any] = {
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
    _vdc()._autonomy_session.persist_autonomy_phase(session_dir, "observe", "prepare", abort_out)
    return abort_out


def _prepare_photo_vql_out_skeleton(
    *,
    src: str,
    session_dir,
    desktop_probe: dict[str, Any],
    map_mismatch: dict[str, Any] | None,
    bootstrap: dict[str, Any],
) -> dict[str, Any]:
    """Initial prepare_photo_vql_for_drive out dict with bootstrap/map hints."""
    skeleton: dict[str, Any] = {
        "ok": False,
        "source": src,
        "session_dir": str(session_dir),
        "desktop_probe": desktop_probe,
    }
    if map_mismatch:
        skeleton["map_capture_mismatch"] = map_mismatch
        skeleton["hint"] = (
            map_mismatch.get("message")
            or "GUI map monitor does not match capture source"
        )
    agent_hint = (bootstrap.get("agent") or {}).get("hint")
    if agent_hint:
        skeleton["hint"] = f"{agent_hint} | {skeleton['hint']}" if skeleton.get("hint") else agent_hint
    screencast_boot = bootstrap.get("screencast") if isinstance(bootstrap.get("screencast"), dict) else {}
    screencast_hint = str(screencast_boot.get("hint") or "").strip()
    if screencast_hint:
        skeleton["vdisplay_screencast_hint"] = screencast_hint
        skeleton["hint"] = f"{screencast_hint} | {skeleton['hint']}" if skeleton.get("hint") else screencast_hint
    if screencast_boot.get("browser_bridge") or screencast_boot.get("browser_bridge_pending"):
        skeleton["browser_bridge_bootstrap"] = {
            "ok": screencast_boot.get("ok"),
            "reason": screencast_boot.get("reason"),
            "browser_bridge": screencast_boot.get("browser_bridge"),
            "keeper_mode": (screencast_boot.get("status") or {}).get("keeper_mode")
            if isinstance(screencast_boot.get("status"), dict)
            else screencast_boot.get("keeper_mode"),
        }
    return skeleton


def _prepare_photo_vql_ide_control_attempt(
    *, ide: str, src: str, ide_control: dict[str, Any] | None
) -> dict[str, Any]:
    """One auto-IDE-control attempt in the prepare retry loop (ide_control + force_refresh)."""
    force_refresh = False
    if _vdc()._auto_ide_control_enabled():
        ide_control = _vdc().ensure_vdisplay_ide_control(ide=ide, source=src)
        if ide_control.get("map_actuation_ok") or ide_control.get("interior_focused"):
            import time

            force_refresh = True
            time.sleep(
                float(os.environ.get("KORU_VDISPLAY_POST_FOCUS_CAPTURE_DELAY_S", "0.8"))
            )
    return {"ide_control": ide_control, "force_refresh": force_refresh}


def _prepare_photo_vql_refresh_or_reuse(
    *, src: str, ide: str, session_dir, force_refresh: bool
) -> dict[str, Any]:
    """Refresh the photo VQL sidecar, or reuse the fresh one already on disk."""
    if force_refresh or _vdc().photo_vql_sidecar_needs_refresh(source=src, ide=ide):
        return _vdc().refresh_photo_vql_sidecar(source=src, ide=ide)
    png = _vdc()._resolve_photo_png_path(src)
    vql = png.with_suffix(png.suffix + ".vql.json")
    meta = _vdc().load_vql_metadata(str(vql))
    return {
        "ok": True,
        "source": src,
        "png": str(png),
        "vql": str(vql),
        "elements": len(meta.get("ui_elements") or meta.get("layers") or []),
        "main_vql_layers": _vdc()._main_vql_layer_count(vql),
        "vql_source": meta.get("_source"),
        "reused_fresh_sidecar": True,
        "session_dir": str(session_dir),
    }


def _prepare_photo_vql_handle_window_warning(
    warned_result: dict[str, Any], *, warn: dict[str, Any], ide: str, src: str
) -> tuple[dict[str, Any], str | None]:
    """Handle an ide_window_warning inside the prepare retry loop: (out, "break" | None)."""
    warned_result["ide_window_warning"] = warn
    warned_result["capture_matches_ide"] = False
    os.environ.pop("KORU_VDISPLAY_CAPTURE_MATCHES_IDE", None)
    cv = warned_result.get("capture_validation") or {}
    if isinstance(cv, dict) and cv.get("body_false_positive"):
        warned_result["body_false_positive"] = True
    # Vision LLM will decide the chat coords from the screenshot; a title that
    # does not affirmatively say "PyCharm" (editor breadcrumb, or a right-docked
    # Qoder/AI chat panel) is not a prepare-stopping mismatch — but a title that
    # names a competing IDE still is.
    vision_soft = _vdc()._vision_overrides_capture_mismatch(warn, ide=ide)
    allow_continue = _vdc()._allow_prepare_map_on_mismatch() or vision_soft
    if (
        not allow_continue
        and not warned_result.get("_focus_recovery_tried")
        and _vdc()._raise_alt_tab_enabled(ide=ide)
    ):
        warned_result["_focus_recovery_tried"] = True
        recovered = _vdc()._attempt_focus_recovery_capture(ide=ide, source=src)
        if recovered.get("ok"):
            warned_result = recovered
            os.environ["KORU_VDISPLAY_CAPTURE_MATCHES_IDE"] = "1"
            if _vdc()._canonical_ide(ide) in {"jetbrains", "pycharm", "idea"}:
                os.environ.setdefault("KORU_VDISPLAY_PREFER_PHOTO_VQL", "auto")
            return warned_result, "break"
        warned_result["focus_recovery"] = recovered.get("focus_recovery")
    if not allow_continue:
        return warned_result, "break"
    return warned_result, None


def _prepare_photo_vql_map_focus_fallback(
    fallback_result: dict[str, Any],
    *,
    ide: str,
    src: str,
    ide_control: dict[str, Any] | None,
    map_path: str | None,
    map_mismatch: dict[str, Any] | None,
) -> dict[str, Any]:
    """On mismatch for JetBrains etc, do extra focus via map when map-only fallback is allowed,
    then re-capture to get correct VQL for the target IDE on the source."""
    fallback_result["capture_matches_ide"] = False
    if not _vdc()._allow_prepare_map_on_mismatch():
        return fallback_result
    mp = None
    if ide_control:
        mp = ide_control.get("map_path")
    if not mp:
        mp = map_path or _vdc()._resolve_ide_prompt_map(_vdc()._ide_prompt_app_id(ide))
    if map_mismatch:
        fallback_result.setdefault("map_skipped", True)
    elif _vdc()._canonical_ide(ide) in {"jetbrains", "pycharm", "idea"} and mp:
        try:
            for t in _vdc()._map_interior_targets_for_ide(_vdc()._ide_prompt_app_id(ide), mp)[:1]:
                _vdc()._control_click(backend="vision", map_path=mp, map_target=t, source=src)
            import time
            time.sleep(0.4)
            fallback_result = _vdc().refresh_photo_vql_sidecar(source=src, ide=ide)
        except Exception:
            pass
    return fallback_result


def _prepare_photo_vql_finalize_out(
    merged_result: dict[str, Any],
    *,
    ide: str,
    ide_control: dict[str, Any] | None,
    map_mismatch: dict[str, Any] | None,
    loop_attempts: int,
    session_dir,
) -> dict[str, Any]:
    """Merge ide_control/map-mismatch/provenance into the prepare out after the retry loop."""
    if ide_control is not None:
        merged_result["ide_control"] = ide_control
    if map_mismatch:
        merged_result["map_capture_mismatch"] = map_mismatch
        mm_msg = map_mismatch.get("message")
        if mm_msg:
            prior = merged_result.get("hint")
            merged_result["hint"] = mm_msg if not prior else f"{mm_msg} | {prior}"
    elif isinstance(ide_control, dict) and ide_control.get("map_capture_mismatch"):
        merged_result["map_capture_mismatch"] = ide_control["map_capture_mismatch"]
    merged_result["ide_control_attempts"] = loop_attempts
    merged_result["session_dir"] = str(session_dir)
    png_path = merged_result.get("png")
    vql_path = merged_result.get("vql")
    if png_path and vql_path and merged_result.get("capture_provenance") is None:
        try:
            meta = _vdc().load_vql_metadata(str(vql_path), allow_stale=True)
            merged_result["capture_provenance"] = _vdc()._capture_provenance(
                ide=ide,
                png_path=str(png_path),
                vql_path=str(vql_path),
                meta=meta,
            )
            if merged_result.get("capture_confirmed") is None:
                merged_result["capture_confirmed"] = merged_result["capture_provenance"].get("capture_confirmed")
        except Exception:
            pass
    return merged_result


def _prepare_photo_vql_apply_capture_guard(
    guarded_result: dict[str, Any],
    *,
    ide: str,
    src: str,
    desktop_probe: dict[str, Any],
    ide_control: dict[str, Any] | None,
) -> dict[str, Any]:
    """Apply surface capture confirmation + CaptureGuard/readiness to the prepare out."""
    capture_error = (
        guarded_result.get("ok") is False
        or bool(guarded_result.get("error"))
        or bool(guarded_result.get("returncode"))
    )
    _vdc()._apply_surface_capture_confirmation(
        guarded_result,
        ide=ide,
        source=src,
        desktop_probe=desktop_probe,
        capture_error=capture_error,
    )
    _vdc()._persist_surface_capture_confirmation_to_vql(guarded_result, ide=ide)
    confirmed = guarded_result.get("capture_confirmed")
    if os.environ.get("KORU_VDISPLAY_DEBUG_CAPTURE", "").strip() in {"1", "true", "yes", "on"}:
        import sys as _sys

        raw_cv = guarded_result.get("capture_validation")
        cv = raw_cv if isinstance(raw_cv, dict) else {}
        print(
            f"[capture-debug] ide={ide} src={src} confirmed={confirmed!r} "
            f"capture_error={capture_error} warn={bool(guarded_result.get('ide_window_warning'))} "
            f"cv.confirmed={cv.get('capture_confirmed')!r} "
            f"cv.vision_deferred={cv.get('vision_deferred_window_mismatch')!r} "
            f"vision_env={os.environ.get('KORU_VDISPLAY_LLM_VISION_DECISION')!r}/"
            f"{os.environ.get('VDISPLAY_VISION_CHAT_DETECT')!r}",
            file=_sys.stderr,
            flush=True,
        )
    guard = _vdc().CaptureGuard.from_observe(
        ide=ide,
        confirmed=confirmed if confirmed is not None else None,
        ide_window_warning=guarded_result.get("ide_window_warning"),
        body_false_positive=bool(guarded_result.get("body_false_positive")),
        map_only_fallback=bool(guarded_result.get("map_only_fallback")),
        surface_only_fallback=bool(guarded_result.get("surface_only_fallback")),
        capture_error=capture_error,
        ide_control=ide_control,
    )
    guarded_result = guard.apply_to_prepare_out(guarded_result, ide_control=ide_control, capture_error=capture_error)
    guarded_result = _vdc()._annotate_png_artifact_state(guarded_result)
    _vdc()._annotate_prepare_drive_readiness(guarded_result)
    return guarded_result


def _prepare_photo_vql_drive_bootstrap() -> dict[str, Any]:
    """Bootstrap vdisplay capture deps when the bootstrap module is importable."""
    try:
        from koru.integrations.vdisplay_agent_bootstrap import bootstrap_vdisplay_capture

        return bootstrap_vdisplay_capture()
    except ImportError:
        return {}


def _pin_photo_vql_drive_env(src: str) -> None:
    """Pin the KORU_VDISPLAY_* environment for koru drive / send_chat."""
    os.environ.setdefault("KORU_VDISPLAY_CONTROL_FALLBACK", "1")
    os.environ["KORU_VDISPLAY_SOURCE"] = src
    os.environ.pop("KORU_VDISPLAY_CAPTURE_MATCHES_IDE", None)


def _prepare_photo_vql_source_and_probe(*, ide: str) -> dict[str, Any]:
    """Resolve capture source + desktop probe, fold the bootstrap and pin env."""
    bootstrap = _vdc()._prepare_photo_vql_drive_bootstrap()
    src, desktop_probe = _vdc()._resolve_vdisplay_source_for_ide(ide)
    if bootstrap:
        desktop_probe = {**desktop_probe, "vdisplay_bootstrap": bootstrap}
    _vdc()._pin_photo_vql_drive_env(src)
    return {"src": src, "desktop_probe": desktop_probe, "bootstrap": bootstrap}


def _open_photo_vql_drive_session(
    *, ide: str, src: str, desktop_probe: dict[str, Any]
) -> dict[str, Any]:
    """Resolve the GUI map, begin the autonomy session and evaluate probe abort."""
    map_path = _vdc()._resolve_ide_prompt_map(_vdc()._ide_prompt_app_id(ide))
    mismatch = _vdc()._prepare_photo_vql_map_mismatch(
        map_path=map_path, src=src, desktop_probe=desktop_probe
    )
    session_dir = _vdc()._autonomy_session.begin_autonomy_session(ide=ide, source=src)
    _vdc()._autonomy_session.persist_autonomy_phase(
        session_dir, "decide", "desktop_probe", mismatch["desktop_probe"]
    )
    aborted = _vdc()._prepare_photo_vql_probe_abort(
        src=src, session_dir=session_dir, desktop_probe=mismatch["desktop_probe"]
    )
    return {
        "map_path": map_path,
        "map_mismatch": mismatch["map_mismatch"],
        "session_dir": session_dir,
        "desktop_probe": mismatch["desktop_probe"],
        "aborted": aborted,
    }


def _prepare_photo_vql_drive_prep(*, ide: str) -> dict[str, Any]:
    """Drive-prepare context: source, probe, env pins, session and abort state."""
    source = _vdc()._prepare_photo_vql_source_and_probe(ide=ide)
    session = _vdc()._open_photo_vql_drive_session(
        ide=ide, src=source["src"], desktop_probe=source["desktop_probe"]
    )
    return {"ide": ide, **source, **session}


def _prepare_photo_vql_confirm_capture_match(matched_result: dict[str, Any], *, ide: str) -> dict[str, Any]:
    """Mark the capture as matching the requested IDE (env + out flags)."""
    os.environ["KORU_VDISPLAY_CAPTURE_MATCHES_IDE"] = "1"
    matched_result["capture_matches_ide"] = True
    if _vdc()._canonical_ide(ide) in {"jetbrains", "pycharm", "idea"}:
        os.environ.setdefault("KORU_VDISPLAY_PREFER_PHOTO_VQL", "auto")
    return matched_result


def _prepare_photo_vql_attempt_outcome(
    candidate: dict[str, Any],
    *,
    ide: str,
    src: str,
    ide_control: dict[str, Any] | None,
    map_path: str | None,
    map_mismatch: dict[str, Any] | None,
) -> dict[str, Any]:
    """Decide one refreshed capture: {'out': ..., 'action': 'break' | 'retry'}."""
    warn = candidate.get("ide_window_warning") or _vdc()._photo_vql_ide_window_warning(
        ide=ide,
        meta=_vdc().load_vql_metadata(str(candidate.get("vql") or "")),
    )
    if warn:
        candidate, action = _vdc()._prepare_photo_vql_handle_window_warning(candidate, warn=warn, ide=ide, src=src)
        if action == "break":
            return {"out": candidate, "action": "break"}
    elif _vdc()._capture_matches_requested_ide(ide):
        return {"out": _vdc()._prepare_photo_vql_confirm_capture_match(candidate, ide=ide), "action": "break"}
    candidate = _vdc()._prepare_photo_vql_map_focus_fallback(
        candidate,
        ide=ide,
        src=src,
        ide_control=ide_control,
        map_path=map_path,
        map_mismatch=map_mismatch,
    )
    return {"out": candidate, "action": "retry"}


def _prepare_photo_vql_drive_attempt(
    *,
    prep: dict[str, Any],
    loop: dict[str, Any],
    retries: int,
) -> dict[str, Any]:
    """Advance the observe/IDE-control retry loop by one attempt."""
    loop_attempts = loop["loop_attempts"] + 1
    control = _vdc()._prepare_photo_vql_ide_control_attempt(
        ide=prep["ide"], src=prep["src"], ide_control=loop["ide_control"]
    )
    attempt_result = _vdc()._prepare_photo_vql_refresh_or_reuse(
        src=prep["src"],
        ide=prep["ide"],
        session_dir=prep["session_dir"],
        force_refresh=control["force_refresh"],
    )
    if not attempt_result.get("ok"):
        return {
            **loop,
            "out": attempt_result,
            "ide_control": control["ide_control"],
            "loop_attempts": loop_attempts,
            "stop": True,
        }
    outcome = _vdc()._prepare_photo_vql_attempt_outcome(
        attempt_result,
        ide=prep["ide"],
        src=prep["src"],
        ide_control=control["ide_control"],
        map_path=prep["map_path"],
        map_mismatch=prep["map_mismatch"],
    )
    if outcome["action"] == "break":
        return {
            **loop,
            "out": outcome["out"],
            "ide_control": control["ide_control"],
            "loop_attempts": loop_attempts,
            "stop": True,
        }
    if loop_attempts < retries:
        import time

        time.sleep(float(os.environ.get("KORU_VDISPLAY_IDE_CONTROL_RETRY_DELAY_S", "0.6")))
    return {
        **loop,
        "out": outcome["out"],
        "ide_control": control["ide_control"],
        "loop_attempts": loop_attempts,
        "stop": False,
    }


def _prepare_photo_vql_drive_attempts(*, prep: dict[str, Any]) -> dict[str, Any]:
    """Run the observe/IDE-control retry loop: out, ide_control, loop_attempts, stop."""
    retries = max(1, int(os.environ.get("KORU_VDISPLAY_IDE_CONTROL_RETRIES", "3") or "3"))
    loop: dict[str, Any] = {
        "out": _vdc()._prepare_photo_vql_out_skeleton(
            src=prep["src"],
            session_dir=prep["session_dir"],
            desktop_probe=prep["desktop_probe"],
            map_mismatch=prep["map_mismatch"],
            bootstrap=prep["bootstrap"],
        ),
        "ide_control": None,
        "loop_attempts": 0,
    }
    for _ in range(retries):
        loop = _vdc()._prepare_photo_vql_drive_attempt(prep=prep, loop=loop, retries=retries)
        if loop["stop"]:
            break
    return loop


def _prepare_photo_vql_drive_out(
    *,
    prep: dict[str, Any],
    result: dict[str, Any],
) -> dict[str, Any]:
    """Finalize, capture-guard and persist the drive-prepare out."""
    prepared = _vdc()._prepare_photo_vql_finalize_out(
        result["out"],
        ide=prep["ide"],
        ide_control=result["ide_control"],
        map_mismatch=prep["map_mismatch"],
        loop_attempts=result["loop_attempts"],
        session_dir=prep["session_dir"],
    )
    prepared = _vdc()._prepare_photo_vql_apply_capture_guard(
        prepared,
        ide=prep["ide"],
        src=prep["src"],
        desktop_probe=prep["desktop_probe"],
        ide_control=result["ide_control"],
    )
    prepared["desktop_probe"] = prep["desktop_probe"]
    _vdc()._autonomy_session.persist_autonomy_phase(prep["session_dir"], "observe", "prepare", prepared)
    return prepared


def prepare_photo_vql_for_drive(*, ide: str) -> dict[str, Any]:
    """Observe (if needed) + pin sidecar before koru drive / send_chat."""
    prep = _vdc()._prepare_photo_vql_drive_prep(ide=ide)
    if prep["aborted"] is not None:
        return prep["aborted"]
    result = _vdc()._prepare_photo_vql_drive_attempts(prep=prep)
    return _vdc()._prepare_photo_vql_drive_out(prep=prep, result=result)


def _normalize_photo_vql_drive_result(photo_res: dict[str, Any], *, ide: str, submit: bool) -> dict[str, Any]:
    """Normalize a drive result with the facade's current policy callbacks."""
    from koru.integrations.vdisplay.drive_result import DriveResultPolicy, normalize_drive_result

    return normalize_drive_result(
        photo_res,
        ide=ide,
        submit=submit,
        policy=DriveResultPolicy(
            trusted_visual_target_id=_vdc()._trusted_visual_target_id,
            surface_target_safe=_vdc()._surface_bounds_target_safe_for_actuation,
            allow_capture_mismatch=_vdc()._allow_actuation_on_capture_mismatch,
            allow_map_source_mismatch=_vdc()._map_source_mismatch_actuation_allowed,
        ),
    )
