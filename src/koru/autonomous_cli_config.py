"""CLI argument normalization helpers for ``koru autonomous``."""

from __future__ import annotations

import os
from typing import Any


def normalize_autonomous_argv(argv: list[str]) -> list[str]:
    """Normalize command line arguments for autonomous mode."""
    if not argv:
        return ["up"]
    if argv[0] == "safe-up":
        return [
            "up",
            "--ticket-sources",
            "queue",
            "--idle-diagnostics",
            "quick",
            "--diagnostic-tickets",
            "--autopilot-action",
            "off",
            "--no-autopilot",
            "--max-cycles",
            "1",
            "--no-semcod-artifacts",
            *argv[1:],
        ]
    if argv[0] != "up" and argv[0] not in ("-h", "--help"):
        return ["up", *argv]
    return argv


def configure_auto_mode_args(
    argv: list[str],
    invoked_as_auto: bool,
    *,
    collect_argv_options: Any,
    expand_auto_up_defaults: Any,
) -> tuple[set[str], list[str]]:
    """Configure arguments for auto mode and return user options and normalized argv."""
    auto_user_options: set[str] = set()
    if invoked_as_auto and argv and argv[0] == "up":
        auto_user_options = collect_argv_options(argv[1:])
        argv = expand_auto_up_defaults(argv)
    return auto_user_options, argv


def apply_auto_pipeline_flags(args: Any, invoked_as_auto: bool) -> None:
    """Apply auto-pipeline specific flags to args."""
    args._auto_pipeline_enabled = (
        invoked_as_auto
        and args.action == "up"
        and os.environ.get("KORU_AUTO_PIPELINE", "").strip().lower()
        in {"1", "true", "yes", "on"}
    )


def apply_replace_existing_flags(args: Any, invoked_as_auto: bool) -> None:
    """Apply replace-existing flags for auto mode."""
    if invoked_as_auto:
        args.replace_existing_global = True
        if not args.allow_duplicate and not args.replace_existing:
            args.replace_existing = True
    elif not hasattr(args, "replace_existing_global"):
        args.replace_existing_global = False


__all__ = [
    "normalize_autonomous_argv",
    "configure_auto_mode_args",
    "apply_auto_pipeline_flags",
    "apply_replace_existing_flags",
]
