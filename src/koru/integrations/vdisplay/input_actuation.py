"""Agent control plumbing, keyboard submit and IDE-prompt/OS type-text
actuation extracted from ``vdisplay_client``.

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


def _agent_client():
    from vdisplay.client import AgentClient

    url = _vdc()._agent_url()
    if not url:
        raise RuntimeError("vdisplay agent URL is not configured")
    return AgentClient(url)


def _controls_find(**kwargs: Any) -> dict[str, Any]:
    _vdc()._load_vdisplay_control()
    if _vdc()._VDISPLAY_DIRECT and _vdc()._vdisplay_control:
        return _vdc()._vdisplay_control.controls_find(**kwargs)
    return _vdc()._agent_client().find_controls(kwargs)


def _control_focus(**kwargs: Any) -> dict[str, Any]:
    _vdc()._load_vdisplay_control()
    if _vdc()._VDISPLAY_DIRECT and _vdc()._vdisplay_control:
        return _vdc()._vdisplay_control.control_focus(**kwargs)
    return _vdc()._agent_client().focus_control(kwargs)


def _control_set_value(**kwargs: Any) -> dict[str, Any]:
    _vdc()._load_vdisplay_control()
    if _vdc()._VDISPLAY_DIRECT and _vdc()._vdisplay_control:
        return _vdc()._vdisplay_control.control_set_value(**kwargs)
    return _vdc()._agent_client().set_control_value(kwargs)


def _control_click(**kwargs: Any) -> dict[str, Any]:
    _vdc()._load_vdisplay_control()
    if _vdc()._VDISPLAY_DIRECT and _vdc()._vdisplay_control:
        return _vdc()._vdisplay_control.control_click(**kwargs)
    return _vdc()._agent_client().invoke_control(kwargs)


def _find_first_selector(
    *,
    ide: str,
    selectors: tuple[dict[str, str], ...],
    backend: str = "auto",
    vql_fallback: bool = True,
) -> tuple[dict[str, str] | None, dict[str, Any] | None]:
    hints = _vdc()._ide_hints(ide)
    base = {
        "backend": backend,
        "app": hints.get("app"),
        "window_title": hints.get("window_title_contains"),
    }
    last_error: dict[str, Any] | None = None
    for spec in selectors:
        payload = {**base, **spec}
        try:
            found = _vdc()._controls_find(**payload)
        except Exception as exc:
            last_error = {"ok": False, "error": str(exc), "selector": spec}
            continue
        if found.get("ok") and int(found.get("count") or 0) > 0:
            return spec, found
        last_error = found

    # VQL fallback: if vision found nothing, use explicit click_center from loaded VQL
    # (fresh 31-elem capture or our analysis with decision_data + mouse coords for JetBrains/Cursor)
    if vql_fallback:
        vql = _vdc().load_vql_metadata()
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
    if _vdc()._canonical_ide(ide) == "cursor":
        return False
    return submit


def _submit_via_keyboard(*, ide: str, submit: bool) -> dict[str, Any] | None:
    if not submit:
        return None

    if not _vdc()._effective_submit_enabled(submit=submit, ide=ide):
        return {"ok": False, "skipped": True, "reason": "paste-only mode"}

    canon = _vdc()._canonical_ide(ide)
    app_id = _vdc()._ide_prompt_app_id(ide)
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
    app_id = _vdc()._ide_prompt_app_id(ide)
    src = source or _vdc()._vdisplay_source_for_ide(ide)
    map_path = _vdc()._resolve_ide_prompt_map(app_id)
    if map_path:
        try:
            from vdisplay.desktop_apps import map_submit_target_candidates

            for map_target in map_submit_target_candidates(app_id):
                try:
                    click = _vdc()._control_click(
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
    result = _vdc()._submit_via_keyboard(ide=ide, submit=True)
    return result or {"ok": False, "error": "submit unavailable"}


def _ide_prompt_app_id(ide: str) -> str:
    canon = _vdc()._canonical_ide(ide)
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
    map_target = _vdc()._ide_map_message_target(app_id)
    source = _vdc()._vdisplay_source_for_ide(ide)
    result: dict[str, Any] = {
        "ok": False,
        "backend": "vdisplay+ide-prompt",
        "fallback": "map-click-paste",
        "map_path": map_path,
        "map_target": map_target,
        "source": source,
    }

    try:
        click_res = _vdc()._control_click(
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
    paste_res = _vdc()._type_text_at_vql_coords(
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
    app_id = _vdc()._ide_prompt_app_id(ide)
    map_path = _vdc()._resolve_ide_prompt_map(app_id)
    if not map_path and _vdc()._canonical_ide(ide) not in {"jetbrains", "pycharm"}:
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
            fallback = _vdc()._type_text_via_ide_map_fallback(
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
                    sub = _vdc()._submit_via_keyboard(ide=ide, submit=True)
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


def _ydotool_click_capture_local(*, x: int, y: int, source: str) -> dict[str, Any]:
    """Direct ydotool move+click when vdisplay vision point click fails."""
    try:
        from vdisplay.capture import compile_capture_coordinate_map
        from vdisplay.input.coords import global_pointer_coords
        from vdisplay.input.linux_ydotool import LinuxYdotoolInput

        capture_meta = _vdc()._enrich_capture_meta_for_pointer(_vdc()._photo_capture_meta_for_source(source), source)
        coordinate_map = compile_capture_coordinate_map(capture_meta, source=source)
        # Deterministic own-uinput-ABS positioning (opt-in): a cached per-monitor
        # affine converts capture pixel -> ABS command. Preferred over ydotool's
        # opaque space on multi-monitor HiDPI. Falls back below on failure.
        if _vdc()._abs_pointer_enabled():
            abs_res = _vdc()._abs_pointer_click(x=x, y=y, source=source)
            if abs_res is not None and abs_res.get("ok"):
                return abs_res
        # Closed-loop adaptive positioning (opt-in): measure + correct instead of
        # trusting the absolute mapping. Falls back to open-loop below on failure.
        if _vdc()._adaptive_pointer_enabled():
            adaptive = _vdc()._adaptive_position_pointer(x=x, y=y, source=source, capture_meta=capture_meta, ide="auto")
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
            "coordinate_map": coordinate_map.to_dict(),
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
    if _vdc()._dry_run():
        return blocking_warnings
    is_code_edit = _vdc()._photo_vql_code_edit_enabled() or str(target_for_log.get("role") or "").lower() == "editor"
    blocking_warnings.extend(
        _vdc()._validate_chat_coords_for_ide(
            x=int(x),
            y=int(y),
            ide=ide,
            target=target_for_log,
            is_code_edit=is_code_edit,
        )
    )
    blocking_warnings.extend(
        _vdc()._type_text_plan_validation_warnings(
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
    pos_log = _vdc()._log_vql_cursor_positioning_at_command(
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
        atspi_res = _vdc()._control_set_value(
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
    pos_log = _vdc()._log_vql_cursor_positioning_at_command(
        target_for_log,
        stage="type_text_at_vql_coords_must_click_for_chat",
        ide=ide,
        source=source,
        final_local={"x": x, "y": y},
        vql_file=vql_file_for_log if isinstance(vql_file_for_log, str) else None,
        command_plan=command_plan,
    )
    result["cursor_positioning"] = pos_log
    ydotool_click = _vdc()._ydotool_click_capture_local(x=x, y=y, source=source)
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
            click_res = _vdc()._control_click(**payload)
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
            paste_log = _vdc()._log_vql_cursor_positioning_at_command(
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


def _type_text_prepare_click_context(
    *,
    x: int,
    y: int,
    ide: str,
    focus_ok: bool,
    focus_res: dict[str, Any] | None,
    force_point_click: bool,
    vql_target: dict[str, Any] | None,
) -> tuple[dict[str, Any], bool, dict[str, Any]]:
    hints = _vdc()._ide_hints(ide) if ide and ide != "auto" else {}
    jetbrains = _vdc()._canonical_ide(ide) in {"jetbrains", "pycharm", "idea"}
    must_click = force_point_click or jetbrains or not focus_ok
    target_for_log = vql_target or (focus_res or {}).get("vql_target") or {
        "click_center": {"x": x, "y": y},
        "note": "pre-type chat write",
    }
    return hints, must_click, target_for_log


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
    hints, must_click, target_for_log = _vdc()._type_text_prepare_click_context(
        x=x,
        y=y,
        ide=ide,
        focus_ok=focus_ok,
        focus_res=focus_res,
        force_point_click=force_point_click,
        vql_target=vql_target,
    )
    result: dict[str, Any] = {"ok": False, "coords": {"x": x, "y": y}}
    blocking_warnings = _vdc()._type_text_blocking_warnings(
        x=x, y=y, ide=ide, target_for_log=target_for_log, command_plan=command_plan
    )
    if blocking_warnings:
        return _vdc()._type_text_blocked_result(
            result,
            blocking_warnings=blocking_warnings,
            target_for_log=target_for_log,
            command_plan=command_plan,
            ide=ide,
            x=x,
            y=y,
        )

    if _vdc()._dry_run() or not _vdc().vdisplay_available():
        return _vdc()._type_text_dry_run_result(
            result,
            value,
            x=x,
            y=y,
            ide=ide,
            source=source,
            target_for_log=target_for_log,
            command_plan=command_plan,
        )

    if _vdc()._type_text_try_atspi_set_value(
        result, value, hints=hints, focus_ok=focus_ok, focus_res=focus_res
    ):
        return result

    click_res = None
    if must_click:
        click_res = _vdc()._type_text_must_click(
            result,
            x=x,
            y=y,
            ide=ide,
            source=source,
            target_for_log=target_for_log,
            command_plan=command_plan,
        )
    if click_res is None and not focus_ok:
        _vdc()._type_text_fallback_click(result, x=x, y=y, source=source, hints=hints)

    return _vdc()._type_text_paste_or_type(
        result,
        value,
        x=x,
        y=y,
        ide=ide,
        source=source,
        target_for_log=target_for_log,
        command_plan=command_plan,
    )
