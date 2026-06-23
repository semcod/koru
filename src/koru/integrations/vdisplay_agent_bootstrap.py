"""Resolve vdisplay-agent URL when koru dashboard occupies :8765."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any

_KORU_DASHBOARD_MARKERS = ("koru dashboard", "<title>koru dashboard</title>")
_VDISPLAY_AGENT_SERVICE = "vdisplay-agent"
_DEFAULT_PORTS = (8765, 8766, 8767, 8776)
_KEEPER_START_HINT = (
    "Run once in a local GNOME terminal (same session as the agent): "
    "vdisplay agent screencast start --force  # choose All Screens or the IDE monitor"
)
_ELECTRON_BRIDGE_HINT = (
    "Use orchestrated stack: koru autopilot vdisplay-up --ide jetbrains "
    "(opens browser bridge; in Chrome/Chromium click Share screen, select the IDE monitor, "
    "keep the tab open); manual: vdisplay electron-share start"
)


def _fetch(url: str, *, timeout: float = 0.35) -> tuple[int, bytes]:
    with urllib.request.urlopen(url, timeout=timeout) as response:
        return int(response.status), response.read()


def _parse_health(raw: bytes) -> dict[str, Any] | None:
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def _screencast_status_data(payload: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return {}
    data = payload.get("data")
    return data if isinstance(data, dict) else payload


def _keeper_ready(status: dict[str, Any]) -> bool:
    if not (status.get("active") and status.get("ready")):
        return False
    if status.get("keeper_managed"):
        return bool(status.get("keeper_socket_path") or status.get("keeper_pid"))
    return bool(str(status.get("keeper_socket_path") or "").strip())


def _browser_bridge_ready(status: dict[str, Any]) -> bool:
    if status.get("capture_ready") and status.get("keeper_mode") == "browser_bridge":
        return True
    bridge = status.get("browser_bridge")
    if isinstance(bridge, dict) and bridge.get("capture_ready"):
        return True
    return False


def _wayland_session() -> bool:
    return bool((os.environ.get("WAYLAND_DISPLAY") or "").strip())


def is_vdisplay_agent_health(payload: object) -> bool:
    if not isinstance(payload, dict):
        return False
    if payload.get("ok") is not True:
        return False
    data = payload.get("data")
    if not isinstance(data, dict):
        return False
    service = str(data.get("service") or data.get("broker") or "").strip().lower()
    return service == _VDISPLAY_AGENT_SERVICE


def is_koru_dashboard_on_port(port: int, *, host: str = "127.0.0.1") -> bool:
    try:
        status, raw = _fetch(f"http://{host}:{port}/", timeout=0.25)
    except (urllib.error.URLError, TimeoutError, OSError, ValueError):
        return False
    if status != 200:
        return False
    text = raw[:4096].decode("utf-8", errors="replace").lower()
    return any(marker in text for marker in _KORU_DASHBOARD_MARKERS)


def probe_vdisplay_agent(base_url: str) -> bool:
    try:
        status, raw = _fetch(f"{base_url.rstrip('/')}/health")
    except (urllib.error.URLError, TimeoutError, OSError, ValueError):
        return False
    if status != 200:
        return False
    return is_vdisplay_agent_health(_parse_health(raw))


def resolve_vdisplay_agent_url(*, host: str = "127.0.0.1") -> str | None:
    """Pick vdisplay-agent base URL; prefer explicit env, then non-koru ports."""
    explicit = (
        os.environ.get("KORU_VDISPLAY_AGENT_URL")
        or os.environ.get("VDISPLAY_AGENT_URL")
        or ""
    ).strip()
    if explicit:
        base = explicit.rstrip("/")
        return base if probe_vdisplay_agent(base) else base

    port_env = os.environ.get("VDISPLAY_AGENT_PORT", "").strip()
    ports: list[int] = []
    if port_env.isdigit():
        ports.append(int(port_env))
    for port in _DEFAULT_PORTS:
        if port not in ports:
            ports.append(port)

    koru_on_8765 = is_koru_dashboard_on_port(8765, host=host)
    for port in ports:
        if koru_on_8765 and port == 8765:
            continue
        base = f"http://{host}:{port}"
        if probe_vdisplay_agent(base):
            return base
    return None


def apply_vdisplay_agent_env(*, host: str = "127.0.0.1") -> dict[str, Any]:
    """Set agent URL env vars when a broker is reachable."""
    url = resolve_vdisplay_agent_url(host=host)
    out: dict[str, Any] = {"agent_url": url, "applied": []}
    if not url:
        if is_koru_dashboard_on_port(8765, host=host):
            out["koru_dashboard_port_conflict"] = True
            out["hint"] = (
                "koru dashboard uses :8765 — start vdisplay-agent on another port, e.g. "
                "VDISPLAY_AGENT_PORT=8766 vdisplay-agent serve"
            )
        return out
    for key in ("KORU_VDISPLAY_AGENT_URL", "VDISPLAY_AGENT_URL"):
        if not os.environ.get(key, "").strip():
            os.environ[key] = url
            out["applied"].append(f"{key}={url}")
    return out


def _fetch_screencast_status(base: str) -> dict[str, Any] | None:
    try:
        _status_code, raw = _fetch(f"{base}/session/screencast/status", timeout=1.0)
    except (urllib.error.URLError, TimeoutError, OSError, ValueError):
        return None
    return _screencast_status_data(_parse_health(raw))


def ensure_screencast_session(*, agent_url: str | None = None) -> dict[str, Any]:
    """Check keeper-managed ScreenCast; never start portal capture from koru on Wayland."""
    base = (agent_url or resolve_vdisplay_agent_url() or "").rstrip("/")
    if not base:
        return {"ok": False, "skipped": True, "reason": "no vdisplay-agent URL"}

    status = _fetch_screencast_status(base) or {}
    if _browser_bridge_ready(status):
        return {
            "ok": True,
            "already_active": True,
            "keeper_managed": False,
            "browser_bridge": True,
            "keeper_mode": status.get("keeper_mode") or "browser_bridge",
            "agent_url": base,
            "status": status,
            "hint": "Electron browser bridge is capture_ready — no PipeWire keeper required",
        }
    if _keeper_ready(status):
        return {
            "ok": True,
            "already_active": True,
            "keeper_managed": True,
            "agent_url": base,
            "status": status,
        }

    if status.get("active"):
        bridge = status.get("browser_bridge")
        if isinstance(bridge, dict) and bridge.get("registered"):
            return {
                "ok": False,
                "already_active": True,
                "keeper_managed": False,
                "browser_bridge_pending": True,
                "agent_url": base,
                "status": status,
                "reason": "browser_bridge_pending_share",
                "hint": (
                    "Electron browser bridge is registered but not capture_ready yet. "
                    "Open the browser bridge, click Share screen, select the IDE monitor, "
                    "keep the tab open, then run vdisplay services status --source HDMI-1 "
                    "(check vdisplay electron-share health if it stays pending)"
                ),
            }
        return {
            "ok": False,
            "already_active": True,
            "keeper_managed": False,
            "agent_url": base,
            "status": status,
            "reason": "screencast_active_without_keeper",
            "hint": (
                "ScreenCast is active in vdisplay-agent but the keeper is not running "
                "(PipeWire capture will time out). "
                f"{_ELECTRON_BRIDGE_HINT} "
                f"Or: {_KEEPER_START_HINT} "
                "Then: vdisplay agent screencast probe --via-agent --source HDMI-1"
            ),
        }

    if _wayland_session():
        return {
            "ok": False,
            "skipped": True,
            "keeper_managed": False,
            "agent_url": base,
            "reason": "wayland_requires_keeper_cli",
            "hint": f"{_KEEPER_START_HINT} Alternatively: {_ELECTRON_BRIDGE_HINT}",
        }

    body = json.dumps({"interactive": False, "timeout_s": 30}).encode("utf-8")
    req = urllib.request.Request(
        f"{base}/session/screencast/start",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=45) as response:
            raw = response.read()
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:500]
        return {
            "ok": False,
            "agent_url": base,
            "error": detail or str(exc),
            "hint": _KEEPER_START_HINT,
        }
    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
        return {"ok": False, "agent_url": base, "error": str(exc)}

    payload = _parse_health(raw) or {}
    adopted = _screencast_status_data(payload)
    ok = payload.get("ok") is True and _keeper_ready(adopted)
    out: dict[str, Any] = {
        "ok": ok,
        "agent_url": base,
        "response": payload,
        "keeper_managed": _keeper_ready(adopted),
    }
    if not ok:
        out["hint"] = _KEEPER_START_HINT
    return out


def bootstrap_vdisplay_capture(*, host: str = "127.0.0.1") -> dict[str, Any]:
    """Apply agent env + check screencast keeper before observe/screenshot."""
    agent = apply_vdisplay_agent_env(host=host)
    sc = ensure_screencast_session(agent_url=agent.get("agent_url"))
    return {"agent": agent, "screencast": sc}


__all__ = [
    "apply_vdisplay_agent_env",
    "bootstrap_vdisplay_capture",
    "ensure_screencast_session",
    "is_koru_dashboard_on_port",
    "is_vdisplay_agent_health",
    "probe_vdisplay_agent",
    "resolve_vdisplay_agent_url",
]
