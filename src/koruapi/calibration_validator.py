"""Validate IDE calibration data from the env2llm desktop registry.

Detects common calibration mistakes:

- Chat coordinates at the very top of a monitor (< 5% height → probably
  title bar, not chat input).
- Chat coordinates at the very top of the display (< 2% height → extreme
  edge, almost certainly wrong).
- Pointer–display mismatch: mouse pointer is on a different display than
  the IDE calibration target.
- Stale calibration: calibrated_at older than a threshold.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)

# ── Thresholds ─────────────────────────────────────────────────────────
TOP_EDGE_THRESHOLD_PCT = 5.0       # display_y within top 5% → probably not chat
EXTREME_TOP_THRESHOLD_PCT = 2.0    # display_y within top 2% → almost certainly wrong
BOTTOM_EDGE_THRESHOLD_PCT = 98.0   # display_y within bottom 2% → probably panel/dock
LEFT_EDGE_THRESHOLD_PCT = 3.0      # display_x within left 3% → probably window border
RIGHT_EDGE_THRESHOLD_PCT = 97.0    # display_x within right 3% → probably scrollbar area
STALE_HOURS = 48.0                 # recalibrate after 48h


# ── Severity levels ────────────────────────────────────────────────────
SEVERITY_ERROR = "error"
SEVERITY_WARNING = "warning"
SEVERITY_INFO = "info"


def _find_display(displays: list[dict[str, Any]], display_id: str) -> dict[str, Any] | None:
    """Lookup a display dict by id or output."""
    for d in displays:
        if d.get("id") == display_id or d.get("output") == display_id:
            return d
    return None


def _pct(value: int | float, total: int | float) -> float:
    if total <= 0:
        return 0.0
    return 100.0 * float(value) / float(total)


def validate_single_calibration(
    cal: dict[str, Any],
    displays: list[dict[str, Any]],
    pointer: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Validate a single IDE calibration entry against display geometry.

    Returns a list of diagnostic dicts, each with keys:
    ``severity``, ``code``, ``message``, ``ide``, and optional ``details``.
    """
    issues: list[dict[str, Any]] = []
    ide = cal.get("ide", "?")
    display_id = cal.get("display_id") or cal.get("display_output")
    display_x = cal.get("display_x")
    display_y = cal.get("display_y")

    if display_id is None or display_x is None or display_y is None:
        issues.append({
            "severity": SEVERITY_WARNING,
            "code": "missing_display_coords",
            "message": f"Calibration for {ide!r} has no display-relative coordinates; cannot validate.",
            "ide": ide,
        })
        return issues

    # Resolve display geometry
    display = _find_display(displays, display_id)
    if display is None:
        issues.append({
            "severity": SEVERITY_WARNING,
            "code": "display_not_found",
            "message": (
                f"Calibration for {ide!r} references display {display_id!r}, "
                "but it was not found in the display list."
            ),
            "ide": ide,
            "details": {"display_id": display_id},
        })
        return issues

    dw = display.get("width", 0)
    dh = display.get("height", 0)

    if dw <= 0 or dh <= 0:
        issues.append({
            "severity": SEVERITY_WARNING,
            "code": "display_zero_size",
            "message": f"Display {display_id!r} has zero or negative dimensions ({dw}×{dh}).",
            "ide": ide,
            "details": {"display_id": display_id, "width": dw, "height": dh},
        })
        return issues

    y_pct = _pct(display_y, dh)
    x_pct = _pct(display_x, dw)

    # ── Top-edge detection (most critical for the reported cursor bug) ──
    if y_pct < EXTREME_TOP_THRESHOLD_PCT:
        issues.append({
            "severity": SEVERITY_ERROR,
            "code": "calibration_at_extreme_top",
            "message": (
                f"Calibration for {ide!r} is at {y_pct:.1f}% height on {display_id} "
                f"(display_y={display_y}, display_height={dh}). "
                "This is almost certainly the title bar or menu bar, NOT the chat input. "
                "Recalibrate with the mouse directly over the chat text field."
            ),
            "ide": ide,
            "details": {
                "display_id": display_id,
                "display_y": display_y,
                "display_height": dh,
                "y_pct": round(y_pct, 2),
            },
        })
    elif y_pct < TOP_EDGE_THRESHOLD_PCT:
        issues.append({
            "severity": SEVERITY_WARNING,
            "code": "calibration_at_top_edge",
            "message": (
                f"Calibration for {ide!r} is at {y_pct:.1f}% height on {display_id} "
                f"(display_y={display_y}, display_height={dh}). "
                "This is probably the title bar, not the chat input field."
            ),
            "ide": ide,
            "details": {
                "display_id": display_id,
                "display_y": display_y,
                "display_height": dh,
                "y_pct": round(y_pct, 2),
            },
        })

    # ── Bottom-edge detection (task bar / dock) ──
    if y_pct > BOTTOM_EDGE_THRESHOLD_PCT:
        issues.append({
            "severity": SEVERITY_WARNING,
            "code": "calibration_at_bottom_edge",
            "message": (
                f"Calibration for {ide!r} is at {y_pct:.1f}% height on {display_id}. "
                "This might be the system panel/dock instead of the chat input."
            ),
            "ide": ide,
            "details": {
                "display_id": display_id,
                "display_y": display_y,
                "display_height": dh,
                "y_pct": round(y_pct, 2),
            },
        })

    # ── Stale calibration ──
    calibrated_at_raw = cal.get("calibrated_at")
    if calibrated_at_raw:
        try:
            calibrated_at = datetime.fromisoformat(str(calibrated_at_raw))
            if calibrated_at.tzinfo is None:
                calibrated_at = calibrated_at.replace(tzinfo=timezone.utc)
            age_hours = (datetime.now(timezone.utc) - calibrated_at).total_seconds() / 3600
            if age_hours > STALE_HOURS:
                issues.append({
                    "severity": SEVERITY_INFO,
                    "code": "calibration_stale",
                    "message": (
                        f"Calibration for {ide!r} is {age_hours:.0f}h old "
                        f"(threshold={STALE_HOURS:.0f}h). Consider recalibrating."
                    ),
                    "ide": ide,
                    "details": {
                        "calibrated_at": str(calibrated_at_raw),
                        "age_hours": round(age_hours, 1),
                        "threshold_hours": STALE_HOURS,
                    },
                })
        except (ValueError, TypeError):
            pass

    # ── Pointer-display mismatch ──
    if pointer:
        pointer_display = pointer.get("display_id") or pointer.get("display_output")
        if pointer_display and display_id and pointer_display != display_id:
            issues.append({
                "severity": SEVERITY_WARNING,
                "code": "pointer_display_mismatch",
                "message": (
                    f"IDE {ide!r} is calibrated on display {display_id!r} but the "
                    f"mouse pointer is on {pointer_display!r}. The autopilot drive may "
                    "click the wrong screen. Move the IDE window or re-calibrate."
                ),
                "ide": ide,
                "details": {
                    "calibration_display": display_id,
                    "pointer_display": pointer_display,
                },
            })

    return issues


