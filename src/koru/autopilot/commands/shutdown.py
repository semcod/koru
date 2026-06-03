"""``koru autopilot shutdown`` command implementation (R5b).

Extracted from :mod:`koru.autopilot.cli_command` to isolate shutdown logic
into a cohesive module.
"""

from __future__ import annotations

import argparse
from typing import TYPE_CHECKING

from koru.autopilot.log_contract import emit_log

if TYPE_CHECKING:
    from koru.autopilot.client import AutopilotClient


def action_shutdown(
    args: argparse.Namespace,
    *,
    client_fn: callable,
    daemon_shutdown_fn: callable,
) -> int:
    """Execute ``koru autopilot shutdown`` command.

    Args:
        args: Parsed command-line arguments
        client_fn: Factory for AutopilotClient
        daemon_shutdown_fn: Backend shutdown implementation from daemon_cli

    Returns:
        Exit code (0 success, 1 error)
    """
    emit_log(
        args,
        component="autopilot.shutdown",
        level="info",
        action="request",
        result="started",
    )
    rc = daemon_shutdown_fn(args, client_fn=client_fn)
    emit_log(
        args,
        component="autopilot.shutdown",
        level="info" if rc == 0 else "error",
        action="request",
        result="ok" if rc == 0 else "failed",
        rc=rc,
    )
    return rc
