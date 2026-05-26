"""CLI for ``koru ide doctor`` — IDE bridge diagnostics."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from koru.autopilot import default_socket_path
from koru.ide_adapters.bridge import (
    apply_bridge_fixes,
    evaluate_bridge,
    format_bridge_text,
    gc_stale_sockets_for_lane,
)
from koru.ide_adapters.registry import get_adapter, supported_adapter_ids
from koruide.ide import normalize_ide_id
from koruide.plugin_installer import resolve_target_ide


def _resolve_ide(raw: str) -> str | None:
    if raw == "auto":
        return resolve_target_ide("auto")
    return normalize_ide_id(raw)


def _resolve_socket(args: argparse.Namespace, ide: str) -> Path:
    if args.socket:
        return Path(args.socket).expanduser().resolve()
    instance = (args.instance or ide or "").strip()
    if not instance:
        return default_socket_path()
    previous = os.environ.get("KORU_AUTOPILOT_INSTANCE")
    os.environ["KORU_AUTOPILOT_INSTANCE"] = instance
    try:
        return default_socket_path()
    finally:
        if previous is None:
            os.environ.pop("KORU_AUTOPILOT_INSTANCE", None)
        else:
            os.environ["KORU_AUTOPILOT_INSTANCE"] = previous


def _add_discover_parser(sub: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    discover = sub.add_parser(
        "discover",
        help="Run code2llm broad discovery and apply planfile tickets (idle queue helper).",
    )
    discover.add_argument("--project", type=Path, default=Path.cwd())
    discover.add_argument("--output-subdir", default="project")
    discover.add_argument("--formats", default="all")
    discover.add_argument("--exclude", action="append", default=None, metavar="PATTERN")
    discover.add_argument("--no-apply", dest="apply_planfile", action="store_false", default=True)
    discover.add_argument("--source", default="koru-project-discovery")
    discover.add_argument("--sprint", default="current")
    discover.add_argument("--limit", type=int, default=20)
    discover.add_argument("--stale-minutes", type=float, default=60.0)
    discover.add_argument("--force", action="store_true")
    discover.add_argument(
        "--format",
        dest="output_format",
        choices=("text", "json"),
        default="text",
    )


def _add_doctor_parser(sub: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    doctor = sub.add_parser(
        "doctor",
        help="Diagnose autopilot daemon + IDE plugin bridge for one IDE lane.",
    )
    doctor.add_argument(
        "--ide",
        default="auto",
        help=f"IDE lane (default: auto). Supported: {', '.join(supported_adapter_ids())}",
    )
    doctor.add_argument(
        "--project",
        type=Path,
        default=Path.cwd(),
        help="Project root for workspace settings checks.",
    )
    doctor.add_argument("--socket", type=Path, default=None, help="Autopilot socket override.")
    doctor.add_argument(
        "--instance",
        default=None,
        help="Set KORU_AUTOPILOT_INSTANCE for this run (e.g. cursor).",
    )
    doctor.add_argument(
        "--fix",
        action="store_true",
        help="Apply safe auto-fixes (workspace socket, trusted publisher when IDE closed).",
    )
    doctor.add_argument(
        "--gc-sockets",
        action="store_true",
        help="Remove stale koru-autopilot-*.sock files before checks.",
    )
    doctor.add_argument(
        "--format",
        dest="output_format",
        choices=("text", "json"),
        default="text",
    )
    doctor.add_argument("--explain", action="store_true", help="Always print hypothesis details.")


def _add_reload_parser(sub: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    reload = sub.add_parser(
        "reload",
        help="Reload IDE window so a newly installed VSIX extension can activate.",
    )
    reload.add_argument("--ide", default="cursor", help="IDE lane (cursor, vscode, vscodium, …).")
    reload.add_argument("--project", type=Path, default=Path.cwd())
    reload.add_argument("--dry-run", action="store_true")
    reload.add_argument(
        "--format",
        dest="output_format",
        choices=("text", "json"),
        default="text",
    )


def _add_command_catalog_parser(sub: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    commands = sub.add_parser(
        "commands",
        help="Print the IDE command/action catalog used by autonomy strategy planning.",
    )
    commands.add_argument("--ide", default="all", help="IDE id or all.")
    commands.add_argument(
        "--format",
        dest="output_format",
        choices=("text", "json", "yaml"),
        default="text",
    )
    commands.add_argument(
        "--for-llm",
        action="store_true",
        help="Print the compact strategy-planning view instead of the full catalog.",
    )


def _add_scenario_parsers(sub: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    scenario_schema = sub.add_parser(
        "scenario-schema",
        help="Print the JSON Schema for LLM-authored IDE command scenarios.",
    )
    scenario_schema.add_argument(
        "--format",
        dest="output_format",
        choices=("json", "yaml"),
        default="json",
    )
    scenario_prompt = sub.add_parser(
        "scenario-prompt",
        help="Print a prompt that asks an LLM to write an IDE command scenario.",
    )
    scenario_prompt.add_argument("--ide", default="all", help="IDE id or all.")
    scenario_validate = sub.add_parser(
        "scenario-validate",
        help="Validate an IDE command scenario JSON/YAML file or stdin.",
    )
    scenario_validate.add_argument("scenario", nargs="?", default="-")
    scenario_validate.add_argument(
        "--format",
        dest="output_format",
        choices=("text", "json", "yaml"),
        default="text",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="koru ide")
    sub = parser.add_subparsers(dest="action", required=True)
    _add_discover_parser(sub)
    _add_doctor_parser(sub)
    _add_reload_parser(sub)
    _add_command_catalog_parser(sub)
    _add_scenario_parsers(sub)
    return parser


def action_ide_doctor(args: argparse.Namespace) -> int:
    ide = _resolve_ide(args.ide)
    if ide is None:
        print(
            "koru ide doctor: could not resolve IDE (pass --ide cursor|vscode|...)",
            file=sys.stderr,
        )
        return 2
    if get_adapter(ide) is None:
        print(f"koru ide doctor: no adapter for ide={ide}", file=sys.stderr)
        return 2
    project = args.project.expanduser().resolve()
    socket_path = _resolve_socket(args, ide)
    removed: list[str] = []
    if args.gc_sockets:
        removed = gc_stale_sockets_for_lane(socket_path)
    status = evaluate_bridge(ide=ide, socket_path=socket_path, project=project)
    status = apply_bridge_fixes(status, project=project, fix=args.fix)
    if removed:
        status.fixes_applied = [
            *status.fixes_applied,
            *[f"removed stale socket {p}" for p in removed],
        ]
    if args.output_format == "json":
        payload = {
            "ide": status.ide,
            "socket": status.socket_path,
            "daemon_running": status.daemon_running,
            "plugins_connected": status.plugins_connected,
            "ready": status.ready,
            "project": status.project,
            "fixes_applied": status.fixes_applied,
            "hypotheses": [
                {
                    "id": h.id,
                    "confidence": h.confidence,
                    "evidence": h.evidence,
                    "remediation": {
                        "kind": h.remediation.kind,
                        "summary": h.remediation.summary,
                        "command": h.remediation.command,
                    },
                }
                for h in status.hypotheses
            ],
        }
        if status.settings is not None:
            payload["settings"] = {
                "expected_socket": status.settings.expected_socket,
                "user_socket": status.settings.user_socket,
                "workspace_socket": status.settings.workspace_socket,
                "mismatch": status.settings.mismatch,
            }
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0 if status.ready else 1
    print(format_bridge_text(status, explain=args.explain))
    return 0 if status.ready else 1


def action_ide_reload(args: argparse.Namespace) -> int:
    from koru.ide_adapters.ide_reload import try_reload_vscode_family_ide

    ide = _resolve_ide(args.ide) or args.ide
    outcome = try_reload_vscode_family_ide(
        ide,
        project=args.project.expanduser().resolve(),
        dry_run=args.dry_run,
    )
    payload = {
        "ide": ide,
        "attempted": outcome.attempted,
        "ok": outcome.ok,
        "method": outcome.method,
        "detail": outcome.detail,
    }
    if args.output_format == "json":
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        if outcome.ok:
            print(f"koru ide reload: ok ({outcome.method})")
        elif outcome.attempted:
            print(f"koru ide reload: failed ({outcome.method}): {outcome.detail}", file=sys.stderr)
        else:
            print(f"koru ide reload: skipped: {outcome.detail}", file=sys.stderr)
    return 0 if outcome.ok else 1


def action_ide_discover(args: argparse.Namespace) -> int:
    from koru.autonomy.code2llm_discovery import (
        DEFAULT_EXCLUDES,
        format_discovery_summary,
        run_code2llm_discovery,
    )

    excludes = tuple(args.exclude) if args.exclude else DEFAULT_EXCLUDES
    outcome = run_code2llm_discovery(
        args.project.expanduser().resolve(),
        output_subdir=args.output_subdir,
        formats=args.formats,
        excludes=excludes,
        apply_planfile=args.apply_planfile,
        planfile_source=args.source,
        planfile_sprint=args.sprint,
        planfile_limit=args.limit,
        stale_minutes=args.stale_minutes,
        force=args.force,
    )
    if args.output_format == "json":
        print(json.dumps(outcome.to_dict(), indent=2, sort_keys=True))
    else:
        print(format_discovery_summary(outcome))
        if outcome.applied_titles:
            print("applied tickets:")
            for title in outcome.applied_titles:
                print(f"  · {title}")
        if outcome.error:
            return 1
    if outcome.error:
        return 1
    if not outcome.ran and not outcome.applied_titles:
        return 2  # nothing happened — caller should know
    return 0


def action_ide_commands(args: argparse.Namespace) -> int:
    import yaml

    from koruide.command_catalog import (
        build_ide_command_catalog,
        command_catalog_for_llm,
        format_command_catalog_text,
    )

    ide = None if args.ide == "all" else args.ide
    try:
        payload = command_catalog_for_llm(ide) if args.for_llm else build_ide_command_catalog(ide)
    except ValueError as exc:
        print(f"koru ide commands: {exc}", file=sys.stderr)
        return 2
    if args.output_format == "json":
        print(json.dumps(payload, indent=2, sort_keys=True))
    elif args.output_format == "yaml":
        print(yaml.safe_dump(payload, sort_keys=False, allow_unicode=True))
    else:
        print(format_command_catalog_text(ide, for_llm=args.for_llm))
    return 0


def action_ide_scenario_schema(args: argparse.Namespace) -> int:
    import yaml

    from koruide.command_scenario import ide_command_scenario_schema

    payload = ide_command_scenario_schema()
    if args.output_format == "yaml":
        print(yaml.safe_dump(payload, sort_keys=False, allow_unicode=True))
    else:
        print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def action_ide_scenario_prompt(args: argparse.Namespace) -> int:
    from koruide.command_scenario import llm_scenario_prompt

    ide = None if args.ide == "all" else args.ide
    try:
        print(llm_scenario_prompt(ide))
    except ValueError as exc:
        print(f"koru ide scenario-prompt: {exc}", file=sys.stderr)
        return 2
    return 0


def action_ide_scenario_validate(args: argparse.Namespace) -> int:
    import yaml

    from koruide.command_scenario import validate_ide_command_scenario

    raw_text = sys.stdin.read() if args.scenario == "-" else Path(args.scenario).read_text()
    try:
        raw = yaml.safe_load(raw_text)
    except yaml.YAMLError as exc:
        print(f"koru ide scenario-validate: invalid YAML/JSON: {exc}", file=sys.stderr)
        return 2
    result = validate_ide_command_scenario(raw)
    payload = result.to_dict()
    if args.output_format == "json":
        print(json.dumps(payload, indent=2, sort_keys=True))
    elif args.output_format == "yaml":
        print(yaml.safe_dump(payload, sort_keys=False, allow_unicode=True))
    else:
        status = "ok" if result.ok else "invalid"
        print(f"scenario {status}")
        for warning in result.warnings:
            print(f"warning: {warning}")
        for error in result.errors:
            print(f"error: {error}")
    return 0 if result.ok else 1


def ide_main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.action == "doctor":
        return action_ide_doctor(args)
    if args.action == "discover":
        return action_ide_discover(args)
    if args.action == "reload":
        return action_ide_reload(args)
    if args.action == "commands":
        return action_ide_commands(args)
    if args.action == "scenario-schema":
        return action_ide_scenario_schema(args)
    if args.action == "scenario-prompt":
        return action_ide_scenario_prompt(args)
    if args.action == "scenario-validate":
        return action_ide_scenario_validate(args)
    parser.error(f"unknown action: {args.action}")
    return 2
