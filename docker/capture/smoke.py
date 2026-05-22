"""Cross-OS smoke test for the koruvision provider stack.

Runs inside the docker/capture/* containers. Emits a single JSON line to
stdout on success and exits non-zero on the first hard failure so that the
outer test harness (`tests/test_docker_capture.py`) can parse + assert.
"""

from __future__ import annotations

import argparse
import json
import os
import struct
import sys
from typing import Any


_PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


def _png_size(payload: bytes) -> tuple[int, int]:
    if len(payload) < 24 or not payload.startswith(_PNG_MAGIC):
        return (0, 0)
    width, height = struct.unpack(">II", payload[16:24])
    return (int(width), int(height))


def _scan_providers() -> dict[str, Any]:
    from koruvision.providers.detector import list_provider_status, rank_providers

    rows = list_provider_status()
    ranked = [provider.name for provider in rank_providers()]
    return {"providers": rows, "ranked": ranked}


def _diagnostics_payload() -> dict[str, Any]:
    from pathlib import Path

    from koruobserve.diagnostics import capture_diagnostics

    return capture_diagnostics(Path(os.getcwd()))


def _capture_one() -> dict[str, Any]:
    from koruvision.capture import capture_monitor_png

    frame = capture_monitor_png(monitor_id=0, scale=0.5)
    width, height = _png_size(frame.payload)
    return {
        "ok": True,
        "monitor_id": frame.monitor_id,
        "mime": frame.mime,
        "width": frame.width,
        "height": frame.height,
        "payload_bytes": len(frame.payload),
        "png_width": width,
        "png_height": height,
        "output": frame.output,
    }


def _capture_all() -> dict[str, Any]:
    from koruvision.capture import capture_all_monitors

    frames = capture_all_monitors(scale=0.5)
    return {
        "ok": True,
        "count": len(frames),
        "frames": [
            {
                "monitor_id": frame.monitor_id,
                "width": frame.width,
                "height": frame.height,
                "output": frame.output,
                "payload_bytes": len(frame.payload),
            }
            for frame in frames
        ],
    }


def _run_headless() -> dict[str, Any]:
    """Headless: every silent provider must fail; diagnostics must be 'blocked' or 'no-log'."""
    providers = _scan_providers()
    diagnostics = _diagnostics_payload()
    capture: dict[str, Any] = {"ok": False}
    try:
        capture = _capture_one()
    except Exception as exc:  # noqa: BLE001
        capture = {"ok": False, "error": str(exc)[:400]}
    expectation_ok = capture["ok"] is False  # truly headless = capture must fail
    return {
        "mode": "headless",
        "providers": providers,
        "diagnostics": diagnostics,
        "capture": capture,
        "expectation_ok": expectation_ok,
    }


def _run_x11() -> dict[str, Any]:
    """X11 + Xvfb: mss provider must capture at least one monitor."""
    providers = _scan_providers()
    diagnostics = _diagnostics_payload()
    capture = _capture_one()
    capture_all = _capture_all()
    expectation_ok = bool(
        capture.get("ok")
        and capture.get("payload_bytes", 0) > 100
        and capture_all.get("count", 0) >= 1
    )
    return {
        "mode": "x11",
        "providers": providers,
        "diagnostics": diagnostics,
        "capture": capture,
        "capture_all": capture_all,
        "expectation_ok": expectation_ok,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("headless", "x11"), required=True)
    parser.add_argument("--explain", action="store_true")
    args = parser.parse_args(argv)

    if args.mode == "headless":
        result = _run_headless()
    else:
        result = _run_x11()

    payload = json.dumps(result, sort_keys=True)
    print(payload)
    if args.explain:
        sys.stderr.write(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return 0 if result.get("expectation_ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
