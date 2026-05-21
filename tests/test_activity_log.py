"""Tests for real-time activity log."""

from __future__ import annotations

import sys
import types

import pytest

from koru import activity_log as al


def test_activity_flushes_with_timestamp(capsys: pytest.CaptureFixture[str]) -> None:
    al.activity("CHAT", "test message", preview="hello world", fmt="human")
    out = capsys.readouterr().out
    assert "koru ▸ CHAT:" in out
    assert "test message" in out
    assert "«hello world»" in out
    assert out.strip().startswith("[")


def test_activity_disabled(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("KORU_ACTIVITY_LOG", "0")
    al.activity("CHAT", "hidden")
    assert capsys.readouterr().out == ""


def test_activity_emits_nfo_event_when_configured(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    events: list[tuple[str, object]] = []
    fake_nfo = types.ModuleType("nfo")

    def configure(**kwargs):
        events.append(("configure", kwargs))

    def event(name, **kwargs):
        events.append((name, kwargs))

    fake_nfo.configure = configure
    fake_nfo.event = event
    monkeypatch.setitem(sys.modules, "nfo", fake_nfo)
    monkeypatch.setenv("KORU_NFO_LOG_PATH", str(tmp_path / "nfo-events.jsonl"))
    monkeypatch.setattr(al, "_NFO_CONFIGURED_PATH", None)
    monkeypatch.setattr(al, "_NFO_UNAVAILABLE", False)
    monkeypatch.setattr(al, "_NFO_UNAVAILABLE_WARNED", False)

    al.activity("CHAT", "test message", preview="hello", data={"ok": True}, fmt="human")

    assert "test message" in capsys.readouterr().out
    assert events[0][0] == "configure"
    assert events[1][0] == "koru.activity"
    payload = events[1][1]
    assert payload["category"] == "CHAT"
    assert payload["activity_message"] == "test message"
    assert payload["preview"] == "hello"
    assert payload["data"] == {"ok": True}


def test_activity_warns_once_when_nfo_fails(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    fake_nfo = types.ModuleType("nfo")

    def configure(**_kwargs):
        raise RuntimeError("boom")

    fake_nfo.configure = configure
    fake_nfo.event = lambda *_args, **_kwargs: None
    monkeypatch.setitem(sys.modules, "nfo", fake_nfo)
    monkeypatch.setenv("KORU_NFO_LOG_PATH", str(tmp_path / "nfo-events.jsonl"))
    monkeypatch.setattr(al, "_NFO_CONFIGURED_PATH", None)
    monkeypatch.setattr(al, "_NFO_UNAVAILABLE", False)
    monkeypatch.setattr(al, "_NFO_UNAVAILABLE_WARNED", False)

    al.activity("CHAT", "first", fmt="human")
    al.activity("CHAT", "second", fmt="human")

    err = capsys.readouterr().err
    assert err.count("nfo activity log disabled") == 1
