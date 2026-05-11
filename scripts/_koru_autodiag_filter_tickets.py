#!/usr/bin/env python3
"""Filter planfile `ticket list --format json` output to [AUTO-DIAG] tickets.

Reads the JSON array from stdin and prints one ticket id per line for every
open ticket whose `name` contains `[AUTO-DIAG]`. When `--check <name>` is
supplied (and not `all`), only rows matching `[AUTO-DIAG] <check> …` are kept.
Used by scripts/koru-autoloop-reset-diag-markers.sh to avoid embedding Python
inside a shell heredoc.
"""

from __future__ import annotations

import argparse
import json
import re
import sys


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        default="all",
        help="Diagnostic check name filter (e.g. regix). Use 'all' to match any.",
    )
    args = parser.parse_args()
    check = (args.check or "all").lower()

    try:
        data = json.load(sys.stdin)
    except Exception:
        data = []

    if not isinstance(data, list):
        return 0

    pattern = re.compile(r"\[AUTO-DIAG\]\s+(\S+)\s+", re.IGNORECASE)
    for entry in data:
        if not isinstance(entry, dict):
            continue
        name = entry.get("name") or ""
        if "[AUTO-DIAG]" not in name:
            continue
        if check != "all":
            match = pattern.search(name)
            if not match or match.group(1).lower() != check:
                continue
        ticket_id = entry.get("id")
        if ticket_id:
            print(ticket_id)
    return 0


if __name__ == "__main__":
    sys.exit(main())
