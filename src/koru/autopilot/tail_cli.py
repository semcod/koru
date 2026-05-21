"""CLI action for reading the autopilot audit log."""

from __future__ import annotations

import argparse
import json
import sys

from koruide.audit import default_log_path


def format_tail_entry(entry: dict) -> str:
    """Render one audit-log line as a single text row."""
    ts = entry.get("ts", "?")
    event = entry.get("event", "?")
    parts = [ts, event]
    for key in (
        "ide",
        "backend",
        "chars",
        "submit",
        "ok",
        "chat",
        "reason",
        "version",
        "source",
        "socket",
        "handoff",
        "error",
    ):
        if key in entry and entry[key] is not None:
            parts.append(f"{key}={entry[key]}")
    return "  ".join(str(p) for p in parts)


def render_tail_json(tail: list[str]) -> None:
    """Render tail output in JSON format."""
    parsed = []
    for line in tail:
        try:
            parsed.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    print(json.dumps(parsed, indent=2, sort_keys=True))


def render_tail_text(tail: list[str]) -> None:
    """Render tail output in text format."""
    for line in tail:
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        print(format_tail_entry(entry))


def action_tail(args: argparse.Namespace) -> int:
    """Dump the last ``--lines`` audit entries."""
    log_path = args.log or default_log_path()
    if not log_path.is_file():
        print(f"koru autopilot tail: no log at {log_path}", file=sys.stderr)
        return 1
    try:
        raw = log_path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError as exc:
        print(f"koru autopilot tail: {exc}", file=sys.stderr)
        return 1
    tail = raw[-args.lines :] if args.lines > 0 else raw
    if args.output_format == "json":
        render_tail_json(tail)
        return 0
    render_tail_text(tail)
    return 0
