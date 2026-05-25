"""``koru autopilot shutdown`` command implementation (R5b).

Extracted from :mod:`koru.autopilot.cli_command` to isolate shutdown logic
into a cohesive module.
"""

from __future__ import annotations

import argparse
from typing import TYPE_CHECKING

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
    return daemon_shutdown_fn(args, client_fn=client_fn)
