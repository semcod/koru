"""Argv normalization and auto-mode flag configuration for ``koru autonomous``.

Owns the CLI argv responsibilities extracted from the historical single-module
facade: maintenance-subcommand normalization, ``koru auto`` option expansion,
auto-pipeline/replace-existing flag application and ``--web`` token
consumption. The facade re-exports every public name so existing
``koru.autonomous`` imports (including ``_consume_web_flag``) keep working.
"""

from __future__ import annotations

from typing import Any

from koru.autonomous_auto_pipeline import (
    _collect_argv_options,
    _expand_auto_up_defaults,
)
from koru.autonomy.configuration import config_cli_config as _autonomous_cli_config


def _normalize_autonomous_argv(argv: list[str]) -> list[str]:
    """Normalize command line arguments for autonomous mode."""
    return _autonomous_cli_config.normalize_autonomous_argv(argv)


def _configure_auto_mode_args(
    argv: list[str],
    args: Any,
    invoked_as_auto: bool,
) -> tuple[set[str], list[str]]:
    """Configure arguments for auto mode and return user options and normalized argv."""
    return _autonomous_cli_config.configure_auto_mode_args(
        argv,
        invoked_as_auto,
        collect_argv_options=_collect_argv_options,
        expand_auto_up_defaults=_expand_auto_up_defaults,
    )


def _apply_auto_pipeline_flags(args: Any, invoked_as_auto: bool) -> None:
    """Apply auto-pipeline specific flags to args."""
    _autonomous_cli_config.apply_auto_pipeline_flags(args, invoked_as_auto)


def _apply_replace_existing_flags(args: Any, invoked_as_auto: bool) -> None:
    """Apply replace-existing flags for auto mode."""
    _autonomous_cli_config.apply_replace_existing_flags(args, invoked_as_auto)


def _consume_web_flag(argv: list[str]) -> tuple[list[str], bool]:
    """Strip ``--web``/``--no-web`` tokens before argparse.

    The flag lives outside ``operator_parser.py`` so concurrent tickets can
    extend the ``up`` parser without write conflicts.
    """
    web = False
    cleaned: list[str] = []
    for token in argv:
        if token == "--web":
            web = True
        elif token == "--no-web":
            web = False
        else:
            cleaned.append(token)
    return cleaned, web
