"""Tests for real-time activity log."""

from __future__ import annotations

import io
import sys

import pytest

from koru import activity_log as al


def test_activity_flushes_with_timestamp(capsys: pytest.CaptureFixture[str]) -> None:
    al.activity("CHAT", "test message", preview="hello world", fmt="human")
    out = capsys.readouterr().out
    assert "koru ▸ CHAT:" in out
    assert "test message" in out
    assert "«hello world»" in out
    assert out.strip().startswith("[")


def test_activity_disabled(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setenv("KORU_ACTIVITY_LOG", "0")
    al.activity("CHAT", "hidden")
    assert capsys.readouterr().out == ""
