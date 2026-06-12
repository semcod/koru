"""Single source of truth for photo-VQL capture guards (IDE title / mismatch)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any


def ide_mismatch_allowed() -> bool:
    return os.environ.get("KORU_VDISPLAY_ALLOW_IDE_MISMATCH", "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def allow_prepare_map_on_mismatch() -> bool:
    """Prepare/focus may use calibrated map clicks to raise the IDE before re-capture."""
    if ide_mismatch_allowed():
        return True
    return os.environ.get("KORU_VDISPLAY_ALLOW_MAP_ON_MISMATCH", "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def allow_prepare_surface_on_capture_error() -> bool:
    """Prepare may record desktop-probe surface bounds when screenshot/VQL fails."""
    if ide_mismatch_allowed():
        return True
    return os.environ.get("KORU_VDISPLAY_ALLOW_SURFACE_ON_CAPTURE_ERROR", "1").strip().lower() not in {
        "0",
        "false",
        "no",
        "off",
    }


def allow_surface_only_actuation() -> bool:
    """Unsafe legacy override: allow typing from surface bounds without confirmed photo/VQL."""
    if ide_mismatch_allowed():
        return True
    return os.environ.get("KORU_VDISPLAY_ALLOW_SURFACE_ONLY_ACTUATION", "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def allow_actuation_on_capture_mismatch() -> bool:
    """When false (default), abort drive typing/clicks on unconfirmed IDE capture."""
    return ide_mismatch_allowed()


def competing_ide_label_from_warning(mismatch: dict[str, Any]) -> str | None:
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


def drive_blocked_on_capture_mismatch(
    *,
    ide: str,
    mismatch: dict[str, Any],
    dry_run: bool = False,
) -> dict[str, Any] | None:
    if dry_run or allow_actuation_on_capture_mismatch():
        return None
    competing = competing_ide_label_from_warning(mismatch)
    focus_hint = (
        f"Minimize or move {competing} off the capture monitor, focus the target IDE, then retry."
        if competing
        else "Focus the target IDE on the capture monitor, confirm window title in observe/capture, then retry."
    )
    return {
        "ok": False,
        "backend": "vdisplay+capture-blocked",
        "type": "blocked",
        "capture_confirmed": False,
        "ide_window_warning": mismatch,
        "competing_ide": competing,
        "error": str(mismatch.get("message") or "capture does not match requested IDE"),
        "hint": (
            f"{focus_hint} "
            "Set KORU_VDISPLAY_ALLOW_MAP_ON_MISMATCH=1 for map fallback or "
            "KORU_VDISPLAY_ALLOW_SURFACE_ON_CAPTURE_ERROR=1 for desktop surface bounds."
        ),
        "ide": ide,
    }


@dataclass
class CaptureGuard:
    confirmed: bool
    ready: bool
    mismatch: dict[str, Any] | None
    competing_ide: str | None
    body_false_positive: bool
    map_only_fallback: bool
    surface_only_fallback: bool
    allow_actuation: bool
    blocked: dict[str, Any] | None

    @classmethod
    def from_observe(
        cls,
        *,
        ide: str,
        confirmed: bool | None,
        ide_window_warning: dict[str, Any] | None,
        body_false_positive: bool = False,
        map_only_fallback: bool = False,
        surface_only_fallback: bool = False,
        capture_error: bool = False,
        ide_control: dict[str, Any] | None = None,
        dry_run: bool = False,
    ) -> CaptureGuard:
        if confirmed is None:
            confirmed = False if capture_error else not bool(ide_window_warning)

        allow_map = allow_prepare_map_on_mismatch()
        allow_surface = allow_prepare_surface_on_capture_error()
        map_fallback = bool(map_only_fallback)
        if (
            not confirmed
            and ide_control is not None
            and (ide_control.get("map_actuation_ok") or ide_control.get("interior_focused"))
            and allow_map
        ):
            map_fallback = True

        surface_fallback = bool(surface_only_fallback)
        if (
            not surface_fallback
            and allow_surface
            and capture_error
            and confirmed
        ):
            surface_fallback = True

        surface_ready = surface_fallback and allow_surface_only_actuation()
        ready = bool(confirmed) or map_fallback or surface_ready
        blocked: dict[str, Any] | None = None
        if not confirmed and not map_fallback and not surface_ready:
            mismatch = ide_window_warning or {"message": "capture does not match requested IDE"}
            blocked = drive_blocked_on_capture_mismatch(ide=ide, mismatch=mismatch, dry_run=dry_run)

        competing = None
        if ide_window_warning:
            competing = competing_ide_label_from_warning(ide_window_warning)

        return cls(
            confirmed=bool(confirmed),
            ready=ready and blocked is None,
            mismatch=ide_window_warning,
            competing_ide=competing,
            body_false_positive=body_false_positive,
            map_only_fallback=map_fallback,
            surface_only_fallback=surface_fallback,
            allow_actuation=allow_map,
            blocked=blocked,
        )

    def apply_to_prepare_out(
        self,
        out: dict[str, Any],
        *,
        ide_control: dict[str, Any] | None,
        capture_error: bool = False,
    ) -> dict[str, Any]:
        out["capture_confirmed"] = self.confirmed
        out["capture_ready"] = self.ready
        if self.body_false_positive:
            out["body_false_positive"] = True
        if self.map_only_fallback:
            out["map_only_fallback"] = True
            if out.get("ide_window_warning"):
                out["ide_window_warning_map_fallback"] = out["ide_window_warning"]
        if self.surface_only_fallback:
            out["surface_only_fallback"] = True
            if out.get("ide_window_warning"):
                out["ide_window_warning_surface_fallback"] = out["ide_window_warning"]
        if self.competing_ide:
            out["competing_ide"] = self.competing_ide

        if ide_control is not None:
            if self.mismatch:
                ide_control["capture_confirmed"] = False
                ide_control["visual_guard_failed"] = True
                if ide_control.get("map_actuation_ok") or ide_control.get("interior_focused"):
                    ide_control["confirmation_bias_risk"] = (
                        "Map/interior actuation succeeded but observe capture still shows a different IDE."
                    )
            elif not self.confirmed and (ide_control.get("map_actuation_ok") or ide_control.get("interior_focused")):
                ide_control["capture_confirmed"] = False
                ide_control["visual_guard_failed"] = True
                ide_control["confirmation_bias_risk"] = (
                    "Map/interior actuation succeeded but observe capture was not confirmed."
                )
            else:
                ide_control["capture_confirmed"] = self.confirmed
                ide_control["visual_guard_failed"] = False

        if self.blocked:
            out["ok"] = False
            out["capture_ready"] = False
            if not capture_error or not out.get("error"):
                out["error"] = self.blocked.get("error")
            if not capture_error or not out.get("hint"):
                out["hint"] = self.blocked.get("hint")
        elif self.ready:
            out["ok"] = True
        return out


__all__ = [
    "CaptureGuard",
    "allow_actuation_on_capture_mismatch",
    "allow_prepare_map_on_mismatch",
    "allow_prepare_surface_on_capture_error",
    "allow_surface_only_actuation",
    "competing_ide_label_from_warning",
    "drive_blocked_on_capture_mismatch",
    "ide_mismatch_allowed",
]
