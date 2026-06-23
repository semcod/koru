"""Tests for vdisplay-agent URL resolution (koru dashboard port conflict)."""

from __future__ import annotations

import json

import pytest

from koru.integrations import vdisplay_agent_bootstrap as boot


def test_is_vdisplay_agent_health() -> None:
    assert boot.is_vdisplay_agent_health({"ok": True, "data": {"service": "vdisplay-agent"}})
    assert not boot.is_vdisplay_agent_health({"ok": True})
    assert not boot.is_vdisplay_agent_health({"ok": True, "data": {"service": "koru"}})


def test_is_koru_dashboard_on_port(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_fetch(url: str, *, timeout: float = 0.35) -> tuple[int, bytes]:
        if url.endswith(":8765/"):
            return 200, b"<title>koru dashboard</title>"
        return 404, b""

    monkeypatch.setattr(boot, "_fetch", fake_fetch)
    assert boot.is_koru_dashboard_on_port(8765) is True
    assert boot.is_koru_dashboard_on_port(8766) is False


def test_resolve_skips_koru_dashboard_port(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_fetch(url: str, *, timeout: float = 0.35) -> tuple[int, bytes]:
        if url.endswith(":8765/health"):
            return 200, json.dumps({"ok": True}).encode()
        if url.endswith(":8765/"):
            return 200, b"<title>koru dashboard</title>"
        if url.endswith(":8766/health"):
            return 200, json.dumps({"ok": True, "data": {"service": "vdisplay-agent"}}).encode()
        raise OSError("unreachable")

    monkeypatch.setattr(boot, "_fetch", fake_fetch)
    monkeypatch.delenv("KORU_VDISPLAY_AGENT_URL", raising=False)
    monkeypatch.delenv("VDISPLAY_AGENT_URL", raising=False)
    assert boot.resolve_vdisplay_agent_url() == "http://127.0.0.1:8766"


def test_apply_vdisplay_agent_env_sets_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(boot, "resolve_vdisplay_agent_url", lambda **k: "http://127.0.0.1:8766")
    monkeypatch.delenv("VDISPLAY_AGENT_URL", raising=False)
    applied = boot.apply_vdisplay_agent_env()
    assert applied["agent_url"] == "http://127.0.0.1:8766"
    assert "VDISPLAY_AGENT_URL=http://127.0.0.1:8766" in applied["applied"]


def test_ensure_screencast_session_accepts_browser_bridge(monkeypatch: pytest.MonkeyPatch) -> None:
    status = {
        "ok": True,
        "data": {
            "active": True,
            "ready": True,
            "capture_ready": True,
            "keeper_mode": "browser_bridge",
            "browser_bridge": {
                "registered": True,
                "sharing": True,
                "capture_ready": True,
                "last_frame_age_ms": 120,
            },
        },
    }

    def fake_fetch(url: str, *, timeout: float = 0.35) -> tuple[int, bytes]:
        if url.endswith("/session/screencast/status"):
            return 200, json.dumps(status).encode()
        raise AssertionError(f"unexpected fetch: {url}")

    monkeypatch.setattr(boot, "_fetch", fake_fetch)
    out = boot.ensure_screencast_session(agent_url="http://127.0.0.1:8766")
    assert out["ok"] is True
    assert out["browser_bridge"] is True
    assert out["keeper_mode"] == "browser_bridge"


def test_ensure_screencast_session_accepts_keeper_managed(monkeypatch: pytest.MonkeyPatch) -> None:
    status = {
        "ok": True,
        "data": {
            "active": True,
            "ready": True,
            "keeper_managed": True,
            "keeper_socket_path": "/run/user/1000/vdisplay-screencast.sock",
        },
    }

    def fake_fetch(url: str, *, timeout: float = 0.35) -> tuple[int, bytes]:
        if url.endswith("/session/screencast/status"):
            return 200, json.dumps(status).encode()
        raise AssertionError(f"unexpected fetch: {url}")

    monkeypatch.setattr(boot, "_fetch", fake_fetch)
    out = boot.ensure_screencast_session(agent_url="http://127.0.0.1:8766")
    assert out["ok"] is True
    assert out["keeper_managed"] is True


def test_ensure_screencast_session_pending_browser_bridge(monkeypatch: pytest.MonkeyPatch) -> None:
    status = {
        "ok": True,
        "data": {
            "active": True,
            "ready": True,
            "capture_ready": False,
            "keeper_managed": False,
            "browser_bridge": {
                "registered": True,
                "sharing": False,
                "capture_ready": False,
            },
        },
    }

    def fake_fetch(url: str, *, timeout: float = 0.35) -> tuple[int, bytes]:
        if url.endswith("/session/screencast/status"):
            return 200, json.dumps(status).encode()
        raise AssertionError(f"unexpected fetch: {url}")

    monkeypatch.setattr(boot, "_fetch", fake_fetch)
    out = boot.ensure_screencast_session(agent_url="http://127.0.0.1:8766")
    assert out["ok"] is False
    assert out["reason"] == "browser_bridge_pending_share"
    assert out["browser_bridge_pending"] is True
    assert "electron-share health" in out["hint"].lower()


def test_ensure_screencast_session_rejects_active_without_keeper(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    status = {
        "ok": True,
        "data": {
            "active": True,
            "ready": True,
            "keeper_managed": False,
            "keeper_socket_path": "",
        },
    }

    def fake_fetch(url: str, *, timeout: float = 0.35) -> tuple[int, bytes]:
        if url.endswith("/session/screencast/status"):
            return 200, json.dumps(status).encode()
        raise AssertionError(f"unexpected fetch: {url}")

    monkeypatch.setattr(boot, "_fetch", fake_fetch)
    out = boot.ensure_screencast_session(agent_url="http://127.0.0.1:8766")
    assert out["ok"] is False
    assert out["reason"] == "screencast_active_without_keeper"
    assert "keeper" in out["hint"].lower()


def test_ensure_screencast_session_skips_rest_start_on_wayland(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    status = {"ok": True, "data": {"active": False, "ready": False}}

    def fake_fetch(url: str, *, timeout: float = 0.35) -> tuple[int, bytes]:
        if url.endswith("/session/screencast/status"):
            return 200, json.dumps(status).encode()
        raise AssertionError(f"unexpected fetch: {url}")

    monkeypatch.setattr(boot, "_fetch", fake_fetch)
    monkeypatch.setenv("WAYLAND_DISPLAY", "wayland-0")
    out = boot.ensure_screencast_session(agent_url="http://127.0.0.1:8766")
    assert out["ok"] is False
    assert out["reason"] == "wayland_requires_keeper_cli"
    assert "screencast start --force" in out["hint"]
    assert "electron-share" in out["hint"]
