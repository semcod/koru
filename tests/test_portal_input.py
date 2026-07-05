"""Hermetic tests for the koru portal-input targeting helpers."""
import struct
import types

import pytest  # noqa: F401

from koru.integrations.vdisplay import portal_input as pi


def _png_bytes(w, h):
    # minimal PNG header with IHDR width/height at bytes 16..24
    return b"\x89PNG\r\n\x1a\n" + b"\x00\x00\x00\rIHDR" + struct.pack(">II", w, h) + b"\x00" * 8


def test_enabled_flag(monkeypatch):
    monkeypatch.delenv("KORU_VDISPLAY_PORTAL_INPUT", raising=False)
    assert pi.portal_input_enabled() is False
    monkeypatch.setenv("KORU_VDISPLAY_PORTAL_INPUT", "1")
    assert pi.portal_input_enabled() is True


def test_png_size_reads_ihdr():
    assert pi._png_size(_png_bytes(2560, 1600)) == (2560, 1600)


def test_landmark_input_between_context_and_auto(monkeypatch):
    Bounds = types.SimpleNamespace
    Box = lambda text, x, y, w, h: types.SimpleNamespace(text=text, bounds=Bounds(x=x, y=y, width=w, height=h))  # noqa: E731
    boxes = [
        Box("Add Context", 200, 700, 120, 24),
        Box("questions", 900, 300, 90, 20),   # a distractor 'context'-free word
        Box("Auto", 260, 840, 60, 22),
    ]
    monkeypatch.setattr("vdisplay.control.vision_ocr.ocr_available", lambda: (True, "ok"))
    monkeypatch.setattr("vdisplay.control.vision_ocr.ocr_png", lambda d, **k: boxes)
    xy = pi._landmark_input_xy(b"frame")
    assert xy is not None
    # x = context.x + 40 ; y = midpoint between context bottom (724) and auto top (840)
    assert xy[0] == 240
    assert 720 <= xy[1] <= 845


def test_landmark_none_without_context(monkeypatch):
    monkeypatch.setattr("vdisplay.control.vision_ocr.ocr_available", lambda: (True, "ok"))
    monkeypatch.setattr("vdisplay.control.vision_ocr.ocr_png", lambda d, **k: [])
    assert pi._landmark_input_xy(b"frame") is None


class _FakePortalSession:
    """Hermetic stand-in for the portal RemoteDesktop session."""

    def __init__(self):
        self.cleared = False
        self.clicked = 0
        self.typed = 0

    def grab_frame(self):
        return _png_bytes(100, 100)

    def frame_to_stream(self, x, y, frame_w, frame_h):
        return (x, y)

    def move_abs(self, x, y):
        pass

    def click(self):
        self.clicked += 1

    def clear_input(self, n):
        self.cleared = True

    def type_into_input_verified(self, sx, sy, text, **kw):
        self.typed += 1
        return True


def _wire_two_pass(monkeypatch, session, *, focused: bool):
    """Route type_into_chat_via_portal into the two-pass clear branch."""
    monkeypatch.delenv("KORU_VDISPLAY_PORTAL_AUTOREMEMBER", raising=False)
    monkeypatch.setattr(pi, "_get_session", lambda: session)
    monkeypatch.setattr(pi, "_cached_input_xy", lambda ide: None)
    # No placeholder anchor -> "input already holds text" branch.
    monkeypatch.setattr(pi, "_anchor_precise", lambda frame, ide: None)
    # Flaky OCR landmark resolves to a rough point.
    monkeypatch.setattr(pi, "_ocr_anchor_xy", lambda frame, ide: (50, 50))
    monkeypatch.setattr(pi, "_focused_near", lambda after, sx, sy, **kw: focused)


def test_two_pass_clear_aborts_when_click_missed_focus(monkeypatch):
    """Regression: clear_input(200) must never fire on an unverified click.

    A mis-located landmark click (editor/terminal pane) used to trigger up
    to 200 deletes in whatever pane got focused, before any guard ran.
    """
    session = _FakePortalSession()
    _wire_two_pass(monkeypatch, session, focused=False)
    result = pi.type_into_chat_via_portal("hello", ide="qoder", submit=False)
    assert result["ok"] is False
    assert "before clear" in (result["error"] or "")
    assert session.cleared is False
    assert session.typed == 0


def test_two_pass_clear_proceeds_when_click_focused(monkeypatch):
    session = _FakePortalSession()
    _wire_two_pass(monkeypatch, session, focused=True)
    result = pi.type_into_chat_via_portal("hello", ide="qoder", submit=False)
    assert session.cleared is True
    assert result["ok"] is True
