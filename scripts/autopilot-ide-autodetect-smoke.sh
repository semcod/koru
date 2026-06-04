#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export PYTHONPATH="${ROOT_DIR}/src:${PYTHONPATH:-}"

python3 - "$@" <<'PY'
from __future__ import annotations

import argparse
import json
import tempfile
import threading
import time
from pathlib import Path

from koru.autopilot.client import AutopilotClient
from koru.autopilot.daemon import AutopilotDaemon
from koru.autopilot.ide import detect_focused_ide_id, detect_running_ides, pick_target
from gillm.injection import InjectionResult


class StubInjector:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def type_text(
        self,
        text: str,
        *,
        ide: str = "default",
        submit: bool = True,
        dry_run: bool = False,
    ) -> InjectionResult:
        self.calls.append(
            {
                "text": text,
                "ide": ide,
                "submit": submit,
                "dry_run": dry_run,
            }
        )
        return InjectionResult(backend="stub", submitted=submit, dry_run=dry_run)


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="autopilot-ide-autodetect-smoke",
        description=(
            "Smoke-check koru autopilot IDE autodetection/routing without typing into the real keyboard."
        ),
    )
    p.add_argument(
        "--text",
        default="koru autopilot autodetect smoke",
        help="Payload used in drive requests.",
    )
    p.add_argument(
        "--socket",
        default=None,
        help="Optional unix-socket path (default: temporary socket).",
    )
    p.add_argument(
        "--require-running-ide",
        action="store_true",
        help="Fail if no running IDEs are detected.",
    )
    p.add_argument(
        "--check-ide",
        action="append",
        default=[],
        choices=["windsurf", "jetbrains", "vscode", "cursor", "zed"],
        help="Extra explicit IDE routing check(s). Repeat to check multiple IDs.",
    )
    return p


def main() -> int:
    args = _parser().parse_args()

    detected = detect_running_ides()
    focused = detect_focused_ide_id()

    if args.require_running_ide and not detected:
        print(
            json.dumps(
                {
                    "ok": False,
                    "reason": "no running IDE detected",
                    "detected": [],
                    "focused_ide": focused,
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 2

    check_ids: list[str] = ["auto"]
    for ide_id in ("windsurf", "jetbrains"):
        if any(i.id == ide_id for i in detected) and ide_id not in check_ids:
            check_ids.append(ide_id)
    for ide_id in args.check_ide:
        if ide_id not in check_ids:
            check_ids.append(ide_id)

    expected_auto = pick_target(detected, prefer=None, focused_id=focused)
    expected_auto_id = expected_auto.id if expected_auto is not None else "default"

    injector = StubInjector()
    sock_path = Path(args.socket) if args.socket else (Path(tempfile.mkdtemp()) / "autopilot-smoke.sock")
    daemon = AutopilotDaemon(socket_path=sock_path, injector=injector)
    thread: threading.Thread | None = None

    results: dict[str, dict[str, object]] = {}
    failures: list[str] = []

    try:
        daemon.start()
        thread = threading.Thread(target=daemon.serve_forever, daemon=True)
        thread.start()
        time.sleep(0.05)

        client = AutopilotClient(socket_path=sock_path, timeout=2.0)

        for check_id in check_ids:
            if check_id != "auto" and not any(i.id == check_id for i in detected):
                results[check_id] = {
                    "ok": False,
                    "reason": f"IDE {check_id!r} not running",
                    "expected_routed_ide": check_id,
                    "actual_routed_ide": None,
                }
                failures.append(check_id)
                continue

            before_calls = len(injector.calls)
            reply = client.drive(args.text, submit=False, ide=check_id)
            after_calls = len(injector.calls)
            routed_ide = None
            if after_calls > before_calls:
                routed_ide = str(injector.calls[-1].get("ide"))

            expected = expected_auto_id if check_id == "auto" else check_id
            ok = bool(reply.get("ok", False)) and routed_ide == expected
            if not ok:
                failures.append(check_id)

            results[check_id] = {
                "ok": ok,
                "expected_routed_ide": expected,
                "actual_routed_ide": routed_ide,
                "daemon_reply_ok": bool(reply.get("ok", False)),
                "daemon_reply_backend": reply.get("backend"),
                "daemon_reply_ide": (
                    reply.get("ide", {}).get("id") if isinstance(reply.get("ide"), dict) else None
                ),
            }
    finally:
        daemon.stop()
        if thread is not None:
            thread.join(timeout=2.0)
        try:
            if sock_path.exists():
                sock_path.unlink()
        except OSError:
            pass

    payload = {
        "ok": len(failures) == 0,
        "session_checks": check_ids,
        "focused_ide": focused,
        "detected": [i.to_dict() for i in detected],
        "results": results,
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
PY
