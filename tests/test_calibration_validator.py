"""Tests for koruapi.calibration_validator — IDE calibration validation."""

from __future__ import annotations

import pytest

from koruapi.calibration_validator import (
    BOTTOM_EDGE_THRESHOLD_PCT,
    EXTREME_TOP_THRESHOLD_PCT,
    SEVERITY_ERROR,
    SEVERITY_INFO,
    SEVERITY_WARNING,
    STALE_HOURS,
    TOP_EDGE_THRESHOLD_PCT,
    validate_calibrations,
    validate_single_calibration,
)


# ── Fixtures ───────────────────────────────────────────────────────────

DISPLAY_DP2 = {
    "id": "DP-2",
    "output": "DP-2",
    "width": 4320,
    "height": 7680,
    "left": 4096,
    "top": 0,
    "is_primary": True,
}

DISPLAY_DP1 = {
    "id": "DP-1",
    "output": "DP-1",
    "width": 4096,
    "height": 2560,
    "left": 0,
    "top": 1304,
    "is_primary": False,
}

DISPLAY_HDMI1 = {
    "id": "HDMI-1",
    "output": "HDMI-1",
    "width": 2048,
    "height": 1280,
    "left": 0,
    "top": 3864,
    "is_primary": False,
}

ALL_DISPLAYS = [DISPLAY_HDMI1, DISPLAY_DP2, DISPLAY_DP1]


def _make_calibration(
    ide: str = "cursor",
    display_id: str = "DP-2",
    display_x: int = 2000,
    display_y: int = 5000,
    chat_x: int = 8000,
    chat_y: int = 5000,
    calibrated_at: str = "2026-06-06T21:31:35.733991+00:00",
) -> dict:
    return {
        "ide": ide,
        "chat_x": chat_x,
        "chat_y": chat_y,
        "display_id": display_id,
        "display_output": display_id,
        "display_x": display_x,
        "display_y": display_y,
        "calibrated_at": calibrated_at,
        "config_path": "/home/tom/.koru/ide-os-injector.json",
        "source": "global",
    }


def _make_desktop(
    calibrations: list[dict] | None = None,
    displays: list[dict] | None = None,
    pointer: dict | None = None,
) -> dict:
    return {
        "ide_calibrations": calibrations or [],
        "displays": displays if displays is not None else ALL_DISPLAYS,
        "pointer": pointer,
    }


# ── validate_single_calibration tests ──────────────────────────────────


