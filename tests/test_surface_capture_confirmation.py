"""Tests for JetBrains surface-based capture confirmation."""

from __future__ import annotations

import pytest

from koru.integrations import vdisplay_client as vc


def test_surface_confirms_jetbrains_on_hdmi() -> None:
    probe = {
        "ide_surface_best": {
            "display_name": "PyCharm",
            "monitor_name": "HDMI-1",
            "stack": "jetbrains_xwayland",
            "pid": 35616,
        }
    }
    assert vc._surface_confirms_ide_capture(ide="jetbrains", source="HDMI-1", desktop_probe=probe)
    assert not vc._surface_confirms_ide_capture(ide="jetbrains", source="DP-1", desktop_probe=probe)


def test_apply_surface_capture_confirmation_clears_mismatch_block() -> None:
    probe = {
        "ide_surface_best": {
            "display_name": "PyCharm",
            "monitor_name": "HDMI-1",
            "stack": "jetbrains_xwayland",
        }
    }
    out = {
        "ok": False,
        "capture_confirmed": False,
        "ide_window_warning": {"message": "no PyCharm title in VQL"},
        "error": "capture does not match requested IDE",
    }
    vc._apply_surface_capture_confirmation(
        out,
        ide="jetbrains",
        source="HDMI-1",
        desktop_probe=probe,
    )
    assert out["capture_confirmed"] is True
    assert out["capture_confirmation_source"] == "ide_surface_best"
    assert "ide_window_warning" not in out


def test_apply_surface_capture_confirmation_allows_prepare_without_png() -> None:
    probe = {
        "ide_surface_best": {
            "display_name": "PyCharm",
            "monitor_name": "HDMI-1",
            "stack": "jetbrains_xwayland",
        }
    }
    out = {
        "ok": False,
        "capture_confirmed": False,
        "ide_window_warning": {"message": "capture does not match requested IDE"},
        "error": "vdisplay capture failed",
        "returncode": 1,
    }
    vc._apply_surface_capture_confirmation(
        out,
        ide="jetbrains",
        source="HDMI-1",
        desktop_probe=probe,
        capture_error=True,
    )
    assert out["capture_confirmed"] is True
    assert out["surface_only_fallback"] is True
    assert out["ok"] is True
    assert "error" not in out


def test_capture_guard_allows_surface_only_fallback_on_capture_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from koru.integrations import photo_vql_guard as guard

    monkeypatch.setenv("KORU_VDISPLAY_ALLOW_SURFACE_ON_CAPTURE_ERROR", "1")
    mismatch = {"message": "capture does not match requested IDE"}
    g = guard.CaptureGuard.from_observe(
        ide="jetbrains",
        confirmed=True,
        ide_window_warning=mismatch,
        surface_only_fallback=True,
        capture_error=True,
    )
    out = g.apply_to_prepare_out(
        {"error": "vdisplay capture failed"},
        ide_control=None,
        capture_error=True,
    )
    assert out["ok"] is True
    assert out["surface_only_fallback"] is True
    assert out["capture_confirmed"] is True


def test_sync_prepare_capture_flags_sets_source(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("KORU_VDISPLAY_SOURCE", raising=False)
    vc.sync_prepare_capture_flags_to_env(
        {"source": "HDMI-1", "capture_confirmed": True, "surface_only_fallback": True},
    )
    import os

    assert os.environ.get("KORU_VDISPLAY_SOURCE") == "HDMI-1"
    assert os.environ.get("KORU_VDISPLAY_CAPTURE_MATCHES_IDE") == "1"
    assert os.environ.get("KORU_VDISPLAY_SURFACE_ONLY_FALLBACK") == "1"


def test_surface_target_can_clear_capture_mismatch(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("KORU_VDISPLAY_CAPTURE_MATCHES_IDE", "1")
    target = {"selection_method": "jetbrains_surface_bounds", "id": "surface:chat"}
    assert vc._surface_target_can_clear_capture_mismatch(target=target, ide="jetbrains")
    assert not vc._surface_target_can_clear_capture_mismatch(
        target={"selection_method": "map_calibrated"},
        ide="jetbrains",
    )
