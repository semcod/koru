"""JetBrains chat target from correlated IDE surface bounds."""

from __future__ import annotations

from koru.integrations.photo_vql_target import jetbrains_chat_target_from_surface


def test_jetbrains_chat_target_from_surface_hdmi1() -> None:
    surface = {
        "display_name": "PyCharm",
        "monitor_name": "HDMI-1",
        "pid": 35616,
        "stack": "jetbrains_xwayland",
        "bounds": {"x": 3216, "y": 2550, "width": 880, "height": 1548},
    }
    # HDMI-1 monitor origin y=2560, capture stream 2048x1280 (no rotation)
    capture_meta = {
        "source": "HDMI-1",
        "monitor_name": "HDMI-1",
        "width": 2048,
        "height": 1280,
        "region": {"x": 0, "y": 2560, "width": 4096, "height": 2560},
    }
    target = jetbrains_chat_target_from_surface(
        surface,
        capture_meta=capture_meta,
        source="HDMI-1",
    )
    assert target is not None
    cc = target["click_center"]
    assert cc["y"] >= 700
    assert cc["x"] >= 1600
    assert target["id"] == "surface:jetbrains-chat"
    assert isinstance(target.get("surface_window_capture_local"), dict)
    rect = target["surface_window_capture_local"]
    assert cc["x"] >= int(rect["x"] + rect["w"] * 0.55)
    assert cc["y"] >= int(rect["y"] + rect["h"] * 0.82)


def test_jetbrains_surface_target_passes_window_relative_validation() -> None:
    from koru.integrations.photo_vql_validation import validate_vql_chat_target

    surface = {
        "display_name": "PyCharm",
        "monitor_name": "HDMI-1",
        "bounds": {"x": 3216, "y": 2550, "width": 880, "height": 1548},
    }
    capture_meta = {
        "source": "HDMI-1",
        "width": 2048,
        "height": 1280,
        "region": {"x": 0, "y": 2560, "width": 4096, "height": 2560},
    }
    target = jetbrains_chat_target_from_surface(
        surface,
        capture_meta=capture_meta,
        source="HDMI-1",
    )
    assert target is not None
    val = validate_vql_chat_target(
        target,
        ide="jetbrains",
        selection_method="jetbrains_surface_bounds",
    )
    assert val["ok"] is True
    assert not val.get("coord_warnings")


def test_jetbrains_chat_target_skips_toolbox() -> None:
    surface = {
        "display_name": "Toolbox",
        "monitor_name": "HDMI-1",
        "bounds": {"x": 3266, "y": 2822, "width": 880, "height": 1326},
    }
    assert jetbrains_chat_target_from_surface(
        surface,
        capture_meta={"source": "HDMI-1", "height": 1280, "region": {"y": 2560, "height": 2560}},
        source="HDMI-1",
    ) is None


def test_jetbrains_chat_target_skips_wrong_monitor() -> None:
    surface = {
        "display_name": "PyCharm",
        "monitor_name": "HDMI-1",
        "bounds": {"x": 3216, "y": 2550, "width": 880, "height": 1548},
    }
    assert jetbrains_chat_target_from_surface(
        surface,
        capture_meta={"source": "DP-1", "height": 1280},
        source="DP-1",
    ) is None
