"""Tests for :mod:`koruvision.providers.obs_websocket`."""

from __future__ import annotations

import base64
import json
import struct
from unittest import mock

from koruvision.providers.obs_websocket import (
    ObsWebSocketProvider,
    _obs_auth,
    _obs_request,
    probe_obs_reachable,
)


def _png(width: int = 8, height: int = 6) -> bytes:
    return b"\x89PNG\r\n\x1a\n" + b"\x00\x00\x00\rIHDR" + struct.pack(">II", width, height)


def test_obs_auth_matches_protocol() -> None:
    # Golden vector from OBS WebSocket 5 docs (password "secret", fixed salt/challenge).
    auth = _obs_auth("secret", "abc", "def")
    assert isinstance(auth, str)
    assert len(auth) > 16


def test_probe_obs_reachable_uses_cache(monkeypatch) -> None:
    calls = {"n": 0}

    def fake_connect(fn, **kwargs):
        calls["n"] += 1
        return True

    monkeypatch.setattr(
        "koruvision.providers.obs_websocket._with_obs_connection",
        lambda fn, **kw: fake_connect(fn),
    )
    monkeypatch.setattr("koruvision.providers.obs_websocket._websockets_missing", lambda: False)
    assert probe_obs_reachable(force=True) is True
    assert probe_obs_reachable() is True
    assert calls["n"] == 1


def test_obs_request_parses_screenshot_response() -> None:
    class FakeWs:
        def __init__(self) -> None:
            self.sent: list[str] = []

        def send(self, payload: str) -> None:
            self.sent.append(payload)

        def recv(self, timeout: float = 10.0) -> str:
            req = json.loads(self.sent[-1])
            req_id = req["d"]["requestId"]
            return json.dumps(
                {
                    "op": 7,
                    "d": {
                        "requestId": req_id,
                        "requestStatus": {"result": True},
                        "responseData": {
                            "imageData": base64.b64encode(_png()).decode("ascii"),
                        },
                    },
                }
            )

    data = _obs_request(FakeWs(), "GetSourceScreenshot", {"sourceName": "Display Capture"})
    assert base64.b64decode(data["imageData"])[:8] == b"\x89PNG\r\n\x1a\n"


def test_obs_provider_capture_one(monkeypatch) -> None:
    monkeypatch.setenv("KORU_OBS_SOURCE", "Screen 1")
    monkeypatch.setattr(
        "koruvision.providers.obs_websocket._run_obs_capture",
        lambda fn: fn(FakeWsForCapture()),
    )
    monkeypatch.setattr(
        "koruvision.providers.obs_websocket.probe_obs_reachable",
        lambda **kw: True,
    )
    provider = ObsWebSocketProvider()
    frame = provider.capture_one(None, scale=0.5)
    assert frame["output"] == "Screen 1"
    assert frame["monitor_id"] == 0
    assert frame["payload"][:8] == b"\x89PNG\r\n\x1a\n"


class FakeWsForCapture:
    def __init__(self) -> None:
        self.sent: list[str] = []

    def send(self, payload: str) -> None:
        self.sent.append(payload)

    def recv(self, timeout: float = 10.0) -> str:
        req = json.loads(self.sent[-1])
        req_id = req["d"]["requestId"]
        return json.dumps(
            {
                "op": 7,
                "d": {
                    "requestId": req_id,
                    "requestStatus": {"result": True},
                    "responseData": {
                        "imageData": base64.b64encode(_png(10, 8)).decode("ascii"),
                    },
                },
            }
        )


def test_rank_puts_obs_first_when_reachable(monkeypatch) -> None:
    monkeypatch.setenv("KORU_VISION_PROVIDER", "auto")
    monkeypatch.setenv("XDG_SESSION_TYPE", "wayland")
    with mock.patch(
        "koruvision.providers.portal_screencast.PortalScreenCastProvider.availability",
        return_value=mock.Mock(available=True, reason="", install_hint="", needs_consent=True),
    ), mock.patch(
        "koruvision.providers.obs_websocket.probe_obs_reachable",
        return_value=True,
    ), mock.patch(
        "koruvision.providers.obs_websocket._websockets_missing",
        return_value=False,
    ), mock.patch(
        "koruvision.providers.mss.MssProvider.availability",
        return_value=mock.Mock(available=True, reason="", install_hint="", needs_consent=False),
    ):
        from koruvision.providers.detector import rank_providers

        names = [p.name for p in rank_providers()]
    assert names[0] == "obs_websocket"
    assert "portal_screencast" in names


def test_rank_forced_obs_skips_probe(monkeypatch) -> None:
    monkeypatch.setenv("KORU_VISION_PROVIDER", "obs")
    from koruvision.providers.detector import rank_providers

    ranked = rank_providers()
    assert len(ranked) == 1
    assert ranked[0].name == "obs_websocket"
