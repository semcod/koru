"""Execute an explicitly requested GitHub issue under a local repository profile."""

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
    from koru.ticket_command.service import run_ticket

    parser = argparse.ArgumentParser(
        prog="koru ticket",
        description="Execute one issue through its operator-configured repository profile.",
        epilog="Profiles default to ~/.config/koru/tickets.json. C2004 uses clean main only; "
        "other configured repositories use canonical ticket worktrees and independent Validator delivery. "
        "Use 'koru ticket auto --help' or 'koru ticket list --help' for local Planfile queue actions.",
    )
    parser.add_argument("url", help="Exact https://github.com/OWNER/REPO/issues/N URL")
    parser.add_argument("--profiles", type=Path, default=Path.home() / ".config/koru/tickets.json")
    parser.add_argument("--dry-run", action="store_true", help="Validate local routing without executing or publishing")
    args = parser.parse_args(argv)
    try:
        result = run_ticket(args.url, args.profiles, dry_run=args.dry_run)
    except (ValueError, RuntimeError, OSError) as exc:
        print(f"koru ticket: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2))
    return 0 if result["state"] in {"planned", "reported"} else 1


if __name__ == "__main__":
    raise SystemExit(ticket_main(sys.argv[1:]))
