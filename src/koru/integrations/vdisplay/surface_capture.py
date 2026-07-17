"""Surface-registry capture confirmation extracted from ``vdisplay_client``.

On Wayland/JetBrains, X11 window titles may be missing; the correlated surface
registry is used to confirm the IDE is on the captured monitor. Re-exported
from ``vdisplay_client`` for backward-compatible imports.
"""

from __future__ import annotations

import json
import os
from typing import Any


def _canonical_ide(ide: str) -> str:
    try:
        from koruide.ide import canonical_autopilot_ide_id

        return canonical_autopilot_ide_id(ide) or ide.strip().lower()
    except Exception:
        return ide.strip().lower()


def surface_confirms_ide_capture(
    *,
    ide: str,
    source: str,
    desktop_probe: dict[str, Any] | None,
) -> bool:
    """Native Wayland JetBrains may lack X11/AT-SPI window titles — trust surface registry."""
    if not desktop_probe:
        return False
    canon = _canonical_ide(ide)
    if canon not in {"jetbrains", "pycharm", "idea"}:
        return False
    best = desktop_probe.get("ide_surface_best")
    if not isinstance(best, dict):
        return False
    monitor = str(best.get("monitor_name") or "")
    if not monitor or monitor != source:
        return False
    name = str(best.get("display_name") or "").lower()
    if "toolbox" in name:
        return False
    stack = str(best.get("stack") or "")
    return stack in {"jetbrains_xwayland", "wayland_native", "x11", "xwayland"}


def clear_surface_overridden_vql_staleness(out: dict[str, Any]) -> None:
    """Do not reject a real VQL only because OCR missed a Wayland/XWayland title."""
    if int(out.get("main_vql_layers") or out.get("elements") or 0) <= 0:
        return
    freshness = out.get("freshness")
    if not isinstance(freshness, dict):
        return
    reasons = [str(item) for item in freshness.get("reasons") or []]
    overridden = {
        "ide_window_mismatch",
        "capture_validation_failed",
        "missing_window_title",
        "missing_canvas_size",
    }
    remaining = [reason for reason in reasons if reason not in overridden]
    if len(remaining) == len(reasons):
        return
    freshness["surface_confirmation_override"] = True
    freshness["overridden_reasons"] = [reason for reason in reasons if reason in overridden]
    freshness["reasons"] = remaining
    freshness["stale"] = bool(remaining)
    if not remaining:
        freshness.pop("ide_window_warning", None)
    out["sidecar_stale"] = bool(remaining)


def apply_surface_capture_error_fallback(out: dict[str, Any], best_prov: dict[str, Any]) -> None:
    """Surface-only confirmation when the capture itself errored (no confirmed pixels)."""
    out["capture_confirmed"] = False
    out["capture_matches_ide"] = False
    out["capture_confirmation_source"] = "ide_surface_best_surface_only"
    out["surface_probe_confirmed"] = True
    out["surface_only_fallback"] = True
    prov = dict(out.get("capture_provenance") or {})
    prov["capture_confirmed"] = False
    prov["surface_confirmed"] = True
    prov["surface_probe_confirmed"] = True
    if best_prov:
        prov["ide_surface_best"] = best_prov
    out["capture_provenance"] = prov
    out["capture_ready"] = False
    os.environ["KORU_VDISPLAY_SURFACE_ONLY_FALLBACK"] = "1"
    os.environ.pop("KORU_VDISPLAY_CAPTURE_MATCHES_IDE", None)


def apply_surface_capture_confirmed(out: dict[str, Any], best_prov: dict[str, Any]) -> None:
    """Mark the capture as surface-confirmed for the requested IDE."""
    out["capture_confirmed"] = True
    out["capture_matches_ide"] = True
    out["capture_confirmation_source"] = "ide_surface_best"
    prov = dict(out.get("capture_provenance") or {})
    prov["capture_confirmed"] = True
    prov["surface_confirmed"] = True
    if best_prov:
        prov["ide_surface_best"] = best_prov
    out["capture_provenance"] = prov
    out.pop("ide_window_warning", None)
    os.environ["KORU_VDISPLAY_CAPTURE_MATCHES_IDE"] = "1"
    if out.get("png"):
        out["ok"] = True
        out.pop("error", None)
    clear_surface_overridden_vql_staleness(out)


def _surface_best_provenance(desktop_probe: dict[str, Any]) -> dict[str, Any]:
    best = desktop_probe.get("ide_surface_best") or {}
    if not isinstance(best, dict):
        return {}
    return {
        "display_name": best.get("display_name"),
        "monitor_name": best.get("monitor_name"),
        "stack": best.get("stack"),
        "pid": best.get("pid"),
    }


