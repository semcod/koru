"""Adaptive-pointer wiring: the opt-in closed-loop positioner is consulted only
under the flag, blocks an off-monitor cursor, and falls back on failure."""
import types

import pytest

import koru.integrations.vdisplay_client as vc


def test_adaptive_pointer_disabled_by_default(monkeypatch):
    monkeypatch.delenv("KORU_VDISPLAY_ADAPTIVE_POINTER", raising=False)
    assert vc._adaptive_pointer_enabled() is False
    monkeypatch.setenv("KORU_VDISPLAY_ADAPTIVE_POINTER", "1")
    assert vc._adaptive_pointer_enabled() is True


def test_ydotool_click_uses_adaptive_when_enabled(monkeypatch):
    monkeypatch.setenv("KORU_VDISPLAY_ADAPTIVE_POINTER", "1")
    monkeypatch.setattr(vc, "_enrich_capture_meta_for_pointer", lambda meta, source: {"source": source})
    monkeypatch.setattr(vc, "_photo_capture_meta_for_source", lambda source: {"source": source})
    called = {}

    def fake_adaptive(*, x, y, source, capture_meta, ide):
        called["hit"] = (x, y, source)
        return {"ok": True, "method": "adaptive-pointer-click", "x": 999, "y": 888}

    monkeypatch.setattr(vc, "_adaptive_position_pointer", fake_adaptive)
    res = vc._ydotool_click_capture_local(x=100, y=200, source="DP-1")
    assert res["method"] == "adaptive-pointer-click"
    assert res["x"] == 999
    assert called["hit"] == (100, 200, "DP-1")


def test_ydotool_click_falls_back_when_adaptive_returns_none(monkeypatch):
    monkeypatch.setenv("KORU_VDISPLAY_ADAPTIVE_POINTER", "1")
    monkeypatch.setattr(vc, "_enrich_capture_meta_for_pointer", lambda meta, source: {"source": source})
    monkeypatch.setattr(vc, "_photo_capture_meta_for_source", lambda source: {"source": source})
    monkeypatch.setattr(vc, "_adaptive_position_pointer", lambda **k: None)

    # stub the open-loop path so we don't touch hardware
    fake_coords = types.SimpleNamespace()
    moved = {}

    class FakeY:
        def move(self, x, y):
            moved["at"] = (x, y)

        def click(self, btn):
            moved["click"] = btn

    monkeypatch.setitem(
        __import__("sys").modules,
        "vdisplay.input.coords",
        types.SimpleNamespace(global_pointer_coords=lambda x, y, meta: (x + 1, y + 2, {"m": "region"})),
    )
    monkeypatch.setitem(
        __import__("sys").modules,
        "vdisplay.input.linux_ydotool",
        types.SimpleNamespace(LinuxYdotoolInput=FakeY),
    )
    res = vc._ydotool_click_capture_local(x=10, y=20, source="DP-1")
    assert res["method"] == "ydotool-click"  # fell back to open-loop
    assert moved["at"] == (11, 22)


def test_abs_pointer_flag_and_precedence(monkeypatch):
    import koru.integrations.vdisplay_client as vc

    monkeypatch.delenv("KORU_VDISPLAY_ABS_POINTER", raising=False)
    assert vc._abs_pointer_enabled() is False
    monkeypatch.setenv("KORU_VDISPLAY_ABS_POINTER", "1")
    assert vc._abs_pointer_enabled() is True

    # when enabled and the ABS click succeeds, it wins over ydotool
    monkeypatch.setattr(vc, "_enrich_capture_meta_for_pointer", lambda meta, source: {"source": source})
    monkeypatch.setattr(vc, "_photo_capture_meta_for_source", lambda source: {"source": source})
    called = {}

    def fake_abs(*, x, y, source):
        called["hit"] = (x, y, source)
        return {"ok": True, "method": "uinput-abs-click", "abs_x": 2375, "abs_y": 2001}

    monkeypatch.setattr(vc, "_abs_pointer_click", fake_abs)
    res = vc._ydotool_click_capture_local(x=1484, y=848, source="DP-1")
    assert res["method"] == "uinput-abs-click"
    assert called["hit"] == (1484, 848, "DP-1")


def test_abs_affine_conversion_math(monkeypatch, tmp_path):
    import json
    import koru.integrations.vdisplay_client as vc

    # cache an affine and confirm _abs_pointer_click inverts it correctly
    aff = {"ax": 0.625, "bx": 0.0, "ay": 0.625, "by": -400.0}
    monkeypatch.setattr(vc, "_load_or_calibrate_abs_affine", lambda source: aff)
    moved = {}

    class FakeDev:
        def open(self): return self
        def move_abs_and_click(self, x, y, **k): moved["at"] = (x, y)
        def close(self): pass

    import types, sys
    monkeypatch.setitem(sys.modules, "vdisplay.input.linux_uinput_abs",
                        types.SimpleNamespace(LinuxUinputAbsInput=FakeDev))
    res = vc._abs_pointer_click(x=1484, y=848, source="DP-1")
    assert res["method"] == "uinput-abs-click"
    # ABS = (local - b)/a : x=(1484-0)/0.625=2374, y=(848+400)/0.625=1997
    assert moved["at"] == (2374, 1996) or moved["at"] == (2374, 1997)
