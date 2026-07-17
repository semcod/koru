"""Window raise/focus helpers extracted from ``vdisplay_client``.

X11 (xdotool), GNOME Shell Eval, map-region click, and Alt+Tab recovery used
before photo-VQL capture. IDE-specific needle lists take injected hint/app-id
callables so this module stays free of the vdisplay_client monolith.
"""

from __future__ import annotations

import os
from collections.abc import Callable
from typing import Any


def _canonical_ide(ide: str) -> str:
    try:
        from koruide.ide import canonical_autopilot_ide_id

        return canonical_autopilot_ide_id(ide) or ide.strip().lower()
    except Exception:
        return ide.strip().lower()


def focus_window_xdotool(*, title_contains: str) -> dict[str, Any]:
    """Raise/focus window by title substring (X11 xdotool fallback)."""
    import subprocess

    needle = title_contains.strip()
    if not needle:
        return {"ok": False, "method": "xdotool", "error": "empty title needle"}
    try:
        proc = subprocess.run(
            ["xdotool", "search", "--name", needle],
            capture_output=True,
            text=True,
            timeout=3.0,
            check=False,
        )
        ids = [line.strip() for line in (proc.stdout or "").splitlines() if line.strip().isdigit()]
        if not ids and proc.returncode != 0:
            return {"ok": False, "method": "xdotool", "error": proc.stderr or "search failed"}
        if not ids:
            return {"ok": False, "method": "xdotool", "error": f"no window matching {needle!r}"}
        wid = ids[-1]
        subprocess.run(
            ["xdotool", "windowactivate", "--sync", wid],
            capture_output=True,
            timeout=3.0,
            check=False,
        )
        subprocess.run(["xdotool", "windowraise", wid], capture_output=True, timeout=3.0, check=False)
        return {"ok": True, "method": "xdotool", "window_id": wid, "needle": needle}
    except FileNotFoundError:
        return {"ok": False, "method": "xdotool", "error": "xdotool not installed", "skipped": True}
    except Exception as exc:
        return {"ok": False, "method": "xdotool", "error": str(exc)}


def _needles_for_ide(
    ide: str,
    *,
    extra: tuple[str, ...],
    ide_hints: Callable[[str], dict[str, str]],
    app_id: Callable[[str], str],
    lower: bool = False,
) -> list[str]:
    hints = ide_hints(ide)
    needles: list[str] = []
    for candidate in (str(hints.get("window_title_contains") or ""), app_id(ide), *extra):
        token = candidate.strip().lower() if lower else candidate.strip()
        if token and token not in needles:
            needles.append(token)
    return needles


def focus_window_xdotool_for_ide(
    *,
    ide: str,
    ide_hints: Callable[[str], dict[str, str]],
    app_id: Callable[[str], str],
) -> dict[str, Any]:
    needles = _needles_for_ide(
        ide,
        extra=("PyCharm", "IntelliJ", "JetBrains"),
        ide_hints=ide_hints,
        app_id=app_id,
    )
    attempts: list[dict[str, Any]] = []
    for needle in needles:
        res = focus_window_xdotool(title_contains=needle)
        attempts.append({"needle": needle, **res})
        if res.get("ok"):
            return {"ok": True, "method": "xdotool", "needle": needle, "attempts": attempts, **res}
    return {
        "ok": False,
        "method": "xdotool",
        "error": "no window matched any title needle",
        "attempts": attempts,
    }


def focus_window_gnome_shell(*, title_contains: str) -> dict[str, Any]:
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
        return {
            "ok": False,
            "method": "gnome-shell-eval",
            "error": text or proc.stderr or "eval failed",
        }
    except Exception as exc:
        return {"ok": False, "method": "gnome-shell-eval", "error": str(exc)}


def focus_window_gnome_shell_for_ide(
    *,
    ide: str,
    ide_hints: Callable[[str], dict[str, str]],
    app_id: Callable[[str], str],
) -> dict[str, Any]:
    """Try GNOME Shell raise with IDE-specific title needles."""
    needles = _needles_for_ide(
        ide,
        extra=("pycharm", "intellij", "jetbrains", "webstorm", "goland"),
        ide_hints=ide_hints,
        app_id=app_id,
        lower=True,
    )
    attempts: list[dict[str, Any]] = []
    for needle in needles:
        res = focus_window_gnome_shell(title_contains=needle)
        attempts.append({"needle": needle, **res})
        if res.get("ok"):
            return {
                "ok": True,
                "method": "gnome-shell-eval",
                "title": res.get("title"),
                "needle": needle,
                "attempts": attempts,
            }
    return {
        "ok": False,
        "method": "gnome-shell-eval",
        "error": "no window matched any title needle",
        "attempts": attempts,
    }


def click_map_region_center(
    map_path: str,
    *,
    source: str,
    region_id: str = "pycharm.ai_chat",
    control_click: Callable[..., dict[str, Any]],
) -> dict[str, Any]:
    """Click the center of a GUI map region (raises native Wayland window)."""
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
        cy = int(bounds.y + min(max(bounds.height * 0.22, 48), bounds.height - 48))
        click = control_click(
            backend="vision",
            x=cx,
            y=cy,
            source=source,
            map_path=map_path,
        )
        return {
            "ok": bool(click.get("ok", True)),
            "region_id": region.id,
            "coords": {"x": cx, "y": cy},
            "click": click,
        }
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def raise_alt_tab_enabled(*, ide: str = "auto") -> bool:
    raw = os.environ.get("KORU_VDISPLAY_RAISE_ALT_TAB", "").strip().lower()
    if raw in {"1", "true", "yes", "on"}:
        return True
    if raw in {"0", "false", "no", "off"}:
        return False
    return _canonical_ide(ide) in {"jetbrains", "pycharm", "idea"}


def alt_tab_window_cycle(*, cycles: int = 1, ide: str = "auto") -> dict[str, Any]:
    """Optional ydotool Alt+Tab cycles to raise a background window."""
    if not raise_alt_tab_enabled(ide=ide):
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


# Historical private names (thin aliases; for_ide variants need wrappers in client).
_focus_window_xdotool = focus_window_xdotool
_focus_window_gnome_shell = focus_window_gnome_shell
_raise_alt_tab_enabled = raise_alt_tab_enabled
_alt_tab_window_cycle = alt_tab_window_cycle

__all__ = [
    "alt_tab_window_cycle",
    "click_map_region_center",
    "focus_window_gnome_shell",
    "focus_window_gnome_shell_for_ide",
    "focus_window_xdotool",
    "focus_window_xdotool_for_ide",
    "raise_alt_tab_enabled",
    "_alt_tab_window_cycle",
    "_focus_window_gnome_shell",
    "_focus_window_xdotool",
    "_raise_alt_tab_enabled",
]
