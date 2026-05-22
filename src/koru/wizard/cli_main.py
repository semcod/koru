"""CLI entrypoint for ``koru wizard``.

Handles argument parsing and delegates to the wizard orchestrator.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path

from koru.wizard.ide import discover_installed_ides
from koru.wizard.llx import llx_available
from koru.wizard.orchestrator import WizardResult, emit_human, run_wizard
from koru.wizard.prompters import StdinPrompter
from koru.wizard.templates import format_templates_list, resolve_strategies_source


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="koru wizard",
        description=(
            "Interactive bootstrap: detect IDE, pick project, choose strategy, "
            "create first ticket."
        ),
    )
    p.add_argument(
        "--strategies",
        default=None,
        metavar="PATH|URL",
        help=(
            "Custom strategies.json (local path or https:// URL; "
            "HTTPS requires --allow-remote)"
        ),
    )
    p.add_argument(
        "--template",
        default=None,
        metavar="NAME",
        help=(
            "Built-in strategy template (default, web-app, ml-research, "
            "cli-tool, library). Mutually exclusive with --strategies."
        ),
    )
    p.add_argument(
        "--list-templates",
        action="store_true",
        help="List built-in strategy templates and exit.",
    )
    p.add_argument(
        "--allow-remote",
        action="store_true",
        help="Allow fetching --strategies from HTTPS URLs (cached locally).",
    )
    p.add_argument(
        "--language",
        default=None,
        help=(
            "UI language (single 'pl' / 'en', or comma-separated 'pl,en' for "
            "bilingual labels). Defaults to strategies.json setting."
        ),
    )
    p.add_argument(
        "--bilingual",
        action="store_true",
        help="Shortcut for --language pl,en (side-by-side bilingual labels).",
    )
    p.add_argument(
        "--quick",
        action="store_true",
        help="Skip every prompt; follow strategies.json quick_default.path.",
    )
    p.add_argument(
        "--strategy",
        default=None,
        help=(
            "Dot-separated option-id path to follow in --quick mode "
            "(e.g. 'quality.cc_refactor'). Implies --quick."
        ),
    )
    p.add_argument(
        "--project",
        type=Path,
        default=None,
        help="Skip project picker, use this path",
    )
    p.add_argument(
        "--no-create",
        action="store_true",
        help="Walk the tree but don't write a ticket",
    )
    p.add_argument(
        "--llx",
        action="store_true",
        help="Ask llx to extend tree branches dynamically",
    )
    p.add_argument(
        "--detect-only",
        action="store_true",
        help="Print IDE / project candidates and exit (no prompts)",
    )
    p.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="--detect-only output format",
    )
    p.add_argument(
        "--gui",
        action="store_true",
        help="Open browser UI on http://127.0.0.1:<port>/wizard (requires koru[api]).",
    )
    p.add_argument(
        "--gui-port",
        type=int,
        default=0,
        metavar="PORT",
        help="Port for --gui (0 = pick a free port). Binds 127.0.0.1 only.",
    )
    p.add_argument(
        "--no-browser",
        action="store_true",
        help="With --gui, print URL but do not open a browser tab.",
    )
    return p


def _resolve_language(language: str | None, bilingual: bool) -> str | None:
    """Resolve the language setting from CLI arguments."""
    if bilingual and not language:
        return "pl,en"
    if bilingual and language and "," not in language:
        return f"{language},pl,en" if language not in {"pl", "en"} else "pl,en"
    return language


def _handle_detect_only(format_type: str) -> int:
    """Handle --detect-only mode."""
    ides = discover_installed_ides()
    from koru.wizard.project import propose_projects

    candidates = propose_projects(ides)
    if format_type == "json":
        payload = {
            "ides": [ide.to_dict() for ide in ides],
            "projects": [{"path": str(c.path), "source": c.source} for c in candidates],
            "llx_available": llx_available(),
        }
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        from koru.wizard.ide import summarize_ides

        print("Detected IDEs:")
        print(summarize_ides(ides))
        print("")
        print("Project candidates:")
        if candidates:
            for cand in candidates:
                print(f"  - {cand.label()}")
        else:
            print("  (none)")
        print("")
        print(f"llx CLI on PATH: {'yes' if llx_available() else 'no'}")
    return 0


def _run_gui_mode(
    strategies_path: Path,
    language: str | None,
    project_override: Path | None,
    create: bool,
    port: int,
    open_browser: bool,
) -> int:
    """Run the wizard in GUI mode."""
    from koru.wizard.gui import run_gui_server

    try:
        return run_gui_server(
            strategies_path=strategies_path,
            language=language,
            project_override=project_override,
            create=create,
            port=port,
            open_browser=open_browser,
        )
    except RuntimeError as exc:
        print(f"koru wizard error: {exc}", file=sys.stderr)
        return 2


def _run_cli_mode(
    strategies_path: Path,
    language: str | None,
    project_override: Path | None,
    create: bool,
    use_llx: bool,
    quick: bool,
    quick_strategy: str | None,
) -> int:
    """Run the wizard in CLI mode."""
    prompter = StdinPrompter()
    try:
        result: WizardResult = run_wizard(
            prompter=prompter,
            strategies_path=strategies_path,
            language=language,
            project_override=project_override,
            create=create,
            use_llx=use_llx,
            quick=quick,
            quick_strategy=quick_strategy,
        )
    except (EOFError, KeyboardInterrupt):
        print("\n(cancelled)", file=sys.stderr)
        return 130
    except (KeyError, ValueError) as exc:
        print(f"koru wizard error: {exc}", file=sys.stderr)
        return 2

    emit_human(sys.stdout, result, result.ticket_id)
    return 0


def wizard_main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)

    if args.template and args.strategies:
        parser.error("--template and --strategies are mutually exclusive")

    if args.list_templates:
        print(format_templates_list())
        return 0

    if args.gui and (args.quick or args.strategy):
        parser.error("--gui cannot be combined with --quick or --strategy")

    if args.detect_only:
        return _handle_detect_only(args.format)

    if args.llx and not llx_available():
        print(
            "note: --llx requested but `llx` CLI not on PATH; falling back to static tree",
            file=sys.stderr,
        )

    language = _resolve_language(args.language, args.bilingual)

    try:
        strategies_path = resolve_strategies_source(
            strategies=args.strategies,
            template=args.template,
            allow_remote=args.allow_remote,
        )
    except (FileNotFoundError, KeyError, ValueError, RuntimeError) as exc:
        print(f"koru wizard error: {exc}", file=sys.stderr)
        return 2

    if args.gui:
        return _run_gui_mode(
            strategies_path=strategies_path,
            language=language,
            project_override=args.project,
            create=not args.no_create,
            port=args.gui_port,
            open_browser=not args.no_browser,
        )

    quick = args.quick or bool(args.strategy)
    return _run_cli_mode(
        strategies_path=strategies_path,
        language=language,
        project_override=args.project,
        create=not args.no_create,
        use_llx=args.llx,
        quick=quick,
        quick_strategy=args.strategy,
    )
