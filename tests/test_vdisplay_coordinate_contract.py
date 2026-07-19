"""Koru boundary tests for VDisplay-owned coordinate truth."""

from __future__ import annotations

import koru.integrations.vdisplay_client as vc


def test_global_coordinate_audit_contains_canonical_map(
    monkeypatch,
) -> None:
    meta = {
        "source": "HDMI-1",
        "monitor_name": "HDMI-1",
        "width": 2048,
        "height": 1280,
        "region": {"x": 0, "y": 2560, "width": 4096, "height": 2560},
    }
    monkeypatch.setenv("VDISPLAY_POINTER_SAFE_MARGIN", "0")
    monkeypatch.setattr(vc, "_photo_capture_meta_for_source", lambda _source: meta)
    monkeypatch.setattr(vc, "_enrich_capture_meta_for_pointer", lambda value, _source: value)

    global_x, global_y, audit = vc._global_coords_from_vql_local(
        x=1024,
        y=640,
        source="HDMI-1",
    )

    assert (global_x, global_y) == (2048, 3840)
    coordinate_map = audit["coordinate_map"]
    assert coordinate_map["schema"] == "vdisplay.coordinate-map.v1"
    assert len(coordinate_map["coordinate_map_hash"]) == 64


def test_live_surface_metadata_delegates_to_vdisplay(monkeypatch) -> None:
    expected = {
        "source": "DP-2",
        "width": 2048,
        "height": 1280,
        "region": {"x": 0, "y": 1932, "width": 2048, "height": 1280},
    }
    monkeypatch.setattr(
        "vdisplay.capture.resolve_live_capture_meta",
        lambda source, default_size: {**expected, "source": source},
    )

    assert vc._live_surface_capture_meta("DP-2") == expected
