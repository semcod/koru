"""Capture frames from OBS Studio via obs-websocket (v5 JSON protocol)."""

from __future__ import annotations

import base64
import hashlib
import json
import os
import time
import uuid
from collections.abc import Callable
from typing import Any

from koruvision.providers.base import MonitorSpec, ProviderAvailability, frame_from_png

_PROBE_CACHE: tuple[float, bool] | None = None
_PROBE_TTL_SECONDS = 5.0


def obs_url() -> str:
    return os.environ.get("KORU_OBS_URL", "ws://127.0.0.1:4455").strip() or "ws://127.0.0.1:4455"


def obs_password() -> str:
    return os.environ.get("KORU_OBS_PASSWORD", "").strip()


def obs_source_name() -> str:
    return os.environ.get("KORU_OBS_SOURCE", "Display Capture").strip() or "Display Capture"


def obs_screenshot_width() -> int:
    raw = os.environ.get("KORU_OBS_IMAGE_WIDTH", "1920").strip()
    try:
        return max(64, int(raw))
    except ValueError:
        return 1920


def _obs_auth(password: str, salt: str, challenge: str) -> str:
    secret = hashlib.sha256((password + salt).encode()).digest()
    secret_b64 = base64.b64encode(secret).decode("ascii")
    response = hashlib.sha256((secret_b64 + challenge).encode()).digest()
    return base64.b64encode(response).decode("ascii")


def _websockets_missing() -> bool:
    try:
        import websockets  # noqa: F401
    except ImportError:
        return True
    return False


def _with_obs_connection(
    fn: Callable[[Any], Any],
    *,
    url: str | None = None,
    password: str | None = None,
    open_timeout: float = 2.0,
) -> Any:
    if _websockets_missing():
        raise RuntimeError("obs_websocket: install koru[observe] (websockets)")
    from websockets.sync.client import connect

    ws_url = url or obs_url()
    secret = password if password is not None else obs_password()
    with connect(ws_url, open_timeout=open_timeout, close_timeout=open_timeout) as ws:
        hello_raw = ws.recv(timeout=open_timeout)
        hello = json.loads(hello_raw)
        if hello.get("op") != 0:
            raise RuntimeError(f"obs_websocket: unexpected hello op={hello.get('op')}")
        identify: dict[str, Any] = {"op": 1, "d": {"rpcVersion": 1, "eventSubscriptions": 0}}
        auth = (hello.get("d") or {}).get("authentication")
        if auth and secret:
            identify["d"]["authentication"] = _obs_auth(
                secret,
                str(auth.get("salt", "")),
                str(auth.get("challenge", "")),
            )
        ws.send(json.dumps(identify))
        identified = json.loads(ws.recv(timeout=open_timeout))
        if identified.get("op") != 2:
            detail = identified.get("d", {}).get("comment", "unknown")
            raise RuntimeError(
                f"obs_websocket: identify failed ({detail})"
            )
        return fn(ws)


def _obs_request(
    ws: Any,
    request_type: str,
    request_data: dict[str, Any] | None = None,
    *,
    timeout: float = 10.0,
) -> dict[str, Any]:
    request_id = f"koru-{uuid.uuid4().hex[:12]}"
    ws.send(
        json.dumps(
            {
                "op": 6,
                "d": {
                    "requestType": request_type,
                    "requestId": request_id,
                    "requestData": request_data or {},
                },
            }
        )
    )
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        raw = ws.recv(timeout=max(0.1, deadline - time.monotonic()))
        msg = json.loads(raw)
        if msg.get("op") != 7:
            continue
        data = msg.get("d") or {}
        if data.get("requestId") != request_id:
            continue
        status = data.get("requestStatus") or {}
        if not status.get("result", False):
            comment = status.get("comment") or status.get("code") or request_type
            raise RuntimeError(f"obs_websocket: {request_type} failed: {comment}")
        return data.get("responseData") or {}
    raise RuntimeError(f"obs_websocket: timed out waiting for {request_type}")


def probe_obs_reachable(*, force: bool = False) -> bool:
    """Return True when OBS WebSocket accepts a short identify handshake."""
    global _PROBE_CACHE
    now = time.monotonic()
    if not force and _PROBE_CACHE is not None:
        cached_at, cached = _PROBE_CACHE
        if now - cached_at < _PROBE_TTL_SECONDS:
            return cached
    if _websockets_missing():
        _PROBE_CACHE = (now, False)
        return False

    def _ping(ws: Any) -> bool:
        _obs_request(ws, "GetVersion", timeout=3.0)
        return True

    try:
        ok = bool(_with_obs_connection(_ping, open_timeout=1.5))
    except Exception:
        ok = False
    _PROBE_CACHE = (now, ok)
    return ok


def _run_obs_capture(fn: Callable[[Any], bytes]) -> bytes:
    return _with_obs_connection(fn)


def _capture_source_png(source_name: str | None = None) -> bytes:
    source = source_name or obs_source_name()
    width = obs_screenshot_width()

    def _shot(ws: Any) -> bytes:
        data = _obs_request(
            ws,
            "GetSourceScreenshot",
            {
                "sourceName": source,
                "imageFormat": "png",
                "imageWidth": width,
                "imageHeight": 0,
                "imageCompressionQuality": 100,
            },
        )
        image_b64 = data.get("imageData") or ""
        if not image_b64:
            raise RuntimeError(f"obs_websocket: empty screenshot for source {source!r}")
        return base64.b64decode(str(image_b64))

    return _run_obs_capture(_shot)


class ObsWebSocketProvider:
    name = "obs_websocket"
    streams = True

    def availability(self) -> ProviderAvailability:
        if _websockets_missing():
            return ProviderAvailability(
                available=False,
                reason="websockets package not installed",
                install_hint="pip install 'koru[observe]'",
            )
        if not probe_obs_reachable():
            return ProviderAvailability(
                available=False,
                reason=f"OBS WebSocket not reachable at {obs_url()}",
                install_hint=(
                    "Start OBS Studio and enable WebSocket server "
                    "(Tools → WebSocket Server Settings)"
                ),
            )
        return ProviderAvailability(
            available=True,
            reason=f"OBS WebSocket at {obs_url()}",
            install_hint=f"Source: {obs_source_name()} (KORU_OBS_SOURCE)",
        )

    def list_monitors(self) -> list[MonitorSpec]:
        return [
            MonitorSpec(
                id=0,
                output=obs_source_name(),
                width=obs_screenshot_width(),
                height=1080,
                is_primary=True,
            )
        ]

    def capture_all(self, scale: float) -> list[dict[str, Any]]:
        payload = _capture_source_png()
        return [
            frame_from_png(
                payload,
                monitor_id=0,
                scale=scale,
                output=obs_source_name(),
                provider=self.name,
            )
        ]

    def capture_one(self, monitor_id: int | None, scale: float) -> dict[str, Any]:
        del monitor_id
        return self.capture_all(scale)[0]
