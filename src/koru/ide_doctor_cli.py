"""CLI for ``koru ide doctor`` — IDE bridge diagnostics."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from koru.autopilot import default_socket_path
from koru.bounded_contexts.repairs import RepairCommandService, RepairQueryService
from koru.bounded_contexts.repairs.commands import (
    RecordRepairAttemptCommand,
    RecordRepairDiagnosticCommand,
)
from koru.bounded_contexts.repairs.queries import LoadRepairHistoryQuery
from koru.bounded_contexts.repairs.read_model import format_repair_history_for_llm
from koru.cqrs import runtime_for_project
from koru.ide_adapters import shared as adapter_shared
from koru.ide_adapters.bridge import (
    apply_bridge_fixes,
    evaluate_bridge,
    format_bridge_text,
    gc_stale_sockets_for_lane,
)
from koru.ide_adapters.registry import get_adapter, supported_adapter_ids
from koruide.ide import canonical_autopilot_ide_id, normalize_ide_id
from koruide.plugin_installer import resolve_target_ide


def _resolve_ide(raw: str) -> str | None:
    if raw == "auto":
        return resolve_target_ide("auto")
    return normalize_ide_id(raw)


def _instance_from_socket_path(socket_path: str, ide: str) -> str | None:
    """Infer lane slug from ``koru-autopilot-<lane>.sock`` setting values."""
    name = Path(socket_path).name
    prefix = "koru-autopilot-"
    suffix = ".sock"
    if not (name.startswith(prefix) and name.endswith(suffix)):
        return None
    lane = name[len(prefix) : -len(suffix)].strip()
    if not lane or canonical_autopilot_ide_id(lane) != ide:
        return None
    return lane


def _infer_instance_from_settings(project: Path | None, ide: str) -> str | None:
    """Best-effort lane inference from workspace/user socket settings."""
    if project is not None:
        ws_path = adapter_shared.workspace_settings_path(project, ide)
        ws_socket = adapter_shared.read_socket_from_settings(ws_path)
        if ws_socket:
            lane = _instance_from_socket_path(ws_socket, ide)
            if lane:
                return lane
    user_path = adapter_shared.user_settings_path(ide)
    user_socket = adapter_shared.read_socket_from_settings(user_path)
    if user_socket:
        return _instance_from_socket_path(user_socket, ide)
    return None


def _resolve_socket(args: argparse.Namespace, ide: str) -> Path:
    if args.socket:
        return Path(args.socket).expanduser().resolve()
    project_arg = getattr(args, "project", None)
    project = Path(project_arg).expanduser().resolve() if project_arg is not None else None
    env_instance = (os.environ.get("KORU_AUTOPILOT_INSTANCE") or "").strip()
    inferred_instance = _infer_instance_from_settings(project, ide)
    instance = (args.instance or env_instance or inferred_instance or ide or "").strip()
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


def _bridge_subject(ide: str, project: Path) -> str:
    return f"ide-bridge:{ide}:{project.resolve()}"


def _bridge_hypotheses_payload(status) -> list[dict[str, object]]:
    return [
        {
            "id": h.id,
            "confidence": h.confidence,
            "evidence": h.evidence,
            "remediation": h.remediation.summary,
            "remediation_kind": h.remediation.kind,
            "remediation_command": h.remediation.command,
        }
        for h in status.hypotheses
    ]


def _bridge_status_payload(status) -> dict[str, object]:
    return {
        "ide": status.ide,
        "socket": status.socket_path,
        "project": status.project,
        "daemon_running": status.daemon_running,
        "plugins_connected": status.plugins_connected,
        "plugins_compatible": status.plugins_compatible,
        "ready": status.ready,
        "fixes_applied": list(status.fixes_applied),
    }


def _record_bridge_repair_history(
    *,
    project: Path,
    status,
    fix_requested: bool,
) -> None:
    runtime = runtime_for_project(project)
    commands = RepairCommandService(runtime)
    subject = _bridge_subject(status.ide, project)
    hypotheses = _bridge_hypotheses_payload(status)
    primary = hypotheses[0]["id"] if hypotheses else "ready"
    commands.record_diagnostic(
        RecordRepairDiagnosticCommand(
            subject=subject,
            repair_kind="ide_bridge",
            project=str(project),
            summary=f"ide={status.ide} ready={status.ready} primary={primary}",
            status=_bridge_status_payload(status),
            hypotheses=hypotheses,
        )
    )
    if fix_requested or status.fixes_applied:
        actions = list(status.fixes_applied)
        if fix_requested and not actions:
            actions = ["safe autofix requested; no safe automatic changes were available"]
        commands.record_attempt(
            RecordRepairAttemptCommand(
                subject=subject,
                repair_kind="ide_bridge",
                project=str(project),
                attempted=bool(fix_requested or actions),
                ok=status.ready,
                actions=actions,
                summary=f"ide={status.ide} autofix ok={status.ready}",
            )
        )


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


def _add_history_parser(sub: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    history = sub.add_parser(
        "history",
        help="Print persisted repair history for LLM diagnostics.",
    )
    history.add_argument("--ide", default="auto", help="IDE lane or all.")
    history.add_argument("--project", type=Path, default=Path.cwd())
    history.add_argument("--limit", type=int, default=20)
    history.add_argument(
        "--format",
        dest="output_format",
        choices=("text", "json"),
        default="text",
    )


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
    _add_history_parser(sub)
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
    _record_bridge_repair_history(project=project, status=status, fix_requested=args.fix)
    if args.output_format == "json":
        payload = {
            "ide": status.ide,
            "socket": status.socket_path,
            "daemon_running": status.daemon_running,
            "plugins_connected": status.plugins_connected,
            "plugins_compatible": status.plugins_compatible,
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


def action_ide_history(args: argparse.Namespace) -> int:
    project = args.project.expanduser().resolve()
    ide = None if args.ide == "all" else _resolve_ide(args.ide)
    if args.ide != "all" and ide is None:
        print(
            "koru ide history: could not resolve IDE (pass --ide all|cursor|vscode|...)",
            file=sys.stderr,
        )
        return 2
    subject = None if ide is None else _bridge_subject(ide, project)
    runtime = runtime_for_project(project)
    history = RepairQueryService(runtime).history(
        LoadRepairHistoryQuery(subject=subject, limit=args.limit)
    )
    if args.output_format == "json":
        payload = [
            {
                "sequence": entry.sequence,
                "event_type": entry.event_type,
                "aggregate_id": entry.aggregate_id,
                "occurred_at": entry.occurred_at,
                "payload": entry.payload,
            }
            for entry in history
        ]
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(format_repair_history_for_llm(history))
    return 0


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
    if args.action == "history":
        return action_ide_history(args)
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
