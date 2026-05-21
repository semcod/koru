"""CLI command for managing CI/quality gate authorizations."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from koru.events import emit_management_event
from koru.gate import VALID_MODES as GATE_VALID_MODES
from koru.gate import authorize_gate


def build_gate_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="koru gate",
        description=(
            "Manage CI/quality gate authorizations on planfile tickets. Subcommands: authorize."
        ),
    )
    sub = parser.add_subparsers(dest="subcommand", required=True)

    auth = sub.add_parser(
        "authorize",
        help="Record an advisory waiver / explicit gate authorization on a ticket.",
        description=(
            "Append a structured KORU-GATE-AUTH note to the ticket. The note "
            "records who authorized which gate mode, why, and which gates "
            "were skipped — so the audit trail is parseable, not buried in "
            "free-text."
        ),
    )
    auth.add_argument("ticket_id", help="Ticket ID (e.g. PLF-070).")
    auth.add_argument(
        "--mode",
        required=True,
        choices=list(GATE_VALID_MODES),
        help=(
            "advisory: agent ran a subset; full CI deferred. "
            "auto: full CI executed by queue. "
            "mandatory_human: do not advance until a human verifies."
        ),
    )
    auth.add_argument(
        "--skipped",
        action="append",
        default=[],
        help=(
            "Gate name skipped under this authorization "
            "(repeat for multiple gates, e.g. --skipped 'task test' "
            "--skipped 'task quality:gate')."
        ),
    )
    auth.add_argument(
        "--reason",
        required=True,
        help=(
            "Why the waiver was granted. Future readers (and your future "
            "self) need this — keep it specific."
        ),
    )
    auth.add_argument(
        "--authorized-by",
        default=None,
        help="Override the actor identifier (defaults to $USER / $LOGNAME).",
    )
    auth.add_argument(
        "--project",
        type=Path,
        default=Path.cwd(),
        help="Project root containing .planfile/.",
    )
    return parser


def gate_main(argv: list[str]) -> int:
    args = build_gate_parser().parse_args(argv)
    if args.subcommand != "authorize":
        print(f"koru gate: unknown subcommand {args.subcommand!r}", file=sys.stderr)
        return 2
    try:
        auth = authorize_gate(
            args.ticket_id,
            mode=args.mode,
            skipped=args.skipped,
            reason=args.reason,
            project=args.project,
            authorized_by=args.authorized_by,
        )
    except ValueError as exc:
        print(f"koru gate authorize: {exc}", file=sys.stderr)
        return 2
    except RuntimeError as exc:
        print(f"koru gate authorize: {exc}", file=sys.stderr)
        return 1

    print(
        f"koru gate: ✓ {auth.mode} waiver recorded on {auth.ticket} "
        f"by {auth.authorized_by} at {auth.authorized_at}",
    )
    if auth.skipped:
        print(f"  skipped: {', '.join(auth.skipped)}")
    print(f"  reason : {auth.reason}")
    emit_management_event(
        tool="koru.gate",
        action="authorized",
        status="completed",
        message=f"{auth.mode} waiver on {auth.ticket}",
        details={
            "ticket": auth.ticket,
            "mode": auth.mode,
            "skipped": list(auth.skipped),
            "reason": auth.reason,
        },
    )
    return 0