def apply_surface_capture_confirmation(
    out: dict[str, Any],
    *,
    ide: str,
    source: str,
    desktop_probe: dict[str, Any],
    capture_error: bool = False,
) -> None:
    if out.get("capture_confirmed") is True and not capture_error:
        return
    if out.get("competing_ide"):
        return
    warn = out.get("ide_window_warning")
    if isinstance(warn, dict) and warn.get("system_overlay"):
        out["capture_confirmed"] = False
        out["capture_matches_ide"] = False
        out["capture_ready"] = False
        os.environ.pop("KORU_VDISPLAY_CAPTURE_MATCHES_IDE", None)
        return
    if isinstance(warn, dict) and warn.get("competing_detected"):
        return
    if not surface_confirms_ide_capture(ide=ide, source=source, desktop_probe=desktop_probe):
        return
    best_prov = _surface_best_provenance(desktop_probe)
    if capture_error:
        apply_surface_capture_error_fallback(out, best_prov)
        return
    apply_surface_capture_confirmed(out, best_prov)


def write_surface_capture_confirmation_sidecar(
    out: dict[str, Any], *, ide: str, vql_path: str
) -> None:
    """Rewrite the VQL sidecar metadata with the surface-confirmed capture validation."""
    with open(vql_path, encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, dict):
        return
    metadata = data.get("metadata") if isinstance(data.get("metadata"), dict) else {}
    original = (
        metadata.get("capture_validation")
        if isinstance(metadata.get("capture_validation"), dict)
        else None
    )
    provenance = out.get("capture_provenance") if isinstance(out.get("capture_provenance"), dict) else {}
    surface = (
        provenance.get("ide_surface_best")
        if isinstance(provenance.get("ide_surface_best"), dict)
        else {}
    )
    validation: dict[str, Any] = {
        "expected_ide": _canonical_ide(ide),
        "capture_confirmed": True,
        # Surface registry proves monitor ownership, not a safe chat target.
        "ok_for_capture": True,
        "ok_for_drive": bool((original or {}).get("ok_for_drive")),
        "reasons": [],
        "window_titles": list(
            (original or {}).get("window_titles") or provenance.get("window_titles") or []
        ),
        "surface_confirmed": True,
        "confirmation_source": "ide_surface_best",
        "ide_surface_best": surface,
    }
    if original:
        validation["original_capture_validation"] = original
    metadata["capture_validation"] = validation
    metadata["surface_capture_confirmation"] = {
        "confirmed": True,
        "source": "ide_surface_best",
        "ide": _canonical_ide(ide),
        "ide_surface_best": surface,
    }
    data["metadata"] = metadata
    with open(vql_path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)
    out["capture_validation"] = validation
    out["vql_surface_confirmation_persisted"] = True


def persist_surface_capture_confirmation_to_vql(out: dict[str, Any], *, ide: str) -> None:
    """Persist surface-confirmed IDE match into the observe VQL sidecar for later processes."""
    if out.get("capture_confirmation_source") != "ide_surface_best":
        return
    warn = out.get("ide_window_warning")
    if isinstance(warn, dict) and warn.get("system_overlay"):
        return
    vql_path = str(out.get("vql") or "").strip()
    if not vql_path or not os.path.isfile(vql_path):
        return
    try:
        write_surface_capture_confirmation_sidecar(out, ide=ide, vql_path=vql_path)
    except Exception as exc:
        out["vql_surface_confirmation_persist_error"] = str(exc)


# Historical private names (vdisplay_client re-exports).
_surface_confirms_ide_capture = surface_confirms_ide_capture
_clear_surface_overridden_vql_staleness = clear_surface_overridden_vql_staleness
_apply_surface_capture_error_fallback = apply_surface_capture_error_fallback
_apply_surface_capture_confirmed = apply_surface_capture_confirmed
_apply_surface_capture_confirmation = apply_surface_capture_confirmation
_write_surface_capture_confirmation_sidecar = write_surface_capture_confirmation_sidecar
_persist_surface_capture_confirmation_to_vql = persist_surface_capture_confirmation_to_vql

__all__ = [
    "apply_surface_capture_confirmation",
    "apply_surface_capture_confirmed",
    "apply_surface_capture_error_fallback",
    "clear_surface_overridden_vql_staleness",
    "persist_surface_capture_confirmation_to_vql",
    "surface_confirms_ide_capture",
    "write_surface_capture_confirmation_sidecar",
    "_apply_surface_capture_confirmation",
    "_apply_surface_capture_confirmed",
    "_apply_surface_capture_error_fallback",
    "_clear_surface_overridden_vql_staleness",
    "_persist_surface_capture_confirmation_to_vql",
    "_surface_confirms_ide_capture",
    "_write_surface_capture_confirmation_sidecar",
]