def validate_calibrations(
    desktop: dict[str, Any] | None,
    *,
    ide_filter: str | None = None,
) -> dict[str, Any]:
    """Validate all IDE calibrations from a desktop payload.

    Parameters
    ----------
    desktop:
        The desktop dict as returned by ``service.desktop_payload()`` or
        the ``desktop`` key from ``env2llm_get_desktop()``.
    ide_filter:
        If given, validate only calibrations matching this IDE name.

    Returns
    -------
    dict with keys:
        ok: bool — True if no errors or warnings.
        calibrations_checked: int
        issues: list[dict] — all validation diagnostics.
        error_count: int
        warning_count: int
        summary: str — human-readable one-liner.
    """
    if not desktop:
        return {
            "ok": False,
            "calibrations_checked": 0,
            "issues": [{
                "severity": SEVERITY_ERROR,
                "code": "no_desktop_data",
                "message": "No desktop data available. Run with ENV2LLM_DESKTOP_PROBE=1.",
                "ide": None,
            }],
            "error_count": 1,
            "warning_count": 0,
            "summary": "No desktop data available",
        }

    calibrations = desktop.get("ide_calibrations") or []
    displays = desktop.get("displays") or []
    pointer = desktop.get("pointer")

    if not calibrations:
        return {
            "ok": False,
            "calibrations_checked": 0,
            "issues": [{
                "severity": SEVERITY_WARNING,
                "code": "no_calibrations",
                "message": (
                    "No IDE calibrations found. "
                    "Run `koru autopilot calibrate --ide auto` first."
                ),
                "ide": None,
            }],
            "error_count": 0,
            "warning_count": 1,
            "summary": "No calibrations to validate",
        }

    all_issues: list[dict[str, Any]] = []
    checked = 0

    for cal in calibrations:
        cal_ide = cal.get("ide", "")
        if ide_filter and cal_ide != ide_filter:
            continue
        checked += 1
        issues = validate_single_calibration(cal, displays, pointer)
        all_issues.extend(issues)

    error_count = sum(1 for i in all_issues if i["severity"] == SEVERITY_ERROR)
    warning_count = sum(1 for i in all_issues if i["severity"] == SEVERITY_WARNING)
    ok = error_count == 0 and warning_count == 0

    if ok:
        summary = f"{checked} calibration(s) validated OK"
    else:
        parts = []
        if error_count:
            parts.append(f"{error_count} error(s)")
        if warning_count:
            parts.append(f"{warning_count} warning(s)")
        summary = f"{checked} calibration(s) checked: {', '.join(parts)}"

    return {
        "ok": ok,
        "calibrations_checked": checked,
        "issues": all_issues,
        "error_count": error_count,
        "warning_count": warning_count,
        "summary": summary,
    }
