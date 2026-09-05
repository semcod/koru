"""Normalize photo-VQL drive results without importing the desktop facade.

The caller supplies current policy callbacks. This keeps environment and surface
policy in the existing vdisplay component while making result shaping testable
without desktop capture, control, or orchestration dependencies.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class DriveResultPolicy:
    """Runtime policy hooks required by result normalization."""

    trusted_visual_target_id: Callable[[str], bool]
    surface_target_safe: Callable[..., bool]
    allow_capture_mismatch: Callable[[], bool]
    allow_map_source_mismatch: Callable[[], bool]


def _photo_vql_drive_out_base(photo_res: dict[str, Any], *, ide: str, submit: bool) -> dict[str, Any]:
    """Build the base send_chat-shaped result dict for a photo-VQL drive outcome."""
    edit = photo_res.get("edit") or {}
    edit_message = edit.get("message")
    if not edit_message and edit.get("method"):
        edit_message = f"typed via {edit['method']}"
    return {
        "ok": bool(photo_res.get("ok")),
        "backend": photo_res.get("backend", "vdisplay+photo-vql"),
        "message": (
            edit_message
            or (photo_res.get("focus") or {}).get("message")
            or f"photo VQL {photo_res.get('target', 'edit')} at {photo_res.get('coords')}"
        ),
        "type": "drive",
        "fallback_from": "plugin",
        "ide": ide,
        "submit": submit,
        "photo_vql": photo_res,
        "coords": photo_res.get("coords"),
        "target": photo_res.get("target"),
        "is_code_edit": photo_res.get("is_code_edit", True),
    }


def _photo_vql_drive_map_target_id(photo_res: dict[str, Any]) -> str:
    """Best-effort target id from drive result (vql_target or nested photo_vql.vql_target)."""
    return str((photo_res.get("vql_target") or photo_res.get("photo_vql", {}).get("vql_target") or {}).get("id") or "")


def _photo_vql_drive_surface_trusted(photo_res: dict[str, Any], policy: DriveResultPolicy) -> bool:
    """Surface-bounds trust check for the drive result's vql_target/command plan."""
    return policy.surface_target_safe(
        target=photo_res.get("vql_target") if isinstance(photo_res.get("vql_target"), dict) else None,
        method=str((photo_res.get("vql_command_plan") or {}).get("selection_method") or ""),
        command_plan=photo_res.get("vql_command_plan") if isinstance(photo_res.get("vql_command_plan"), dict) else None,
    )


def _photo_vql_drive_verified_false_blocks(photo_res: dict[str, Any], policy: DriveResultPolicy) -> bool:
    """True when verified=False must force ok=False (no trusted-target override applies)."""
    return photo_res.get("verified") is False and not (
        (photo_res.get("edit") or {}).get("ok")
        and (
            policy.trusted_visual_target_id(_photo_vql_drive_map_target_id(photo_res))
            or _photo_vql_drive_surface_trusted(photo_res, policy)
        )
        and (policy.allow_capture_mismatch() or _photo_vql_drive_surface_trusted(photo_res, policy))
    )


def _apply_photo_vql_capture_confirmed(
    out: dict[str, Any], photo_res: dict[str, Any], policy: DriveResultPolicy
) -> None:
    """Propagate capture_confirmed from the drive result, gating ok on unconfirmed captures."""
    if photo_res.get("capture_confirmed") is False:
        map_id = _photo_vql_drive_map_target_id(photo_res)
        edit_ok = bool((photo_res.get("edit") or {}).get("ok"))
        if not (policy.trusted_visual_target_id(map_id) and edit_ok and policy.allow_capture_mismatch()):
            out["ok"] = False
            out["capture_confirmed"] = False
        else:
            out["capture_confirmed"] = False
    elif photo_res.get("capture_confirmed") is True:
        out["capture_confirmed"] = True


def _apply_photo_vql_plan_inference_gate(
    out: dict[str, Any], photo_res: dict[str, Any], policy: DriveResultPolicy
) -> None:
    """Force ok=False when the command plan's inference failed without a trusted override."""
    plan = photo_res.get("vql_command_plan") or {}
    surface_trusted = policy.surface_target_safe(
        target=photo_res.get("vql_target") if isinstance(photo_res.get("vql_target"), dict) else None,
        method=str(plan.get("selection_method") or ""),
        command_plan=plan,
    )
    if (
        plan.get("inference_ok") is False
        and not policy.allow_capture_mismatch()
        and not (surface_trusted and bool((photo_res.get("edit") or {}).get("ok")))
    ):
        out["ok"] = False


def _apply_photo_vql_map_mismatch_gate(
    out: dict[str, Any], photo_res: dict[str, Any], policy: DriveResultPolicy
) -> None:
    """Force ok=False and surface the mismatch when the map targets a different monitor."""
    plan = photo_res.get("vql_command_plan") or {}
    map_source_mismatch = photo_res.get("map_capture_mismatch") or plan.get("map_capture_mismatch")
    if map_source_mismatch and not policy.allow_map_source_mismatch():
        out["ok"] = False
        out["map_capture_mismatch"] = map_source_mismatch
        out["message"] = str(
            (map_source_mismatch or {}).get("message") or "photo-VQL map is calibrated for a different monitor"
        )


def _apply_photo_vql_provenance_and_verification(out: dict[str, Any], photo_res: dict[str, Any]) -> None:
    """Copy capture provenance and verification fields into the normalized result."""
    if photo_res.get("capture_provenance"):
        out["capture_provenance"] = photo_res.get("capture_provenance")
        if out.get("capture_confirmed") is None:
            out["capture_confirmed"] = out["capture_provenance"].get("capture_confirmed")
    if photo_res.get("verification"):
        out["verification"] = photo_res.get("verification")
        out["verified"] = photo_res.get("verified")


def _apply_photo_vql_submit_fields(out: dict[str, Any], photo_res: dict[str, Any], submit: bool) -> None:
    """Copy submitted/submit_result fields and annotate the message on submit."""
    out["submitted"] = bool(photo_res.get("submitted"))
    submit_result = photo_res.get("submit")
    if submit_result is not None:
        out["submit_result"] = submit_result
    if submit and out.get("submitted"):
        out["message"] = f"{out['message']} (submitted)"


def normalize_drive_result(
    photo_res: dict[str, Any], *, ide: str, submit: bool, policy: DriveResultPolicy
) -> dict[str, Any]:
    """Map perform_photo_vql_focus_and_edit output to send_chat response shape."""
    out = _photo_vql_drive_out_base(photo_res, ide=ide, submit=submit)
    if photo_res.get("llm_used"):
        out["llm_used"] = True
        out["llm_decision"] = photo_res.get("llm_decision")
    if photo_res.get("vql_command_plan"):
        out["vql_command_plan"] = photo_res.get("vql_command_plan")
    if photo_res.get("ide_window_warning"):
        out["ide_window_warning"] = photo_res.get("ide_window_warning")
        if not policy.allow_capture_mismatch():
            out["ok"] = False
            out["capture_confirmed"] = False
    if _photo_vql_drive_verified_false_blocks(photo_res, policy):
        out["ok"] = False
    _apply_photo_vql_capture_confirmed(out, photo_res, policy)
    _apply_photo_vql_plan_inference_gate(out, photo_res, policy)
    _apply_photo_vql_map_mismatch_gate(out, photo_res, policy)
    _apply_photo_vql_provenance_and_verification(out, photo_res)
    _apply_photo_vql_submit_fields(out, photo_res, submit)
    if photo_res.get("is_code_edit") and (photo_res.get("edit") or {}).get("ok"):
        out["ok"] = True
    return out
