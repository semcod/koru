"""CLI for lane-scoped Koru environment control (koruenv)."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import UTC, datetime
from typing import Sequence

from koruenv.lane import build_lane_environ


def _normalize_log_format(raw: str | None) -> str:
    value = (raw or "").strip().lower()
    return value if value in {"human", "jsonl"} else "human"


def _iso_ts() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _emit_log(
    *,
    log_format: str,
    component: str,
    level: str,
    action: str,
    result: str,
    rc: int | None = None,
    **extra,
) -> None:
    if log_format != "jsonl":
        return
    row = {
        "ts": _iso_ts(),
        "corr": "koruenv-cli",
        "component": component,
        "level": level,
        "action": action,
        "result": result,
    }
    if rc is not None:
        row["rc"] = int(rc)
    row.update({k: v for k, v in extra.items() if v is not None})
    sys.stderr.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")
    sys.stderr.flush()


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="koruenv")
    parser.add_argument(
        "--log-format",
        choices=("human", "jsonl"),
        default=os.environ.get("KORUENV_LOG_FORMAT", "human"),
        help="logging format for koruenv diagnostic events",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_env = sub.add_parser("env", help="emit lane env exports")
    p_env.add_argument("ide")
    p_env.add_argument("instance")
    p_env.add_argument(
        "--shell",
        choices=("bash", "sh", "zsh", "powershell"),
        default="bash",
        help="output format for export statements",
    )

    p_run = sub.add_parser("run", help="run command in lane environment")
    p_run.add_argument("ide")
    p_run.add_argument("instance")
    p_run.add_argument("rest", nargs=argparse.REMAINDER)

    p_status = sub.add_parser("status", help="run `koru autopilot status --explain` in lane")
    p_status.add_argument("ide")
    p_status.add_argument("instance")
    p_status.add_argument(
        "--koru-cmd",
        default="koru",
        help="koru executable or command name (default: koru)",
    )
    return parser


def _render_exports(env_overlay: dict[str, str], *, shell: str) -> str:
    lines: list[str] = []
    if shell in {"bash", "sh", "zsh"}:
        for key, value in env_overlay.items():
            lines.append(f"export {key}={value}")
        return "\n".join(lines)
    for key, value in env_overlay.items():
        lines.append(f"$env:{key} = '{value}'")
    return "\n".join(lines)


def _strip_double_dash(rest: Sequence[str]) -> list[str]:
    parts = list(rest)
    if parts and parts[0] == "--":
        return parts[1:]
    return parts


def _run_with_overlay(argv: Sequence[str], overlay: dict[str, str], *, log_format: str) -> int:
    env = os.environ.copy()
    env.update(overlay)
    _emit_log(
        log_format=log_format,
        component="koruenv",
        level="info",
        action="run",
        result="started",
        argv=list(argv),
        instance=overlay.get("KORU_AUTOPILOT_INSTANCE"),
        ide=overlay.get("KORU_AUTOPILOT_IDE"),
    )
    try:
        proc = subprocess.run(list(argv), env=env, check=False)
    except KeyboardInterrupt:
        _emit_log(
            log_format=log_format,
            component="koruenv",
            level="warn",
            action="run",
            result="interrupted",
            rc=130,
        )
        return 130
    rc = int(proc.returncode)
    _emit_log(
        log_format=log_format,
        component="koruenv",
        level="info" if rc == 0 else "error",
        action="run",
        result="ok" if rc == 0 else "failed",
        rc=rc,
    )
    return rc


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    log_format = _normalize_log_format(args.log_format)

    try:
        env_overlay = build_lane_environ(ide=args.ide, instance=args.instance)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        _emit_log(
            log_format=log_format,
            component="koruenv",
            level="error",
            action="lane.resolve",
            result="failed",
            rc=2,
            reason=str(exc),
        )
        return 2

    if args.command == "env":
        _emit_log(
            log_format=log_format,
            component="koruenv",
            level="info",
            action="env",
            result="ok",
            ide=env_overlay.get("KORU_AUTOPILOT_IDE"),
            instance=env_overlay.get("KORU_AUTOPILOT_INSTANCE"),
            socket=env_overlay.get("KORU_AUTOPILOT_SOCKET"),
        )
        print(_render_exports(env_overlay, shell=args.shell))
        return 0

    if args.command == "status":
        command = [args.koru_cmd, "autopilot", "status", "--explain"]
        return _run_with_overlay(command, env_overlay, log_format=log_format)

    rest = _strip_double_dash(args.rest)
    if not rest:
        print("error: run requires '-- <command> [args...]'", file=sys.stderr)
        _emit_log(
            log_format=log_format,
            component="koruenv",
            level="error",
            action="run",
            result="failed",
            rc=2,
            reason="missing command",
        )
        return 2
    return _run_with_overlay(rest, env_overlay, log_format=log_format)


if __name__ == "__main__":
    raise SystemExit(main())
