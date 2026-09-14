"""Execute a GitHub issue or issue list under a local repository profile."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def ticket_main(argv: list[str]) -> int:
    # Keep explicit local queue/list actions alongside the exact issue workflow.
    # An issue URL must never enter broad backlog synchronization or ID guessing.
    if argv and argv[0] == "auto" and len(argv) > 1 and argv[1].startswith("https://"):
        argv = argv[1:]
    elif argv and argv[0] in {"auto", "list"}:
        from koru.cli_ticket_queue import ticket_main as queue_main

        return queue_main(argv)
    from koru.ticket_command.batch import run_issue_list
    from koru.ticket_command.profile import parse_target
    from koru.ticket_command.service import run_ticket

    parser = argparse.ArgumentParser(
        prog="koru ticket",
        description="Execute an issue or successive open issues through the configured repository profile.",
        epilog="Profiles default to ~/.config/koru/tickets.json. C2004 uses clean main only; "
        "other configured repositories use canonical ticket worktrees and independent Validator delivery. "
        "Issue lists resume their saved selection after interruption; reported issues are not executed again. "
        "Use 'koru ticket auto --help' or 'koru ticket list --help' for local Planfile queue actions.",
    )
    parser.add_argument(
        "url", help="https://github.com/OWNER/REPO/issues/N or /issues/ (oldest first, stop on failure)"
    )
    parser.add_argument("--profiles", type=Path, default=Path.home() / ".config/koru/tickets.json")
    parser.add_argument(
        "--dry-run", action="store_true", help="Preview routing and read an issue list without executing or publishing"
    )
    args = parser.parse_args(argv)
    try:
        _, number = parse_target(args.url)
        execute = run_issue_list if number is None else run_ticket
        result = execute(args.url, args.profiles, dry_run=args.dry_run)
    except (ValueError, RuntimeError, OSError) as exc:
        print(f"koru ticket: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2))
    return 0 if result["state"] in {"planned", "reported", "completed"} else 1


if __name__ == "__main__":
    raise SystemExit(ticket_main(sys.argv[1:]))
