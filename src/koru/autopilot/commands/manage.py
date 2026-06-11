"""``koru autopilot manage`` command implementation (R5b).

Extracted from :mod:`koru.autopilot.cli_command` to isolate install manager
logic into a cohesive module.
"""

from __future__ import annotations

import argparse
import json
from typing import TYPE_CHECKING

from koru.autopilot.log_contract import emit_log

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
    emit_log(
        args,
        component="autopilot.manage",
        level="info",
        action="request",
        result="started",
        ide=str(args.ide),
        fix=bool(args.fix),
        dry_run=bool(args.dry_run),
    )
    project = getattr(args, "project", None)
    if args.fix:
        kwargs = dict(ide=args.ide, socket_path=args.socket, dry_run=args.dry_run)
        if project is not None:
            kwargs["project"] = project
        report = repair_fn(**kwargs)
    else:
        kwargs = dict(ide=args.ide, socket_path=args.socket)
        if project is not None:
            kwargs["project"] = project
        report = collect_report_fn(**kwargs)
    if args.output_format == "json":
        print(json.dumps(report.to_dict(), indent=2, sort_keys=True))
    else:
        print(format_report_fn(report))
    rc = 0 if report.ok else 1
    if rc != 0 and getattr(args, "allow_unconnected", False):
        ignored_codes = {
            "plugin_not_connected",
            "plugin_build_mismatch",
            "plugin_version_mismatch",
            "plugin_socket_candidate_mismatch",
            "plugin_live_host_stale",
        }
        if not any(issue.severity == "error" and issue.code not in ignored_codes for issue in report.issues):
            rc = 0

    emit_log(
        args,
        component="autopilot.manage",
        level="info" if rc == 0 else "error",
        action="request",
        result="ok" if rc == 0 else "failed",
        rc=rc,
    )
    return rc
