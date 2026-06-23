"""``koru autopilot vdisplay-up`` — start vdisplay services stack."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys


def _resolve_bridge_source(ide: str) -> str:
    explicit = __import__("os").environ.get("KORU_VDISPLAY_SOURCE", "").strip()
    if explicit:
        return explicit
    try:
        from koru.autopilot.ide import normalize_ide_id
        from koru.integrations.photo_vql_monitor import resolve_vdisplay_source_for_ide
        from koru.integrations.vdisplay_client import _desktop_probe

        source, _probe = resolve_vdisplay_source_for_ide(
            ide,
            canonical_ide=normalize_ide_id,
            desktop_probe=_desktop_probe,
        )
        return source
    except Exception:
        return "HDMI-1"


def action_vdisplay_up(args: argparse.Namespace) -> int:
    ide = str(getattr(args, "ide", "jetbrains") or "jetbrains").strip().lower()
    from koru.autonomous_vdisplay_defaults import apply_vdisplay_drive_defaults

    applied = apply_vdisplay_drive_defaults(ide=ide)
    if applied:
        print(f"koru autopilot vdisplay-up: env defaults → {', '.join(applied)}", file=sys.stderr)

    source = getattr(args, "source", None) or _resolve_bridge_source(ide)
    agent_url = getattr(args, "agent_url", None) or __import__("os").environ.get(
        "VDISPLAY_AGENT_URL", "http://127.0.0.1:8766"
    )
    port = int(getattr(args, "port", 8799) or 8799)

    try:
        from vdisplay.commands.services import handle_up as services_up

        ns = argparse.Namespace(
            host="127.0.0.1",
            port=port,
            timeout_s=float(getattr(args, "timeout_s", 3.0) or 3.0),
            instance=ide,
            target=ide,
            source=source,
            agent_url=agent_url,
            no_agent_bridge=False,
            mode="full",
            no_always_on_top=False,
            ozone_platform=None,
            startup_timeout_s=float(getattr(args, "startup_timeout_s", 25.0) or 25.0),
            agent_startup_timeout_s=float(
                getattr(args, "agent_startup_timeout_s", 15.0) or 15.0
            ),
            capture_timeout_s=float(getattr(args, "capture_timeout_s", 120.0) or 120.0),
            wait_capture=not bool(getattr(args, "no_wait_capture", False)),
            start_agent=not bool(getattr(args, "no_start_agent", False)),
            open_browser_bridge=not bool(getattr(args, "no_open_browser_bridge", False)),
            install=bool(getattr(args, "install", False)),
        )
        return services_up(ns)
    except ImportError:
        vdisplay_bin = shutil.which("vdisplay")
        if not vdisplay_bin:
            print(
                "vdisplay not found — install wronai/vdisplay in this venv or on PATH",
                file=sys.stderr,
            )
            return 1
        cmd = [
            vdisplay_bin,
            "services",
            "up",
            "--instance",
            ide,
            "--target",
            ide,
            "--source",
            source,
            "--port",
            str(port),
            "--agent-url",
            agent_url,
        ]
        if not getattr(args, "no_open_browser_bridge", False):
            cmd.append("--open-browser-bridge")
        if getattr(args, "no_wait_capture", False):
            cmd.append("--no-wait-capture")
        if getattr(args, "no_start_agent", False):
            cmd.append("--no-start-agent")
        return subprocess.run(cmd, check=False).returncode


__all__ = ["action_vdisplay_up"]