class TestValidateSingleCalibration:
    def test_valid_calibration_returns_no_issues(self) -> None:
        """A calibration at ~65% height should pass without issues."""
        cal = _make_calibration(display_y=5000)  # 5000/7680 = 65%
        issues = validate_single_calibration(cal, ALL_DISPLAYS)
        assert issues == []

    def test_extreme_top_returns_error(self) -> None:
        """display_y=68 on a 7680px display is 0.9% — should be an error."""
        cal = _make_calibration(display_y=68)  # The exact cursor bug!
        issues = validate_single_calibration(cal, ALL_DISPLAYS)
        errors = [i for i in issues if i["severity"] == SEVERITY_ERROR]
        assert len(errors) == 1
        assert errors[0]["code"] == "calibration_at_extreme_top"
        assert "title bar" in errors[0]["message"].lower() or "NOT the chat" in errors[0]["message"]

    def test_top_edge_returns_warning(self) -> None:
        """display_y at 3% should trigger a warning (not error)."""
        # 3% of 7680 = 230
        cal = _make_calibration(display_y=230)
        issues = validate_single_calibration(cal, ALL_DISPLAYS)
        warnings = [i for i in issues if i["severity"] == SEVERITY_WARNING]
        codes = [w["code"] for w in warnings]
        assert "calibration_at_top_edge" in codes

    def test_5pct_boundary_is_safe(self) -> None:
        """display_y at exactly 5% should NOT trigger any position warning."""
        # 5% of 7680 = 384
        cal = _make_calibration(display_y=384)
        issues = validate_single_calibration(cal, ALL_DISPLAYS)
        position_issues = [
            i for i in issues
            if i["code"] in ("calibration_at_extreme_top", "calibration_at_top_edge")
        ]
        assert position_issues == []

    def test_bottom_edge_returns_warning(self) -> None:
        """display_y near 100% height should trigger dock/panel warning."""
        cal = _make_calibration(display_y=7600)  # 7600/7680 = 99%
        issues = validate_single_calibration(cal, ALL_DISPLAYS)
        warnings = [i for i in issues if i["code"] == "calibration_at_bottom_edge"]
        assert len(warnings) == 1

    def test_pointer_display_mismatch(self) -> None:
        """Pointer on DP-2, calibration on DP-1 → mismatch warning."""
        cal = _make_calibration(display_id="DP-1", display_y=1500)
        pointer = {"display_id": "DP-2", "x": 8151, "y": 68}
        issues = validate_single_calibration(cal, ALL_DISPLAYS, pointer)
        mismatches = [i for i in issues if i["code"] == "pointer_display_mismatch"]
        assert len(mismatches) == 1
        assert "DP-1" in mismatches[0]["message"]
        assert "DP-2" in mismatches[0]["message"]

    def test_no_mismatch_when_same_display(self) -> None:
        """Pointer on same display as calibration → no mismatch."""
        cal = _make_calibration(display_id="DP-2", display_y=5000)
        pointer = {"display_id": "DP-2"}
        issues = validate_single_calibration(cal, ALL_DISPLAYS, pointer)
        mismatches = [i for i in issues if i["code"] == "pointer_display_mismatch"]
        assert mismatches == []

    def test_stale_calibration(self) -> None:
        """Calibration older than threshold → info."""
        cal = _make_calibration(
            display_y=5000,
            calibrated_at="2026-06-01T00:00:00+00:00",  # ~5 days ago
        )
        issues = validate_single_calibration(cal, ALL_DISPLAYS)
        stale = [i for i in issues if i["code"] == "calibration_stale"]
        assert len(stale) == 1
        assert stale[0]["severity"] == SEVERITY_INFO

    def test_missing_display_coords(self) -> None:
        """Calibration without display_y → warning about missing coords."""
        cal = {"ide": "cursor", "chat_x": 100, "chat_y": 200}
        issues = validate_single_calibration(cal, ALL_DISPLAYS)
        assert len(issues) == 1
        assert issues[0]["code"] == "missing_display_coords"

    def test_display_not_found(self) -> None:
        """Calibration referencing a non-existent display → warning."""
        cal = _make_calibration(display_id="VIRTUAL-1", display_y=500)
        issues = validate_single_calibration(cal, ALL_DISPLAYS)
        assert any(i["code"] == "display_not_found" for i in issues)

    def test_display_zero_height(self) -> None:
        """Display with zero height → warning."""
        displays = [{"id": "DP-2", "output": "DP-2", "width": 4320, "height": 0}]
        cal = _make_calibration(display_y=100)
        issues = validate_single_calibration(cal, displays)
        assert any(i["code"] == "display_zero_size" for i in issues)

    def test_no_pointer_skips_mismatch_check(self) -> None:
        """No pointer data → no mismatch warning."""
        cal = _make_calibration(display_id="HDMI-1", display_y=800)
        issues = validate_single_calibration(cal, ALL_DISPLAYS, pointer=None)
        assert not any(i["code"] == "pointer_display_mismatch" for i in issues)


# ── validate_calibrations (batch) tests ────────────────────────────────


