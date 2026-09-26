"""send_chat pipeline (preflight, fallback routing, selector plumbing)
extracted from ``vdisplay_client``.

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


def _persist_send_chat_drive_result(
    result: dict[str, Any],
    *,
    prompt: str,
    ide: str,
    submit: bool,
) -> None:
    """Persist act/drive_result.json for send_chat outcomes (photo-vql, ide-prompt, blocked)."""
    session = _vdc()._autonomy_session.active_session_dir()
    if session is None:
        return
    backend = str(result.get("backend") or "")
    if result.get("type") == "blocked" or backend.endswith("+blocked"):
        _vdc()._autonomy_session.persist_autonomy_phase(session, "act", "drive_result", {**result, "prompt": prompt[:200], "submit": submit})  # noqa: E501
        return
    if not (backend.startswith("vdisplay") or result.get("type") == "drive"):
        return
    payload = {**result, "prompt": prompt[:200], "submit": submit}
    _vdc()._autonomy_session.persist_autonomy_phase(session, "act", "drive_result", payload)


def _finalize_send_chat(
    result: dict[str, Any],
    *,
    prompt: str,
    ide: str,
    submit: bool,
) -> dict[str, Any]:
    _vdc()._persist_send_chat_drive_result(result, prompt=prompt, ide=ide, submit=submit)
    return result


def _ide_hints(ide: str) -> dict[str, str]:
    canon = _vdc()._canonical_ide(ide)
    # Prefer local _IDE_HINTS for consistency with test expectations
    if canon in _vdc()._IDE_HINTS:
        return dict(_vdc()._IDE_HINTS[canon])
    try:
        from vdisplay.desktop_apps import ide_hints_for

        return ide_hints_for(canon)
    except Exception:
        return {"app": canon, "window_title_contains": canon}


def _chat_selectors_for(ide: str) -> tuple[dict[str, str], ...]:
    # Return local selectors by default for consistency with tests
    return _vdc()._CHAT_INPUT_SELECTORS


def _submit_selectors_for(ide: str) -> tuple[dict[str, str], ...]:
    # Return local selectors by default for consistency with tests
    return _vdc()._SUBMIT_BUTTON_SELECTORS


def _send_chat_preflight_ide_prompt(
    prompt: str,
    *,
    ide: str,
    submit: bool,
    effective_dry: bool,
    mismatch: dict[str, Any] | None,
) -> dict[str, Any] | None:
    """Preferred IDE-prompt path in _send_chat_preflight (real drive or dry-run intent)."""
    if not effective_dry and _vdc().vdisplay_available():
        ide_prompt = _vdc().send_chat_via_ide_prompt(
            prompt, ide=ide, submit=submit, dry_run=False,
        )
        if ide_prompt is not None and ide_prompt.get("ok"):
            if mismatch:
                ide_prompt["ide_window_warning"] = mismatch
                ide_prompt["photo_vql_skipped"] = True
            return _vdc()._finalize_send_chat(ide_prompt, prompt=prompt, ide=ide, submit=submit)
    if effective_dry:
        app_id = _vdc()._ide_prompt_app_id(ide)
        map_path = _vdc()._resolve_ide_prompt_map(app_id)
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
        return _vdc()._finalize_send_chat(out, prompt=prompt, ide=ide, submit=submit)
    return None


def _send_chat_preflight_capture_blocked(
    blocked: dict[str, Any], *, prompt: str, ide: str, submit: bool
) -> dict[str, Any]:
    """Persist and finalize a capture-mismatch drive block."""
    session = _vdc()._autonomy_session.active_session_dir()
    if session is not None:
        _vdc()._autonomy_session.persist_autonomy_phase(session, "decide", "capture_blocked", blocked)
    return _vdc()._finalize_send_chat(blocked, prompt=prompt, ide=ide, submit=submit)


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
    mismatch = _vdc()._photo_vql_ide_capture_mismatch(ide=ide)
    blocked = _vdc()._drive_blocked_on_capture_mismatch(
        ide=ide, mismatch=mismatch, dry_run=effective_dry
    ) if mismatch else None
    prefer_ide_prompt = _vdc()._prefer_ide_prompt_over_photo_vql(ide=ide)
    map_on_mismatch_allowed = bool(mismatch and _vdc()._allow_prepare_map_on_mismatch())
    surface_on_capture_error = bool(
        mismatch and _vdc()._surface_only_fallback_active() and _vdc()._allow_prepare_surface_on_capture_error()
    )
    if prefer_ide_prompt and (blocked is None or map_on_mismatch_allowed or surface_on_capture_error):
        result = _vdc()._send_chat_preflight_ide_prompt(
            prompt, ide=ide, submit=submit, effective_dry=effective_dry, mismatch=mismatch
        )
        if result is not None:
            return result
    if blocked is not None and not map_on_mismatch_allowed and not surface_on_capture_error:
        return _vdc()._send_chat_preflight_capture_blocked(blocked, prompt=prompt, ide=ide, submit=submit)
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
        _vdc()._prefer_photo_vql_chat(ide=ide)
        or (use_llm_vision and _vdc().llm_vision_enabled() and _vdc()._capture_matches_requested_ide(ide))
        or is_code
    )
    if not photo_prefer_chat:
        return None
    if effective_dry:
        os.environ["KORU_VDISPLAY_DRY_RUN"] = "1"
    photo_res = _vdc().perform_photo_vql_focus_and_edit(
        prompt,
        ide=ide,
        source=_vdc()._vdisplay_source_for_ide(ide),
        is_code_edit=is_code,
        submit=submit,
    )
    return _vdc()._finalize_send_chat(
        _vdc()._normalize_photo_vql_drive_result(photo_res, ide=ide, submit=submit),
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
    app_id = _vdc()._ide_prompt_app_id(ide)
    map_path = _vdc()._resolve_ide_prompt_map(app_id)
    hints = _vdc()._ide_hints(ide)
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
    if not _vdc()._send_chat_os_injector_enabled(ide=ide):
        return None
    canon = _vdc()._canonical_ide(ide)
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
    ide_prompt = _vdc().send_chat_via_ide_prompt(
        prompt, ide=ide, submit=submit, dry_run=False,
    )
    if ide_prompt is not None and ide_prompt.get("ok"):
        return _vdc()._finalize_send_chat(ide_prompt, prompt=prompt, ide=ide, submit=submit)
    return None


def _send_chat_semantic_vdisplay(
    prompt: str,
    *,
    ide: str,
    submit: bool,
) -> dict[str, Any]:
    """VQL photo chat focus + selector/set_value typing path."""
    hints = _vdc()._ide_hints(ide)
    focus_error: str | None = None
    photo_vql_target: dict[str, Any] | None = None

    if not _vdc()._dry_run() and os.environ.get("KORU_VDISPLAY_USE_VQL_MOUSE_FOCUS", "1").strip().lower() not in {
        "0",
        "false",
        "no",
        "off",
    }:
        photo_vql_target, focus_error = _vdc()._send_chat_photo_vql_mouse_focus(prompt, ide=ide)

    selector, found, selector_error = _vdc()._send_chat_resolve_chat_selector(
        ide=ide,
        hints=hints,
        photo_vql_target=photo_vql_target,
        focus_error=focus_error,
    )
    if selector_error is not None:
        return selector_error

    typed, click_point, type_error = _vdc()._send_chat_type_at_selector(
        prompt,
        ide=ide,
        hints=hints,
        selector=selector,
        found=found,
        focus_error=focus_error,
    )
    if type_error is not None:
        return type_error

    submitted, submit_result = _vdc()._send_chat_submit_if_requested(ide=ide, hints=hints, submit=submit)
    return _vdc()._finalize_send_chat(
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
        photo_vql_target = _vdc().get_vql_chat_target_from_photo()
        use_llm_vision = _vdc().llm_vision_enabled()
        if use_llm_vision:
            image_path = _vdc()._resolve_photo_png_path_from_vql(source=_vdc()._vdisplay_source())
            if image_path and os.path.exists(str(image_path)):
                try:
                    rx, ry, rdec = _vdc()._resolve_photo_vql_llm_coords(
                        prompt=prompt,
                        target=photo_vql_target,
                        source=_vdc()._vdisplay_source(),
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
        mf = _vdc().move_mouse_to_vql_target_and_focus_keyboard(photo_vql_target, ide=ide)
        if not mf.get("ok"):
            focus_error = mf.get("error") or mf.get("message")
    except Exception as exc:
        focus_error = str(exc)
        photo_vql_target = _vdc().get_vql_chat_target_from_photo()
    return photo_vql_target, focus_error


def _send_chat_resolve_chat_selector(
    *,
    ide: str,
    hints: dict[str, str],
    photo_vql_target: dict[str, Any] | None,
    focus_error: str | None,
) -> tuple[dict[str, str] | None, dict[str, Any] | None, dict[str, Any] | None]:
    selector, found = _vdc()._find_first_selector(ide=ide, selectors=_vdc()._chat_selectors_for(ide))
    if selector is not None:
        return selector, found, None

    found = _vdc()._resolve_vql_chat_target(ide, hints)
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
    selected, click_point, selector = _vdc()._send_chat_selector_click_point(found, selector)
    write_kwargs = _vdc()._send_chat_selector_write_kwargs(
        prompt, hints=hints, selector=selector, selected=selected, click_point=click_point
    )

    try:
        typed = _vdc()._control_set_value(**write_kwargs)
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
    submit_selector, submit_found = _vdc()._find_first_selector(
        ide=ide,
        selectors=_vdc()._submit_selectors_for(ide),
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
            submit_result = _vdc()._control_click(**click_kwargs)
            submitted = bool(submit_result.get("ok", True))
        except Exception as exc:
            submit_result = {"ok": False, "error": str(exc)}
    if not submitted:
        submit_result = _vdc()._submit_via_keyboard(ide=ide, submit=submit)
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
    effective_dry = _vdc()._dry_run() if dry_run is None else dry_run
    is_code = _vdc()._photo_vql_code_edit_enabled()

    result = _vdc()._send_chat_preflight(
        prompt, ide=ide, submit=submit, effective_dry=effective_dry, is_code=is_code
    )
    if result is not None:
        return result

    result = _vdc()._send_chat_try_photo_vql(
        prompt, ide=ide, submit=submit, effective_dry=effective_dry, is_code=is_code
    )
    if result is not None:
        return result

    result = _vdc()._send_chat_dry_run(prompt, ide=ide, submit=submit, effective_dry=effective_dry)
    if result is not None:
        return result

    if not _vdc().vdisplay_available():
        return {
            "ok": False,
            "backend": "vdisplay",
            "message": _vdc().vdisplay_missing_message(),
            "type": "error",
            "fallback_from": "plugin",
        }

    if _vdc()._auto_ide_control_enabled() and _vdc()._photo_vql_ide_capture_mismatch(ide=ide):
        _vdc().ensure_vdisplay_ide_control(ide=ide, source=_vdc()._vdisplay_source())

    result = _vdc()._send_chat_try_os_injector(prompt, ide=ide, submit=submit)
    if result is not None:
        return result

    result = _vdc()._send_chat_try_ide_prompt_fallback(prompt, ide=ide, submit=submit)
    if result is not None:
        return result

    return _vdc()._send_chat_semantic_vdisplay(prompt, ide=ide, submit=submit)
