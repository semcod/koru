"""``koru autopilot manage`` command implementation (R5b).

Extracted from :mod:`koru.autopilot.cli_command` to isolate install manager
logic into a cohesive module.
"""

from __future__ import annotations

import argparse
import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from koru.autopilot.install_manager import InstallManagerReport


def action_manage(
    args: argparse.Namespace,
    *,
    collect_report_fn: callable,
    format_report_fn: callable,
    repair_fn: callable,
) -> int:
    """Execute ``koru autopilot manage`` command.

    Collects install manager report or repairs installation based on args.

    Args:
        args: Parsed command-line arguments
        collect_report_fn: Function to collect install manager report
        format_report_fn: Function to format report for display
        repair_fn: Function to repair installation

    Returns:
        Exit code (0 success, 1 error)
    """
    report: InstallManagerReport = (
        repair_fn(ide=args.ide, socket_path=args.socket, dry_run=args.dry_run)
        if args.fix
        else collect_report_fn(ide=args.ide, socket_path=args.socket)
    )
    if args.output_format == "json":
        print(json.dumps(report.to_dict(), indent=2, sort_keys=True))
    else:
        print(format_report_fn(report))
    return 0 if report.ok else 1
