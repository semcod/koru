"""``koru autopilot diagnose-vdisplay`` — probe vision LLM chat detection on latest capture."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def _latest_jetbrains_capture(root: Path) -> Path | None:
    matches = sorted(
        root.glob(".vdisplay/*/*koru-jetbrains/observe/capture.png"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    return matches[0] if matches else None


def action_diagnose_vdisplay(args: argparse.Namespace) -> int:
    from koru.autonomous_vdisplay_defaults import apply_vdisplay_drive_defaults

    ide = (args.ide or "jetbrains").strip().lower()
    applied = apply_vdisplay_drive_defaults(ide=ide)
    if applied:
        print(f"koru autopilot diagnose-vdisplay: env defaults → {', '.join(applied)}", file=sys.stderr)

    png = Path(args.png).expanduser() if args.png else _latest_jetbrains_capture(Path.cwd())
    if png is None or not png.is_file():
        print(
            json.dumps(
                {
                    "ok": False,
                    "error": "no capture.png found — run: koru autopilot prepare-vdisplay --ide jetbrains",
                },
                indent=2,
            )
        )
        return 1

    try:
        from vdisplay.integrations.chat_target import diagnose_chat_target_resolution
    except ImportError as exc:
        print(json.dumps({"ok": False, "error": f"vdisplay not installed: {exc}"}, indent=2))
        return 1

    source = __import__("os").environ.get("KORU_VDISPLAY_SOURCE", "DP-1")
    out = diagnose_chat_target_resolution(
        png,
        ide=ide,
        source=source,
        layers=[],
        capture_validation={"capture_confirmed": False, "ok_for_drive": False},
    )
    print(json.dumps(out, indent=2))
    return 0 if out.get("ok") else 1


__all__ = ["action_diagnose_vdisplay"]
