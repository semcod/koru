"""Tests for autonomous vdisplay env defaults."""

from __future__ import annotations

import os

import pytest

from koru.autonomous_vdisplay_defaults import apply_vdisplay_drive_defaults


def test_apply_vdisplay_defaults_jetbrains_wayland(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("WAYLAND_DISPLAY", "wayland-1")
    for key in (
        "KORU_VDISPLAY_CONTROL_FALLBACK",
        "KORU_VDISPLAY_SOURCE",
        "KORU_VDISPLAY_PREFER_PHOTO_VQL",
        "KORU_VDISPLAY_USE_VQL_MOUSE_FOCUS",
        "KORU_VDISPLAY_ALLOW_SURFACE_ONLY_ACTUATION",
    ):
        monkeypatch.delenv(key, raising=False)
    applied = apply_vdisplay_drive_defaults(ide="jetbrains")
    assert "KORU_VDISPLAY_CONTROL_FALLBACK=1" in applied
    assert "KORU_VDISPLAY_SOURCE" not in os.environ
    assert not any(item.startswith("KORU_VDISPLAY_ALLOW_SURFACE_ONLY_ACTUATION=") for item in applied)
    assert "KORU_VDISPLAY_ALLOW_SURFACE_ONLY_ACTUATION" not in os.environ


def test_apply_vdisplay_defaults_skips_when_already_set(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("WAYLAND_DISPLAY", "wayland-1")
    monkeypatch.setenv("KORU_VDISPLAY_SOURCE", "HDMI-1")
    applied = apply_vdisplay_drive_defaults(ide="jetbrains")
    assert os.environ["KORU_VDISPLAY_SOURCE"] == "HDMI-1"
    assert not any(item.startswith("KORU_VDISPLAY_SOURCE=") for item in applied)


def test_apply_vdisplay_defaults_skips_unsupported_ide(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("WAYLAND_DISPLAY", "wayland-1")
    monkeypatch.delenv("KORU_VDISPLAY_CONTROL_FALLBACK", raising=False)
    assert apply_vdisplay_drive_defaults(ide="emacs") == []


def test_apply_vdisplay_defaults_windsurf_wayland(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("WAYLAND_DISPLAY", "wayland-1")
    for key in (
        "KORU_VDISPLAY_CONTROL_FALLBACK",
        "KORU_VDISPLAY_SOURCE",
        "KORU_VDISPLAY_PREFER_PHOTO_VQL",
        "KORU_VDISPLAY_USE_VQL_MOUSE_FOCUS",
        "KORU_VDISPLAY_ALLOW_MAP_ON_MISMATCH",
    ):
        monkeypatch.delenv(key, raising=False)
    applied = apply_vdisplay_drive_defaults(ide="windsurf")
    assert "KORU_VDISPLAY_CONTROL_FALLBACK=1" in applied
