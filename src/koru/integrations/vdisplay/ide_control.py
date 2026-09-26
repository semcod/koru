"""Window focus and semantic IDE control orchestration extracted from
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


def _focus_window_xdotool(*, title_contains: str) -> dict[str, Any]:
    return _vdc()._window_focus.focus_window_xdotool(title_contains=title_contains)


def _focus_window_xdotool_for_ide(*, ide: str) -> dict[str, Any]:
    return _vdc()._window_focus.focus_window_xdotool_for_ide(
        ide=ide, ide_hints=_vdc()._ide_hints, app_id=_vdc()._ide_prompt_app_id
    )


def _focus_window_gnome_shell(*, title_contains: str) -> dict[str, Any]:
    return _vdc()._window_focus.focus_window_gnome_shell(title_contains=title_contains)


def _focus_window_gnome_shell_for_ide(*, ide: str) -> dict[str, Any]:
    return _vdc()._window_focus.focus_window_gnome_shell_for_ide(
        ide=ide, ide_hints=_vdc()._ide_hints, app_id=_vdc()._ide_prompt_app_id
    )


def _click_map_region_center(
    map_path: str,
    *,
    source: str,
    region_id: str = "pycharm.ai_chat",
) -> dict[str, Any]:
    return _vdc()._window_focus.click_map_region_center(
        map_path,
        source=source,
        region_id=region_id,
        control_click=_vdc()._control_click,
    )


def _raise_alt_tab_enabled(*, ide: str = "auto") -> bool:
    return _vdc()._window_focus.raise_alt_tab_enabled(ide=ide)


def _alt_tab_window_cycle(*, cycles: int = 1, ide: str = "auto") -> dict[str, Any]:
    return _vdc()._window_focus.alt_tab_window_cycle(cycles=cycles, ide=ide)


def _attempt_focus_recovery_capture(*, ide: str, source: str) -> dict[str, Any]:
    """Alt+Tab cycles with re-capture until observe confirms target IDE or attempts exhausted."""
    if not _vdc()._raise_alt_tab_enabled(ide=ide):
        return {"ok": False, "skipped": True, "focus_recovery": {"ok": False, "skipped": True}}

    import time

    max_attempts = max(1, int(os.environ.get("KORU_VDISPLAY_FOCUS_RECOVERY_ATTEMPTS", "3") or "3"))
    attempts_log: list[dict[str, Any]] = []
    delay = float(os.environ.get("KORU_VDISPLAY_POST_FOCUS_CAPTURE_DELAY_S", "0.8"))

    for attempt_idx in range(max_attempts):
        recovery = _vdc()._alt_tab_window_cycle(cycles=1, ide=ide)
        attempts_log.append({"attempt": attempt_idx + 1, **recovery})
        if not recovery.get("ok"):
            continue
        time.sleep(delay)
        out = _vdc().refresh_photo_vql_sidecar(source=source, ide=ide)
        warn = out.get("ide_window_warning") or _vdc()._photo_vql_ide_window_warning(
            ide=ide,
            meta=_vdc().load_vql_metadata(str(out.get("vql") or ""), allow_stale=True),
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
    map_path = _vdc()._resolve_ide_prompt_map(app_id)
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
    if not _vdc()._auto_open_ide_enabled(ide=ide):
        return
    try:
        from vdisplay.ide_prompt import open_desktop_app

        opened = open_desktop_app(app_id, wait_seconds=2.0)
        result["steps"].append({"open": opened})
    except Exception as exc:
        result["steps"].append({"open": {"ok": False, "error": str(exc)}})


def _ide_control_raise_window(result: dict[str, Any], ide: str) -> None:
    """Raise the IDE window via gnome-shell, falling back to xdotool."""
    gnome_focus = _vdc()._focus_window_gnome_shell_for_ide(ide=ide)
    result["steps"].append({"gnome_raise": gnome_focus})
    if not gnome_focus.get("ok"):
        xdotool_focus = _vdc()._focus_window_xdotool_for_ide(ide=ide)
        if not xdotool_focus.get("skipped"):
            result["steps"].append({"xdotool_raise": xdotool_focus})


def _ide_control_region_raise(
    result: dict[str, Any], map_path: str | None, map_mismatch: dict[str, Any] | None, src: str
) -> None:
    """Click the calibrated map region center to raise the window (skipped on mismatch)."""
    if map_path and not map_mismatch:
        region_click = _vdc()._click_map_region_center(map_path, source=src)
        result["steps"].append({"region_raise": region_click})
    elif map_mismatch:
        result["steps"].append({"region_raise": {"ok": False, "skipped": True, **map_mismatch}})


def _ide_control_alt_tab(result: dict[str, Any], ide: str) -> None:
    """Cycle alt-tab to bring the IDE window forward, recording the step unless skipped."""
    alt_tab = _vdc()._alt_tab_window_cycle(
        cycles=int(os.environ.get("KORU_VDISPLAY_RAISE_ALT_TAB_CYCLES", "2")),
        ide=ide,
    )
    if not alt_tab.get("skipped"):
        result["steps"].append({"alt_tab": alt_tab})


def _ide_control_window_focus(result: dict[str, Any], hints: dict[str, str]) -> None:
    """Focus the IDE window via the control plane, recording the step."""
    try:
        focus_res = _vdc()._control_focus(
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
            fb_targets = _vdc()._map_raise_targets_for_ide(app_id, map_path) or ("prompt", "analyzing")
            for t in fb_targets[:2]:
                fb_click = _vdc()._control_click(backend="vision", map_path=map_path, map_target=t, source=src)
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
    for target in _vdc()._map_interior_targets_for_ide(app_id, map_path)[:1]:
        try:
            click = _vdc()._control_click(
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
    window_ok, open_ok, fallback_ok = _vdc()._ide_control_outcome_flags(result)
    # For JetBrains on rotated monitors (DP-2 etc), successful map/region/interior clicks bring the window forward
    # and focus the chat area (as seen in real DP-2 tests with ydotool + rotation mapping succeeding even when
    # strict window selector fails). Count as window_focused for better reporting and downstream logic.
    if (
        not window_ok
        and (interior_ok or fallback_ok)
        and _vdc()._canonical_ide(ide) in {"jetbrains", "pycharm", "idea"}
    ):
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
    app_id = _vdc()._ide_prompt_app_id(ide)
    src = source or _vdc()._vdisplay_source_for_ide(ide)
    os.environ["KORU_VDISPLAY_SOURCE"] = src
    os.environ.setdefault("VDISPLAY_CAPTURE_SOURCE", src)

    result: dict[str, Any] = {
        "ok": False,
        "ide": ide,
        "app_id": app_id,
        "source": src,
        "steps": [],
    }

    if _vdc()._dry_run():
        result.update({"ok": True, "dry_run": True, "skipped": True})
        return result
    if not _vdc().vdisplay_available():
        result["error"] = _vdc().vdisplay_missing_message()
        return result

    result["steps"].append({"dismiss_overview": _vdc()._dismiss_gnome_overview(reason="pre-control")})

    hints = _vdc()._ide_hints(ide)
    map_path, map_mismatch = _vdc()._ide_control_resolve_map(result, app_id, src)

    _vdc()._ide_control_open_ide(result, app_id, ide)
    _vdc()._ide_control_raise_window(result, ide)
    _vdc()._ide_control_region_raise(result, map_path, map_mismatch, src)
    _vdc()._ide_control_alt_tab(result, ide)
    _vdc()._ide_control_window_focus(result, hints)

    interior_ok = _vdc()._ide_control_focus_fallback(result, app_id, map_path, map_mismatch, src)

    if focus_interior and map_path and not map_mismatch:
        interior_ok = _vdc()._ide_control_focus_interior(result, app_id, map_path, src) or interior_ok

    result["steps"].append({"dismiss_overview": _vdc()._dismiss_gnome_overview(reason="post-control")})

    _vdc()._ide_control_finalize_result(
        result,
        ide=ide,
        map_path=map_path,
        map_mismatch=map_mismatch,
        focus_interior=focus_interior,
        interior_ok=interior_ok,
    )
    return result
