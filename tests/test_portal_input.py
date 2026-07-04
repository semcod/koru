"""Hermetic tests for the koru portal-input targeting helpers."""
import struct
import types

import pytest

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
    Box = lambda text, x, y, w, h: types.SimpleNamespace(text=text, bounds=Bounds(x=x, y=y, width=w, height=h))
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
