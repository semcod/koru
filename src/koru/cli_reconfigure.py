"""CLI entrypoint for 'koru reconfigure' command."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from koru.autonomy.dsl_reconfigure import DslReconfigurator, build_default_autonomy_registry


def register_reconfigure_subcommand(subparsers: argparse._SubParsersAction) -> None:
    """Register 'reconfigure' command in Koru CLI."""
    parser = subparsers.add_parser(
        "reconfigure",
        help="Reconfigure project autonomy settings using Process URI DSL",
    )
    parser.add_argument(
        "--spec",
        type=Path,
        required=False,
        help="Path to the DSL specification file (yaml: uri {json})",
    )
    parser.add_argument(
        "--export-gbnf",
        action="store_true",
        help="Export GBNF grammar for process URI generation to stdout",
    )
    parser.add_argument(
        "--list-actions",
        action="store_true",
        help="List available process actions and parameter schemas in the registry",
    )
    parser.set_defaults(func=run_reconfigure_cli)


def run_reconfigure_cli(args: argparse.Namespace) -> int:
    registry = build_default_autonomy_registry()
    reconfigurator = DslReconfigurator(registry)

    if getattr(args, "export_gbnf", False):
        sys.stdout.write(registry.export_gbnf())
        return 0

    if getattr(args, "list_actions", False):
        actions = registry.list_actions()
        for act in actions:
            sys.stdout.write(f"{act['uri']}: {act['description']}\n")
        return 0

    spec_path = getattr(args, "spec", None)
    if not spec_path:
        sys.stderr.write("Error: either --spec, --export-gbnf or --list-actions is required\n")
        return 1

    if not spec_path.is_file():
        sys.stderr.write(f"Error: spec file not found: {spec_path}\n")
        return 1

    content = spec_path.read_text(encoding="utf-8")
    result = reconfigurator.apply_to_project(Path.cwd(), content)
    sys.stdout.write(f"Reconfiguration applied: {result['operations_count']} operations.\n")
    return 0
