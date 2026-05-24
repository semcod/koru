"""CLI for ``koru ide doctor`` — IDE bridge diagnostics."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from koru.autopilot import default_socket_path
from koru.ide_adapters.bridge import (
    apply_bridge_fixes,
    evaluate_bridge,
    format_bridge_text,
    gc_stale_sockets_for_lane,
)
from koru.ide_adapters.registry import get_adapter, supported_adapter_ids
from koruide.ide import normalize_ide_id
from koruide.plugin_installer import resolve_target_ide


def _resolve_ide(raw: str) -> str | None:
    if raw == "auto":
        return resolve_target_ide("auto")
    return normalize_ide_id(raw)


def _resolve_socket(args: argparse.Namespace, ide: str) -> Path:
    if args.socket:
        return Path(args.socket).expanduser().resolve()
    if args.instance:
        import os

        os.environ["KORU_AUTOPILOT_INSTANCE"] = args.instance
    return default_socket_path()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="koru ide")
    sub = parser.add_subparsers(dest="action", required=True)
    doctor = sub.add_parser(
        "doctor",
        help="Diagnose autopilot daemon + IDE plugin bridge for one IDE lane.",
    )
    doctor.add_argument("--ide", default="auto", help=f"IDE lane (default: auto). Supported: {', '.join(supported_adapter_ids())}")
    doctor.add_argument("--project", type=Path, default=Path.cwd(), help="Project root for workspace settings checks.")
    doctor.add_argument("--socket", type=Path, default=None, help="Autopilot socket override.")
    doctor.add_argument("--instance", default=None, help="Set KORU_AUTOPILOT_INSTANCE for this run (e.g. cursor).")
    doctor.add_argument("--fix", action="store_true", help="Apply safe auto-fixes (workspace socket, trusted publisher when IDE closed).")
    doctor.add_argument("--gc-sockets", action="store_true", help="Remove stale koru-autopilot-*.sock files before checks.")
    doctor.add_argument(
        "--format",
        dest="output_format",
        choices=("text", "json"),
        default="text",
    )
    doctor.add_argument("--explain", action="store_true", help="Always print hypothesis details.")
    return parser


def action_ide_doctor(args: argparse.Namespace) -> int:
    ide = _resolve_ide(args.ide)
    if ide is None:
        print("koru ide doctor: could not resolve IDE (pass --ide cursor|vscode|...)", file=sys.stderr)
        return 2
    if get_adapter(ide) is None:
        print(f"koru ide doctor: no adapter for ide={ide}", file=sys.stderr)
        return 2
    project = args.project.expanduser().resolve()
    socket_path = _resolve_socket(args, ide)
    removed: list[str] = []
    if args.gc_sockets:
        removed = gc_stale_sockets_for_lane(socket_path)
    status = evaluate_bridge(ide=ide, socket_path=socket_path, project=project)
    status = apply_bridge_fixes(status, project=project, fix=args.fix)
    if removed:
        status.fixes_applied = [*status.fixes_applied, *[f"removed stale socket {p}" for p in removed]]
    if args.output_format == "json":
        payload = {
            "ide": status.ide,
            "socket": status.socket_path,
            "daemon_running": status.daemon_running,
            "plugins_connected": status.plugins_connected,
            "ready": status.ready,
            "project": status.project,
            "fixes_applied": status.fixes_applied,
            "hypotheses": [
                {
                    "id": h.id,
                    "confidence": h.confidence,
                    "evidence": h.evidence,
                    "remediation": {
                        "kind": h.remediation.kind,
                        "summary": h.remediation.summary,
                        "command": h.remediation.command,
                    },
                }
                for h in status.hypotheses
            ],
        }
        if status.settings is not None:
            payload["settings"] = {
                "expected_socket": status.settings.expected_socket,
                "user_socket": status.settings.user_socket,
                "workspace_socket": status.settings.workspace_socket,
                "mismatch": status.settings.mismatch,
            }
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0 if status.ready else 1
    print(format_bridge_text(status, explain=args.explain))
    return 0 if status.ready else 1


def ide_main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.action == "doctor":
        return action_ide_doctor(args)
    parser.error(f"unknown action: {args.action}")
    return 2