class TestValidateCalibrations:
    def test_no_desktop_data(self) -> None:
        result = validate_calibrations(None)
        assert result["ok"] is False
        assert result["error_count"] == 1
        assert result["issues"][0]["code"] == "no_desktop_data"

    def test_empty_desktop(self) -> None:
        result = validate_calibrations({})
        assert result["ok"] is False
        assert result["issues"][0]["code"] == "no_desktop_data"

    def test_desktop_with_no_calibrations(self) -> None:
        desktop = {"displays": ALL_DISPLAYS, "ide_calibrations": []}
        result = validate_calibrations(desktop)
        assert result["ok"] is False
        assert result["issues"][0]["code"] == "no_calibrations"

    def test_all_good(self) -> None:
        cals = [
            _make_calibration(ide="vscode", display_id="DP-1", display_y=1500),
            _make_calibration(ide="windsurf", display_id="DP-1", display_y=1800),
        ]
        desktop = _make_desktop(calibrations=cals)
        result = validate_calibrations(desktop)
        assert result["ok"] is True
        assert result["calibrations_checked"] == 2
        assert result["error_count"] == 0
        assert result["warning_count"] == 0

    def test_mixed_good_and_bad(self) -> None:
        cals = [
            _make_calibration(ide="cursor", display_id="DP-2", display_y=68),  # BAD
            _make_calibration(ide="vscode", display_id="DP-1", display_y=1500),  # OK
        ]
        desktop = _make_desktop(calibrations=cals)
        result = validate_calibrations(desktop)
        assert result["ok"] is False
        assert result["error_count"] >= 1
        assert result["calibrations_checked"] == 2

    def test_ide_filter_limits_scope(self) -> None:
        cals = [
            _make_calibration(ide="cursor", display_id="DP-2", display_y=68),  # BAD
            _make_calibration(ide="vscode", display_id="DP-1", display_y=1500),
        ]
        desktop = _make_desktop(calibrations=cals)
        # Only validate vscode — should be OK
        result = validate_calibrations(desktop, ide_filter="vscode")
        assert result["ok"] is True
        assert result["calibrations_checked"] == 1

    def test_ide_filter_cursor_finds_error(self) -> None:
        cals = [
            _make_calibration(ide="cursor", display_id="DP-2", display_y=68),
            _make_calibration(ide="vscode", display_id="DP-1", display_y=1500),
        ]
        desktop = _make_desktop(calibrations=cals)
        result = validate_calibrations(desktop, ide_filter="cursor")
        assert result["ok"] is False
        assert result["calibrations_checked"] == 1
        assert result["error_count"] == 1

    def test_pointer_mismatch_detected_in_batch(self) -> None:
        cals = [
            _make_calibration(ide="cursor", display_id="DP-1", display_y=1500),
        ]
        pointer = {"display_id": "DP-2"}
        desktop = _make_desktop(calibrations=cals, pointer=pointer)
        result = validate_calibrations(desktop)
        mismatch_issues = [
            i for i in result["issues"]
            if i["code"] == "pointer_display_mismatch"
        ]
        assert len(mismatch_issues) == 1

    def test_summary_format(self) -> None:
        desktop = _make_desktop(
            calibrations=[_make_calibration(display_y=5000)]
        )
        result = validate_calibrations(desktop)
        assert "validated OK" in result["summary"]

    def test_summary_with_errors(self) -> None:
        desktop = _make_desktop(
            calibrations=[_make_calibration(display_y=68)]
        )
        result = validate_calibrations(desktop)
        assert "error" in result["summary"].lower()


# ── Real-world scenario: the cursor bug from the report ────────────────


class TestRealWorldCursorBug:
    """Reproduce the exact scenario from the test report.

    cursor calibration: display_y=68, display on DP-2 (height=7680)
    → 68/7680 = 0.89% → must be flagged as error.
    """

    def test_exact_cursor_scenario(self) -> None:
        cals = [
            {
                "ide": "cursor",
                "chat_x": 8151,
                "chat_y": 68,
                "config_path": "/home/tom/.koru/ide-os-injector.json",
                "source": "global",
                "display_id": "DP-2",
                "display_output": "DP-2",
                "display_x": 4055,
                "display_y": 68,
                "window_id": None,
                "calibrated_at": "2026-06-06T21:31:35.733991+00:00",
            },
            {
                "ide": "jetbrains",
                "chat_x": 2058,
                "chat_y": 2137,
                "display_id": "DP-1",
                "display_output": "DP-1",
                "display_x": 2058,
                "display_y": 833,
                "calibrated_at": "2026-06-06T21:31:35.733991+00:00",
            },
        ]
        displays = [
            {"id": "HDMI-1", "output": "HDMI-1", "width": 2048, "height": 1280},
            {"id": "DP-2", "output": "DP-2", "width": 4320, "height": 7680},
            {"id": "DP-1", "output": "DP-1", "width": 4096, "height": 2560},
        ]
        pointer = {"display_id": "DP-2", "x": 8151, "y": 68}
        desktop = {
            "ide_calibrations": cals,
            "displays": displays,
            "pointer": pointer,
        }

        result = validate_calibrations(desktop)

        # cursor should have an error for extreme top
        cursor_errors = [
            i for i in result["issues"]
            if i["ide"] == "cursor" and i["severity"] == SEVERITY_ERROR
        ]
        assert len(cursor_errors) == 1
        assert cursor_errors[0]["code"] == "calibration_at_extreme_top"
        assert cursor_errors[0]["details"]["y_pct"] < 1.0

        # jetbrains at 833/2560 = 32.5% should be fine
        jb_issues = [
            i for i in result["issues"]
            if i["ide"] == "jetbrains"
            and i["severity"] in (SEVERITY_ERROR, SEVERITY_WARNING)
            and i["code"] in (
                "calibration_at_extreme_top",
                "calibration_at_top_edge",
                "calibration_at_bottom_edge",
            )
        ]
        assert jb_issues == []

        assert result["ok"] is False
        assert result["error_count"] >= 1
