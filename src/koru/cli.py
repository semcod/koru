"""Command-line entrypoint for koru."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import shlex
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

from .agents import (
    detect_agent_options,
)
from .autonomous import autonomous_main, stop_prior_autonomous_for_auto_start
from .autopilot.cli_command import autopilot_main
from .bootstrap import import_flat_pipeline
from .context import build_context, render_markdown_handoff
from .doctor import render_text as render_doctor_text
from .doctor import run_diagnostics
from .events import emit_management_event
from .gate import VALID_MODES as GATE_VALID_MODES
from .gate import authorize_gate
from .gc import DEFAULT_KEEP_LAST, DEFAULT_MAX_AGE_DAYS, GC_STATUSES, run_gc
from .init import init_project, refresh_init_agent_lane
from .loop import discover_repositories, run_closed_loop
from .queue import (
    default_human_prompt as _queue_default_human_prompt,
)
from .queue import (
    run_api_request as _queue_run_api_request,
)
from .queue import (
    run_llm_request as _queue_run_llm_request,
)
from .queue import (
    run_process as _queue_run_process,
)
from .queue import (
    run_shell_command as _queue_run_shell_command,
)
from .queue_clean import CleanupReport, clean_queue
from .scan import ScanResult, run_scan
from .serve import DEFAULT_HOST, DEFAULT_PORT
from .tasks import create_nl_task
from .tools import (
    build_tool_task_scaffold,
    detect_tools,
    find_tool_entry,
    load_tool_registry,
    render_tools_detect_text,
)
from .watch import watch_planfile_events


def _env_truthy(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in ("1", "true", "yes", "on")


def _command_value(value: str) -> str:
    stripped = value.strip()
    if not stripped:
        raise argparse.ArgumentTypeError("Command cannot be empty")
    return stripped


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run closed-loop automation on semcod repositories.",
    )
    parser.add_argument("--workspace", type=Path, default=Path.cwd(), help="Workspace root.")
    parser.add_argument(
        "--include",
        default="semcod/*",
        help="Glob (relative to workspace) selecting repositories.",
    )
    parser.add_argument(
        "--max-rounds",
        type=int,
        default=3,
        help="Maximum retries for repositories that fail.",
    )
    parser.add_argument(
        "--command",
        type=_command_value,
        help="Command to execute in each repository, e.g. 'python -m pytest -q'.",
    )
    parser.add_argument(
        "--queue",
        action="store_true",
        help="Run one task from the local planfile queue instead of repository loop mode.",
    )
    parser.add_argument(
        "--project",
        type=Path,
        default=Path.cwd(),
        help="Project root for --queue mode.",
    )
    parser.add_argument(
        "--actor",
        default="koru-shell",
        help="Actor name used when claiming planfile queue tickets.",
    )
    parser.add_argument(
        "--queue-name",
        default=None,
        help="Only execute tickets from this planfile execution queue.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview the selected planfile queue task without executing it.",
    )
    parser.add_argument(
        "--interactive",
        action="store_true",
        help=(
            "When the next ticket is a 'human' executor, prompt for the answer "
            "on stdin (multi-line, Ctrl-D submits, Ctrl-C cancels). On submit, "
            "the ticket is claimed/started/completed with the answer recorded "
            "in --note and --result-json."
        ),
    )
    parser.add_argument(
        "--loop",
        action="store_true",
        help=(
            "Drain the planfile queue: keep fetching and running the next "
            "ticket until the queue is idle, a ticket needs human input we "
            "cannot satisfy, or --max-iterations is reached. Combine with "
            "--interactive to also handle human tickets in the same run."
        ),
    )
    parser.add_argument(
        "--max-iterations",
        type=int,
        default=100,
        help="Safety cap on the number of tickets --loop will process (default 100).",
    )
    parser.add_argument(
        "--watch",
        action="store_true",
        help="Watch planfile WebSocket events.",
    )
    parser.add_argument(
        "--ws-url",
        default="ws://localhost:8000/ws",
        help="Planfile WebSocket URL for --watch mode.",
    )
    parser.add_argument(
        "--max-events",
        type=int,
        default=None,
        help="Stop --watch after this many events, useful for smoke tests.",
    )
    parser.add_argument(
        "--skip-host-environment",
        action="store_true",
        help=(
            "With --init or --init-agent-lane: skip writing .planfile/.koru/"
            "host-environment.{json,md} (desktop + injector probe). "
            "Use in CI or minimal sandboxes."
        ),
    )
    parser.add_argument(
        "--bootstrap",
        action="store_true",
        help="Import a flat-format pipeline YAML into .planfile/ for queue-mode execution.",
    )
    parser.add_argument(
        "--from",
        dest="from_file",
        type=Path,
        default=None,
        help="Source flat-pipeline YAML for --bootstrap (e.g. examples/bootstrap.planfile.yaml).",
    )
    parser.add_argument(
        "--sprint",
        default="current",
        help="Target sprint name when --bootstrap writes .planfile/sprints/<sprint>.yaml.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite an existing sprint file during --bootstrap.",
    )
    parser.add_argument(
        "--agent-lane",
        default="auto",
        metavar="LANE",
        help=(
            "With --init or --init-agent-lane: write .planfile/.koru/"
            "shell-env.sh and run-autonomous.sh for that lane. "
            "Use auto (default) to pick cursor or windsurf from project "
            "dotdirs, else local; use none/off to skip or remove helpers."
        ),
    )
    parser.add_argument(
        "--init",
        action="store_true",
        help=(
            "Initialise a koru-managed project in --project: import a "
            "flat pipeline (or generate a 2-ticket starter scaffold), "
            "write .planfile/.koru/policy.yaml stub, add "
            ".planfile/.koru/ to .gitignore, and (unless --agent-lane none) "
            "emit shell-env.sh + run-autonomous.sh, and write a host-environment "
            "snapshot (host-environment.json + .md) for autopilot setup. Pass "
            "--from <yaml> to "
            "import an existing pipeline; --force to re-init."
        ),
    )
    parser.add_argument(
        "--init-agent-lane",
        action="store_true",
        dest="init_agent_lane",
        help=(
            "On a project that already has .planfile/config.yaml, only "
            "write or remove shell-env.sh and run-autonomous.sh per "
            "--agent-lane. Does not touch sprint, policy, or pipelines. "
            "Use when `koru --init` refuses without --force."
        ),
    )
    parser.add_argument(
        "--doctor",
        action="store_true",
        help=(
            "Run diagnostic checks against --project (planfile config, "
            "sprints, policy.yaml, .gitignore, planfile binary, CI "
            "command). Exits 1 if any check fails; warnings alone "
            "exit 0. Use --format json for machine-readable output."
        ),
    )
    parser.add_argument(
        "--fix",
        action="store_true",
        help=(
            "With --doctor, include guided auto-repair commands. The top-level "
            "doctor still does not mutate the project by itself."
        ),
    )
    parser.add_argument(
        "--context",
        action="store_true",
        help=(
            "Emit a self-service brief (ticket + policy + constraints + "
            "command vocabulary) for an LLM agent. The brief is the only "
            "thing an autonomous agent should need to act safely."
        ),
    )
    parser.add_argument(
        "--ticket",
        default=None,
        help="Target a specific ticket id (e.g. PLF-074) for --context. "
        "Default is the next runnable ticket from the queue.",
    )
    parser.add_argument(
        "--format",
        dest="output_format",
        choices=["json", "markdown", "text"],
        default="json",
        help="Output format for --context (default: json).",
    )
    parser.add_argument(
        "--include-fixtures",
        dest="include_fixtures",
        action="store_true",
        default=None,
        help=(
            "Include test/dryrun fixture tickets (labels test-only, "
            "dryrun, synthetic, auto-close) in --context. Default is "
            "to skip them so the agent isn't pointed at planfile/koru "
            "self-test artifacts. Also controlled via the "
            "KORU_INCLUDE_FIXTURES env var."
        ),
    )
    parser.add_argument(
        "--no-include-fixtures",
        dest="include_fixtures",
        action="store_false",
        help="Explicitly hide fixtures (overrides KORU_INCLUDE_FIXTURES env).",
    )
    parser.add_argument(
        "--no-log",
        action="store_true",
        help="Disable the per-run JSONL log under .planfile/.koru/runs/. "
        "Has no effect outside --queue mode.",
    )
    return parser


def _build_tools_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="koru tools",
        description="Inspect AI tool registry/detection status.",
    )
    sub = parser.add_subparsers(dest="subcommand", required=True)
    detect = sub.add_parser("detect", help="Detect tools from the 2026 registry.")
    detect.add_argument("--project", type=Path, default=Path.cwd(), help="Project root.")
    detect.add_argument(
        "--registry",
        type=Path,
        default=None,
        help="Override registry YAML path (default: docs/ai-tool-registry-2026.yaml).",
    )
    detect.add_argument(
        "--format",
        dest="output_format",
        choices=("text", "json"),
        default="text",
        help="Output format (default: text).",
    )
    return parser


def _tools_main(argv: list[str]) -> int:
    args = _build_tools_parser().parse_args(argv)
    if args.subcommand != "detect":
        print(f"koru tools: unknown subcommand {args.subcommand!r}", file=sys.stderr)
        return 2

    registry, registry_path = load_tool_registry(args.registry)
    results = detect_tools(args.project.resolve(), registry)

    if args.output_format == "json":
        payload = {
            "project": str(args.project),
            "registry": str(registry_path) if registry_path else None,
            "tools": results,
        }
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(render_tools_detect_text(results, registry_path=registry_path))

    emit_management_event(
        tool="koru.tools.detect",
        action="completed",
        status="completed",
        message=f"tools={len(results)}",
        details={
            "project": str(args.project),
            "registry": str(registry_path) if registry_path else None,
            "available": sum(1 for r in results if r.get("available")),
        },
    )
    return 0


def _build_task_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="koru task",
        description="Create a planfile ticket from a natural-language sentence.",
    )
    parser.add_argument("text", nargs="+", help="Natural-language task description.")
    parser.add_argument("--project", type=Path, default=Path.cwd(), help="Project root.")
    parser.add_argument("--sprint", default="current", help="Target planfile sprint.")
    parser.add_argument("--queue-name", default=None, help="Execution queue for the new ticket.")
    parser.add_argument("--priority", default="normal", help="Ticket priority.")
    parser.add_argument(
        "--tool",
        dest="tool_id",
        default=None,
        help=(
            "Build a tool-adapter scaffold ticket for this tool id "
            "(from docs/ai-tool-registry-2026.yaml)."
        ),
    )
    parser.add_argument(
        "--tool-kind",
        dest="tool_kind",
        choices=("human", "shell", "api", "llm"),
        default=None,
        help="Override scaffolded executor hint for --tool.",
    )
    parser.add_argument(
        "--tool-registry",
        dest="tool_registry",
        type=Path,
        default=None,
        help="Override tool registry path for --tool lookup.",
    )
    return parser


def _build_serve_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="koru serve",
        description=(
            "Run a local dashboard for koru (live LLM brief, ticket, "
            "policy, agent lanes). Binds to 127.0.0.1 by default."
        ),
    )
    parser.add_argument("--project", type=Path, default=Path.cwd(), help="Project root.")
    parser.add_argument(
        "--queue-name",
        default=None,
        help="Queue used when selecting the active ticket.",
    )
    parser.add_argument(
        "--host",
        default=DEFAULT_HOST,
        help=f"Bind address (default {DEFAULT_HOST}).",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=DEFAULT_PORT,
        help=f"TCP port to listen on (default {DEFAULT_PORT}).",
    )
    parser.add_argument(
        "--auto-port",
        action="store_true",
        help=(
            "If the port is busy, try the next ports (then an ephemeral port). "
            "Also on when KORU_SERVE_AUTO_PORT is 1/true/yes."
        ),
    )
    open_group = parser.add_mutually_exclusive_group()
    open_group.add_argument(
        "--open",
        dest="open_browser",
        action="store_true",
        default=True,
        help="Open the dashboard URL in the default browser (default).",
    )
    open_group.add_argument(
        "--no-open",
        dest="open_browser",
        action="store_false",
        help="Do not open a browser tab; just start the server.",
    )
    return parser


def _build_local_serve_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="koru local-serve",
        description=(
            "Minimal localhost JSON/NDJSON hub for scripts and HTTP clients "
            "(see docs/local-service.md)."
        ),
    )
    parser.add_argument(
        "--host",
        default=None,
        help="Bind address (default: KORU_LOCAL_SERVICE_HOST or 127.0.0.1).",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=None,
        help=(
            "TCP port (default: KORU_LOCAL_SERVICE_PORT or 18766). "
            "Use 0 for an ephemeral OS-assigned port."
        ),
    )
    parser.add_argument(
        "--max-events",
        type=int,
        default=None,
        help="Ring buffer size (default: KORU_LOCAL_SERVICE_MAX_EVENTS or 256).",
    )
    return parser


def _build_scan_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="koru scan",
        description=(
            "Auto-generate planfile tickets from real repo signals "
            "(pytest collection errors, TODO/FIXME markers, missing gates "
            "and semcod tools, gitignore drift). Dry-run by default; "
            "pass --apply to create tickets via `planfile ticket create`."
        ),
    )
    parser.add_argument("--project", type=Path, default=Path.cwd(), help="Project root.")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Create the proposed tickets in planfile (otherwise dry-run).",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Cap the number of suggestions (default: all).",
    )
    parser.add_argument(
        "--skip-pytest",
        action="store_true",
        help="Do not run `pytest --collect-only` (faster scan).",
    )
    parser.add_argument(
        "--semcod-artifacts",
        action="store_true",
        help=(
            "Include semcod-style quality exports (jscpd JSON, code2llm analysis.toon*, "
            "testql_api_results.json, redup filtered JSON). "
            "Otherwise only when KORU_SCAN_SEMCOD_ARTIFACTS is truthy."
        ),
    )
    parser.add_argument(
        "--source",
        default="koru-scan",
        help="`--source` tag used when creating tickets (default: koru-scan).",
    )
    parser.add_argument(
        "--format",
        dest="output_format",
        choices=("text", "json", "markdown"),
        default="text",
        help="Output format for dry-run (default: text).",
    )
    return parser


def _render_scan_text(result: ScanResult) -> str:
    if not result.suggestions:
        return "koru scan: no suggestions — repo looks clean."
    lines: list[str] = [f"koru scan: {len(result.suggestions)} suggestion(s)"]
    for s in result.suggestions:
        marker = {"critical": "!!", "high": "!", "normal": "·", "low": " "}.get(
            s.priority,
            "·",
        )
        lines.append(f"  [{marker}] {s.priority:<8} {s.signal:<15} {s.title}")
    if result.applied:
        lines.append("")
        lines.append(f"Applied ({len(result.applied)}):")
        for t in result.applied:
            lines.append(f"  + {t}")
    if result.skipped:
        lines.append("")
        lines.append(f"Skipped ({len(result.skipped)}):")
        for t in result.skipped:
            lines.append(f"  - {t}")
    return "\n".join(lines)


def _render_scan_markdown(result: ScanResult) -> str:
    if not result.suggestions:
        return "# koru scan\n\n_No suggestions — repo looks clean._\n"
    lines = [
        "# koru scan",
        "",
        f"Found **{len(result.suggestions)}** suggestion(s).",
        "",
        "| priority | signal | title |",
        "| --- | --- | --- |",
    ]
    for s in result.suggestions:
        lines.append(f"| `{s.priority}` | `{s.signal}` | {s.title} |")
    if result.applied:
        lines.append("")
        lines.append(f"## Applied ({len(result.applied)})")
        for t in result.applied:
            lines.append(f"- {t}")
    if result.skipped:
        lines.append("")
        lines.append(f"## Skipped ({len(result.skipped)})")
        for t in result.skipped:
            lines.append(f"- {t}")
    return "\n".join(lines) + "\n"


def _scan_main(argv: list[str]) -> int:
    args = _build_scan_parser().parse_args(argv)
    result = run_scan(
        project=args.project.resolve(),
        apply=args.apply,
        limit=args.limit,
        skip_pytest=args.skip_pytest,
        include_semcod_artifacts=True if args.semcod_artifacts else None,
        source=args.source,
    )
    if args.output_format == "json":
        print(json.dumps(result.to_dict(), indent=2, sort_keys=True))
    elif args.output_format == "markdown":
        print(_render_scan_markdown(result))
    else:
        print(_render_scan_text(result))
    emit_management_event(
        tool="koru.scan",
        action="applied" if args.apply else "previewed",
        status="completed",
        message=f"{len(result.suggestions)} suggestion(s)",
        details={
            "project": str(args.project),
            "applied_count": len(result.applied),
            "skipped_count": len(result.skipped),
            "source": args.source,
        },
    )
    return 0


def _build_gate_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="koru gate",
        description=(
            "Manage CI/quality gate authorizations on planfile tickets. Subcommands: authorize."
        ),
    )
    sub = parser.add_subparsers(dest="subcommand", required=True)

    auth = sub.add_parser(
        "authorize",
        help="Record an advisory waiver / explicit gate authorization on a ticket.",
        description=(
            "Append a structured KORU-GATE-AUTH note to the ticket. The note "
            "records who authorized which gate mode, why, and which gates "
            "were skipped — so the audit trail is parseable, not buried in "
            "free-text."
        ),
    )
    auth.add_argument("ticket_id", help="Ticket ID (e.g. PLF-070).")
    auth.add_argument(
        "--mode",
        required=True,
        choices=list(GATE_VALID_MODES),
        help=(
            "advisory: agent ran a subset; full CI deferred. "
            "auto: full CI executed by queue. "
            "mandatory_human: do not advance until a human verifies."
        ),
    )
    auth.add_argument(
        "--skipped",
        action="append",
        default=[],
        help=(
            "Gate name skipped under this authorization "
            "(repeat for multiple gates, e.g. --skipped 'task test' "
            "--skipped 'task quality:gate')."
        ),
    )
    auth.add_argument(
        "--reason",
        required=True,
        help=(
            "Why the waiver was granted. Future readers (and your future "
            "self) need this — keep it specific."
        ),
    )
    auth.add_argument(
        "--authorized-by",
        default=None,
        help="Override the actor identifier (defaults to $USER / $LOGNAME).",
    )
    auth.add_argument(
        "--project",
        type=Path,
        default=Path.cwd(),
        help="Project root containing .planfile/.",
    )
    return parser


def _gate_main(argv: list[str]) -> int:
    args = _build_gate_parser().parse_args(argv)
    if args.subcommand != "authorize":
        print(f"koru gate: unknown subcommand {args.subcommand!r}", file=sys.stderr)
        return 2
    try:
        auth = authorize_gate(
            args.ticket_id,
            mode=args.mode,
            skipped=args.skipped,
            reason=args.reason,
            project=args.project,
            authorized_by=args.authorized_by,
        )
    except ValueError as exc:
        print(f"koru gate authorize: {exc}", file=sys.stderr)
        return 2
    except RuntimeError as exc:
        print(f"koru gate authorize: {exc}", file=sys.stderr)
        return 1

    print(
        f"koru gate: ✓ {auth.mode} waiver recorded on {auth.ticket} "
        f"by {auth.authorized_by} at {auth.authorized_at}",
    )
    if auth.skipped:
        print(f"  skipped: {', '.join(auth.skipped)}")
    print(f"  reason : {auth.reason}")
    emit_management_event(
        tool="koru.gate",
        action="authorized",
        status="completed",
        message=f"{auth.mode} waiver on {auth.ticket}",
        details={
            "ticket": auth.ticket,
            "mode": auth.mode,
            "skipped": list(auth.skipped),
            "reason": auth.reason,
            "authorized_by": auth.authorized_by,
            "authorized_at": auth.authorized_at,
        },
    )
    return 0


def _build_gc_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="koru gc",
        description=(
            "Garbage-collect stale planfile tickets. Removes done, failed, "
            "and blocked tickets that exceed --max-age days. Dry-run by "
            "default; pass --apply to actually delete."
        ),
    )
    parser.add_argument("--project", type=Path, default=Path.cwd(), help="Project root.")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Actually delete stale tickets (default is dry-run preview).",
    )
    parser.add_argument(
        "--max-age",
        type=int,
        default=DEFAULT_MAX_AGE_DAYS,
        help=f"Delete tickets finished more than N days ago (default {DEFAULT_MAX_AGE_DAYS}).",
    )
    parser.add_argument(
        "--keep-last",
        type=int,
        default=DEFAULT_KEEP_LAST,
        help=(
            "Always keep the N most recently finished tickets per status, "
            f"even if older than --max-age (default {DEFAULT_KEEP_LAST})."
        ),
    )
    parser.add_argument(
        "--status",
        default=",".join(sorted(GC_STATUSES)),
        help=(
            f"Comma-separated ticket statuses to clean (default: {','.join(sorted(GC_STATUSES))})."
        ),
    )
    parser.add_argument(
        "--sprint",
        default="current",
        help="Sprint YAML to scan (default: current).",
    )
    parser.add_argument(
        "--no-archive",
        action="store_true",
        help="Skip archiving removed tickets to .planfile/.koru/gc/.",
    )
    parser.add_argument(
        "--format",
        dest="output_format",
        choices=("text", "json"),
        default="text",
        help="Output format (default: text).",
    )
    return parser


def _gc_main(argv: list[str]) -> int:
    from .gc_cli_helpers import (
        emit_gc_management_event,
        gc_statuses_from_args,
        print_gc_report,
    )

    args = _build_gc_parser().parse_args(argv)
    result = run_gc(
        args.project.resolve(),
        apply=args.apply,
        statuses=gc_statuses_from_args(args.status),
        max_age_days=args.max_age,
        keep_last=args.keep_last,
        sprint=args.sprint,
        archive=not args.no_archive,
    )
    print_gc_report(args, result)
    emit_gc_management_event(args, result)
    return 0


def _build_queue_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="koru queue",
        description=("Manage the planfile queue. Subcommands: clean (sweep stale test fixtures)."),
    )
    sub = parser.add_subparsers(dest="subcommand", required=True)

    clean = sub.add_parser(
        "clean",
        help="Sweep stale fixture/test tickets out of the queue (dry-run by default).",
        description=(
            "Identify ``open`` / ``ready`` tickets that look like test "
            "fixtures (labels match FIXTURE_LABELS, optionally also "
            "names matching ^TEST:/^Test ) and complete them with a "
            "structured KORU-QUEUE-CLEAN audit note. Default is dry-run; "
            "pass --apply to actually close them."
        ),
    )
    clean.add_argument(
        "--apply",
        action="store_true",
        help="Actually close the candidates. Without this, prints what would happen.",
    )
    clean.add_argument(
        "--include-names",
        action="store_true",
        help="Also match tickets whose name starts with 'Test ' or 'TEST:'.",
    )
    clean.add_argument(
        "--include-active",
        action="store_true",
        help=(
            "DANGEROUS: also consider in_progress / waiting_input tickets. "
            "By default these are surfaced as 'skipped active' so the "
            "operator can decide whether to interrupt them."
        ),
    )
    clean.add_argument(
        "--max-age-days",
        type=float,
        default=None,
        help=(
            "Only sweep matching tickets older than N days. Used as a "
            "safety modifier on top of label/name match — never on its own."
        ),
    )
    clean.add_argument(
        "--reason",
        default="swept by koru queue clean",
        help="Free-text reason recorded in the audit note.",
    )
    clean.add_argument(
        "--project",
        type=Path,
        default=Path.cwd(),
        help="Project root containing .planfile/.",
    )
    clean.add_argument(
        "--format",
        dest="output_format",
        choices=("text", "json"),
        default="text",
        help="Output format for the report.",
    )
    return parser


def _render_clean_report_text(report: CleanupReport) -> str:
    lines: list[str] = []
    mode = "DRY-RUN" if report.dry_run else "APPLIED"
    header = f"koru queue clean [{mode}]"
    lines.append(header)
    lines.append("=" * len(header))
    if not report.candidates:
        lines.append("No fixture-like tickets found in the queue. Nothing to do.")
        if report.skipped_active:
            lines.append("")
            lines.append(
                f"Active tickets matching cleanup rules but skipped "
                f"(use --include-active to override): {', '.join(report.skipped_active)}",
            )
        return "\n".join(lines)
    lines.append(f"Candidates ({len(report.candidates)}):")
    for c in report.candidates:
        labels = ",".join(c.labels) if c.labels else "(no labels)"
        lines.append(f"  - {c.ticket_id} [{c.status}] {c.name[:60]}")
        lines.append(f"      labels: {labels}")
        lines.append(f"      rules : {', '.join(c.matched_rules)}")
        if c.age_days is not None:
            lines.append(f"      age   : {c.age_days:.1f} days")
    if report.dry_run:
        lines.append("")
        lines.append("Re-run with --apply to actually close these tickets.")
    else:
        if report.applied:
            lines.append("")
            lines.append(f"✓ Closed: {', '.join(report.applied)}")
        if report.failed:
            lines.append("")
            lines.append("✗ Failed:")
            for tid, err in report.failed:
                lines.append(f"  - {tid}: {err}")
    if report.skipped_active:
        lines.append("")
        lines.append(
            f"⚠ Active tickets matching cleanup rules (skipped, use "
            f"--include-active to override): {', '.join(report.skipped_active)}",
        )
    return "\n".join(lines)


def _queue_main(argv: list[str]) -> int:
    args = _build_queue_parser().parse_args(argv)
    if args.subcommand != "clean":
        print(f"koru queue: unknown subcommand {args.subcommand!r}", file=sys.stderr)
        return 2
    try:
        report = clean_queue(
            args.project,
            include_names=args.include_names,
            include_active=args.include_active,
            max_age_days=args.max_age_days,
            apply=args.apply,
            reason=args.reason,
        )
    except RuntimeError as exc:
        print(f"koru queue clean: {exc}", file=sys.stderr)
        return 1

    if args.output_format == "json":
        print(json.dumps(report.to_dict(), indent=2, sort_keys=True, default=str))
    else:
        print(_render_clean_report_text(report))

    emit_management_event(
        tool="koru.queue.clean",
        action="completed" if not report.failed else "failed",
        status="completed" if not report.failed else "failed",
        level="error" if report.failed else "info",
        message=(
            f"{'dry-run' if report.dry_run else 'applied'}: "
            f"{len(report.candidates)} candidates, "
            f"{len(report.applied)} applied, "
            f"{len(report.failed)} failed"
        ),
        details=report.to_dict(),
    )
    if report.failed:
        return 1
    return 0


def _build_agent_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="koru agent",
        description="Print or launch the best available LLM/IDE handoff for this project.",
    )
    parser.add_argument("--project", type=Path, default=Path.cwd(), help="Project root.")
    parser.add_argument(
        "--queue-name",
        default=None,
        help="Queue used when selecting the active ticket.",
    )
    parser.add_argument("--ticket", default=None, help="Render prompt for a specific ticket id.")
    parser.add_argument("--agent", dest="agent_id", default=None, help="Agent id to select.")
    parser.add_argument(
        "--launch",
        action="store_true",
        help="Launch the selected agent if it has a CLI.",
    )
    parser.add_argument("--list", action="store_true", help="List detected agents and exit.")
    parser.add_argument(
        "--format",
        dest="output_format",
        choices=("text", "json"),
        default="text",
        help="With --list: machine-readable json (default: text).",
    )
    parser.add_argument(
        "--lane",
        dest="lane_id",
        default=None,
        help=(
            "Agent lane id for --env-exports / --env-json (e.g. cursor, windsurf, claude-code). "
            "Falls back to --agent when set."
        ),
    )
    parser.add_argument(
        "--env-exports",
        action="store_true",
        help=(
            "Print shell exports for KORU_AUTOPILOT_* / queue actor hints; "
            "requires --lane or --agent."
        ),
    )
    parser.add_argument(
        "--env-json",
        action="store_true",
        help="Print recommended lane env as JSON (requires --lane or --agent).",
    )
    return parser


def _task_main(argv: list[str]) -> int:
    args = _build_task_parser().parse_args(argv)
    scaffold: dict[str, Any] | None = None
    if args.tool_id:
        registry, registry_path = load_tool_registry(args.tool_registry)
        if not registry:
            print(
                "koru task: tool registry is empty or missing. "
                "Use --tool-registry PATH or ensure docs/ai-tool-registry-2026.yaml exists.",
            )
            return 2
        tool = find_tool_entry(registry, args.tool_id)
        if tool is None:
            known = ", ".join(sorted(str(t.get("id")) for t in registry if t.get("id")))
            print(f"koru task: unknown --tool '{args.tool_id}'. Known ids: {known}")
            return 2
        scaffold = build_tool_task_scaffold(tool, adapter_kind=args.tool_kind)
        if registry_path is not None:
            scaffold.setdefault("source_context", {})
            if isinstance(scaffold.get("source_context"), dict):
                scaffold["source_context"]["registry"] = str(registry_path)

    try:
        created = create_nl_task(
            args.project,
            " ".join(args.text),
            sprint=args.sprint,
            queue_name=args.queue_name,
            priority=args.priority,
            scaffold=scaffold,
        )
    except ValueError as exc:
        print(f"koru task: {exc}")
        return 2
    print(f"koru task: ✓ created {created.ticket_id} in {created.path}")
    print(f"  name:  {created.name}")
    print(f"  queue: {args.queue_name or 'default'}")
    if args.tool_id:
        print(f"  tool:  {args.tool_id}")
        print("  note: scaffold ticket created — fill concrete executor inputs before queue run")
    print("Next: run `koru` to get the LLM prompt, or `koru --queue` to execute one task.")
    emit_management_event(
        tool="koru.task",
        action="created",
        status="completed",
        message=created.name,
        queue=args.queue_name,
        details={
            "ticket_id": created.ticket_id,
            "project": str(args.project),
            "sprint": args.sprint,
            "priority": args.priority,
        },
    )
    return 0


def _serve_main(argv: list[str]) -> int:
    from koruapi.dashboard import dashboard_main

    return dashboard_main(argv)


def _local_serve_main(argv: list[str]) -> int:
    from koruapi.local import local_main

    return local_main(argv)


def _agent_main(argv: list[str]) -> int:
    from .agent_cli_helpers import (
        print_agent_list,
        run_agent_handoff,
        try_agent_env_exports,
    )

    args = _build_agent_parser().parse_args(argv)
    project = args.project.resolve()
    env_code = try_agent_env_exports(args)
    if env_code is not None:
        return env_code
    if args.list:
        print_agent_list(args, detect_agent_options(project))
        return 0
    return run_agent_handoff(project, args)


def _is_bare_invocation(args: argparse.Namespace) -> bool:
    """True when the user typed only ``koru`` (or ``koru --project P``).

    Bare = no action flag (init/bootstrap/context/queue/watch) and no
    ``--command``. We route this to the markdown brief — the friendliest
    starting point for both humans and LLM agents.
    """
    return not (
        args.init
        or args.init_agent_lane
        or args.doctor
        or args.bootstrap
        or args.context
        or args.queue
        or args.watch
        or args.command
    )


def _build_topology_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="koru topology",
        description=(
            "Show & edit the project topology: which semcod components "
            "(regix, testql, wup, …) and pipelines (idle-diagnostics, "
            "gate:regix, autoloop:queue, …) are enabled. State is "
            "persisted to .koru/topology.yaml."
        ),
    )
    parser.add_argument("--project", type=Path, default=Path.cwd(), help="Project root.")
    parser.add_argument(
        "--format",
        dest="output_format",
        choices=("text", "json"),
        default="text",
        help="Output format for the listing (default text).",
    )
    parser.add_argument("--enable", metavar="ID", help="Enable component ID and persist.")
    parser.add_argument("--disable", metavar="ID", help="Disable component ID and persist.")
    parser.add_argument(
        "--enable-pipeline",
        metavar="ID",
        help="Enable pipeline ID and persist.",
    )
    parser.add_argument(
        "--disable-pipeline",
        metavar="ID",
        help="Disable pipeline ID and persist.",
    )
    parser.add_argument(
        "--is-enabled",
        metavar="ID",
        help=(
            "Print 'true' or 'false' for the given component or pipeline id "
            "(component takes precedence on collision) and exit 0/1."
        ),
    )
    parser.add_argument(
        "--enabled-components-for",
        metavar="PIPELINE",
        help="Print comma-separated enabled component ids for the pipeline and exit.",
    )
    return parser


def _render_topology_text(topology: dict[str, Any]) -> str:
    from .topology_cli import render_topology_text

    return render_topology_text(topology)


def _topology_main(argv: list[str]) -> int:
    from .topology import (
        load_topology,
        save_topology,
        set_component_enabled,
        set_pipeline_enabled,
    )

    args = _build_topology_parser().parse_args(argv)
    project = args.project.resolve()

    # Predicate modes — print value and exit; do not mutate.
    if args.is_enabled:
        topo = load_topology(project)
        target = args.is_enabled
        comp = (topo.get("components") or {}).get(target)
        pipe = (topo.get("pipelines") or {}).get(target)
        if isinstance(comp, dict):
            enabled = bool(comp.get("enabled", True))
        elif isinstance(pipe, dict):
            enabled = bool(pipe.get("enabled", True))
        else:
            print(f"koru topology: unknown id {target!r}", file=sys.stderr)
            return 2
        print("true" if enabled else "false")
        return 0 if enabled else 1

    if args.enabled_components_for:
        from .topology import enabled_components_for_pipeline

        ids = enabled_components_for_pipeline(project, args.enabled_components_for)
        print(",".join(ids))
        return 0

    from .topology_cli import TopologyMutation, apply_topology_mutations

    topo = load_topology(project)
    mutated, rc = apply_topology_mutations(
        topo,
        [
            TopologyMutation(args.enable, True, "component", set_component_enabled),
            TopologyMutation(args.disable, False, "component", set_component_enabled),
            TopologyMutation(args.enable_pipeline, True, "pipeline", set_pipeline_enabled),
            TopologyMutation(args.disable_pipeline, False, "pipeline", set_pipeline_enabled),
        ],
    )
    if rc != 0:
        return rc

    if mutated:
        path = save_topology(project, topo)
        print(f"koru topology: saved {path}")
        # Reload to surface the merged view back to the user.
        topo = load_topology(project)

    if args.output_format == "json":
        print(json.dumps(topo, indent=2, sort_keys=True, default=str))
    else:
        print(_render_topology_text(topo))
    return 0


def _build_runtime_context_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="koru runtime-context",
        description=(
            "Show the current project runtime context: systems, libraries, "
            "algorithms, APIs, applications, pipelines, and topology."
        ),
    )
    parser.add_argument("--project", type=Path, default=Path.cwd(), help="Project root.")
    parser.add_argument(
        "--format",
        dest="output_format",
        choices=("json", "text"),
        default="json",
        help="Output format (default json).",
    )
    return parser


def _render_runtime_context_text(context: dict[str, Any]) -> str:
    summary = context.get("summary") or {}
    lines = [
        f"koru runtime-context: {summary.get('project') or context.get('project_root')}",
        f"  version: {summary.get('version') or '-'}",
        f"  services: {summary.get('services', 0)}",
        f"  workspaces: {summary.get('workspaces', 0)}",
        f"  pipelines: {summary.get('pipelines', 0)}",
        f"  topology nodes: {summary.get('topology_nodes', 0)}",
        "",
        "Systems:",
    ]
    for service in context.get("systems") or []:
        ports = ", ".join(service.get("ports") or []) or "-"
        files = ", ".join(service.get("compose_files") or []) or "-"
        lines.append(f"  {service.get('name')}: ports={ports} compose={files}")
    lines.append("")
    lines.append("Pipelines:")
    for pipeline in context.get("pipelines") or []:
        mode = "interactive" if pipeline.get("interactive") else "batch"
        lines.append(f"  {pipeline.get('name')}: {mode} — {pipeline.get('description') or '-'}")
    return "\n".join(lines)


def _runtime_context_main(argv: list[str]) -> int:
    args = _build_runtime_context_parser().parse_args(argv)
    try:
        from planfile.runtime_context import build_runtime_context
    except ImportError as exc:
        print(
            "koru runtime-context: planfile.runtime_context is not available. "
            "Install/update semcod/planfile or add it to PYTHONPATH.",
            file=sys.stderr,
        )
        print(str(exc), file=sys.stderr)
        return 2
    context = build_runtime_context(args.project)
    if args.output_format == "text":
        print(_render_runtime_context_text(context))
    else:
        print(json.dumps(context, indent=2, sort_keys=True, default=str))
    return 0


def _init_ci_main(_argv: list[str]) -> int:
    """Print where to copy the reference GitHub Actions workflow (Epic 2 thin CI)."""
    print(
        "koru init-ci:\n"
        "  After copying the reference workflow, it should live at:\n"
        "    .github/workflows/koru-ci.yml\n"
        "  Upstream reference (semcod/koru):\n"
        "    https://github.com/semcod/koru/blob/main/.github/workflows/koru-ci.yml\n"
        "  How to adapt for your repo:\n"
        "    https://github.com/semcod/koru/blob/main/docs/ci-github.md\n"
        "  GitLab — example pipeline in this repo:\n"
        "    examples/ci/gitlab-ci.example.yml\n"
        "    https://github.com/semcod/koru/blob/main/examples/ci/gitlab-ci.example.yml\n"
        "  GitLab — how to adapt:\n"
        "    https://github.com/semcod/koru/blob/main/docs/ci-gitlab.md",
    )
    return 0


def _mcp_serve_main(argv: list[str]) -> int:
    from koruapi.mcp import mcp_main

    return mcp_main(argv)


def _agent_backends_main(argv: list[str]) -> int:
    """List or describe IDE agent backend profiles (``agent_backends``)."""
    from dataclasses import asdict

    from .agent_backends import get_agent_backend_profile, iter_agent_backend_profiles

    parser = argparse.ArgumentParser(prog="koru agent-backends")
    parser.add_argument(
        "--format",
        dest="output_format",
        choices=("text", "json"),
        default="text",
    )
    parser.add_argument(
        "backend_id",
        nargs="?",
        default=None,
        metavar="BACKEND_ID",
        help="When set, print one profile; otherwise list every profile id.",
    )
    args = parser.parse_args(argv)

    if args.backend_id:
        profile = get_agent_backend_profile(args.backend_id)
        if profile is None:
            sys.stderr.write(f"koru agent-backends: unknown id {args.backend_id!r}\n")
            sys.stderr.write("  run `koru agent-backends` for ids.\n")
            return 2
    else:
        profile = None

    if args.output_format == "json":
        if profile:
            print(json.dumps(asdict(profile), indent=2, sort_keys=True))
        else:
            print(
                json.dumps(
                    [asdict(p) for p in iter_agent_backend_profiles()],
                    indent=2,
                    sort_keys=True,
                ),
            )
        return 0

    if profile:
        print(f"id                 {profile.id}")
        print(f"transport          {profile.transport}")
        print(f"can_push_chat      {profile.can_push_chat}")
        print(f"can_pull_chat_text {profile.can_pull_chat_text}")
        print(f"needs_gui_session  {profile.needs_gui_session}")
        print(f"mcp_tools_only     {profile.mcp_tools_only}")
        print(f"primary_code       {profile.primary_code}")
        return 0

    for p in iter_agent_backend_profiles():
        print(p.id)
    return 0


def _init_ide_main(argv: list[str]) -> int:
    from .mcp_provision import init_ide_main

    return init_ide_main(argv)


def _refactor_planfile_handoff_main(argv: list[str]) -> int:
    """CLI: ``koru refactor-planfile-handoff`` — markdown for IDE chat (planfile tickets)."""
    import argparse

    from .refactor_planfile_handoff import render_planfile_refactor_handoff

    p = argparse.ArgumentParser(
        prog="koru refactor-planfile-handoff",
        description=(
            "Print markdown instructions for attaching project/analysis.toon.yaml "
            "and drafting planfile refactor tickets in the IDE chat."
        ),
    )
    p.add_argument("--project", type=Path, default=Path.cwd(), help="Project root.")
    args = p.parse_args(argv)
    print(render_planfile_refactor_handoff(args.project), end="")
    return 0


def ide_router_main(argv: list[str]) -> int:
    """CLI: ``koru ide-router`` — print resolved IDE / headless routing."""
    import argparse
    import json

    from .ide_router import resolve_ide_route

    p = argparse.ArgumentParser(prog="koru ide-router")
    p.add_argument(
        "--cli-ide",
        default="auto",
        help="Preview merge as if autonomous passed --autopilot-ide (default: auto).",
    )
    p.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="text lines (default) or json for scripts",
    )
    args = p.parse_args(argv)
    route = resolve_ide_route(cli_autopilot_ide=args.cli_ide)
    payload = {
        "autopilot_ide": route.autopilot_ide,
        "headless": route.headless,
        "primary_surface": route.primary_surface,
        "recommend_mcp": route.recommend_mcp,
        "recommend_autopilot_drive": route.recommend_autopilot_drive,
        "notes": route.notes,
    }
    if args.format == "json":
        print(json.dumps(payload, sort_keys=True))
    else:
        for key, val in payload.items():
            print(f"{key}: {val}")
    return 0


def _dsl_main(argv: list[str]) -> int:
    from korudsl.cli import main as dsl_main

    return dsl_main(argv)


def _api_main(argv: list[str]) -> int:
    from koruapi.cli import main as api_main

    return api_main(argv)


def _peek_project_from_argv(argv: list[str]) -> Path:
    for idx, part in enumerate(argv):
        if part == "--project" and idx + 1 < len(argv):
            return Path(argv[idx + 1]).expanduser().resolve()
        if part.startswith("--project="):
            return Path(part.split("=", 1)[1]).expanduser().resolve()
    return Path.cwd().resolve()


def _auto_main(argv: list[str]) -> int:
    """``koru auto``: stop prior autonomous/auto loops, then start with ``--replace-existing``."""
    if "--allow-duplicate" not in argv:
        stdio = os.environ.get("KORU_STDIO_FORMAT", "human")
        stop_prior_autonomous_for_auto_start(_peek_project_from_argv(argv), stdio_format=stdio)
    if "--replace-existing" not in argv and "--allow-duplicate" not in argv:
        argv = ["--replace-existing", *argv]
    return autonomous_main(argv, invoked_as_auto=True)


_SUBCOMMANDS: dict[str, Callable[[list[str]], int]] = {
    "init-ci": _init_ci_main,
    "init-ide": _init_ide_main,
    "agent-backends": _agent_backends_main,
    "task": _task_main,
    "agent": _agent_main,
    "local-serve": _local_serve_main,
    "serve": _serve_main,
    "scan": _scan_main,
    "refactor-planfile-handoff": _refactor_planfile_handoff_main,
    "gate": _gate_main,
    "queue": _queue_main,
    "gc": _gc_main,
    "tools": _tools_main,
    "mcp-serve": _mcp_serve_main,
    "ide-router": ide_router_main,
    "autopilot": autopilot_main,
    "autonomous": autonomous_main,
    "auto": lambda argv: _auto_main(argv),
    "dsl": _dsl_main,
    "api": _api_main,
    "topology": _topology_main,
    "runtime-context": _runtime_context_main,
}


def _doctor_main(args: argparse.Namespace, raw_args: list[str]) -> int:
    report = run_diagnostics(args.project)
    fix_payload = _doctor_fix_payload(report) if getattr(args, "fix", False) else None
    explicit_format = "--format" in raw_args
    if explicit_format and args.output_format == "json":
        payload = report.to_dict()
        if fix_payload is not None:
            payload["fix"] = fix_payload
        print(json.dumps(payload, indent=2, sort_keys=True))
    elif explicit_format and args.output_format == "markdown":
        print(_render_doctor_with_fix(report, fix_payload))
    else:
        print(_render_doctor_with_fix(report, fix_payload))
    emit_management_event(
        tool="koru.doctor",
        action="completed",
        status="failed" if report.has_failures else "completed",
        level="error" if report.has_failures else "info",
        message=", ".join(f"{k}={v}" for k, v in report.summary().items() if v),
        queue=args.queue_name,
        details={"project": str(args.project)},
    )
    return 1 if report.has_failures else 0


def _doctor_fix_payload(report: Any) -> dict[str, object]:
    """Guided remediation for ``koru --doctor --fix``.

    The root doctor is intentionally read-only. This payload tells a human or
    LLM operator which explicit commands may mutate the host/project.
    """
    project = str(report.project)
    failing = [c.name for c in report.checks if c.status == "fail"]
    warnings = [c.name for c in report.checks if c.status == "warn"]
    return {
        "mode": "guided",
        "writes_by_default": False,
        "failing_checks": failing,
        "warning_checks": warnings,
        "commands": [
            f"koru --doctor --project {shlex.quote(project)} --format json",
            f"koru --init --project {shlex.quote(project)}",
            "koru autopilot doctor --fix",
            "koru autopilot setup-host --install --dry-run",
            "koru autopilot setup-host --install",
            "koru autopilot install-plugin --dry-run --format json",
            "koru autopilot install-plugin",
            "koru autopilot install-unit",
            f"koru autonomous safe-up --project {shlex.quote(project)}",
        ],
        "notes": [
            "`koru --doctor --fix` only prints guidance; it does not edit files.",
            "`setup-host --install` may run apt and needs sudo on Debian/Ubuntu.",
            "`install-plugin` mutates the selected IDE extension directory.",
            "`--diagnostic-tickets` creates deduplicated planfile tickets for failed checks.",
        ],
    }


def _render_doctor_with_fix(report: Any, fix_payload: dict[str, object] | None) -> str:
    text = render_doctor_text(report)
    if fix_payload is None:
        return text
    lines = [text, "", "Guided repair (--fix):"]
    for command in fix_payload.get("commands", []):
        lines.append(f"  - {command}")
    notes = fix_payload.get("notes")
    if isinstance(notes, list) and notes:
        lines.append("Notes:")
        for note in notes:
            lines.append(f"  - {note}")
    return "\n".join(lines)


def _init_main(args: argparse.Namespace) -> int:
    try:
        report = init_project(
            args.project,
            from_file=args.from_file,
            sprint=args.sprint,
            force=args.force,
            agent_lane=args.agent_lane,
            prepare_host_environment=not args.skip_host_environment,
        )
    except FileExistsError as exc:
        print(f"koru init: {exc}")
        return 1
    except (FileNotFoundError, ValueError) as exc:
        print(f"koru init: {exc}")
        return 2
    print(f"koru init: ✓ project initialised at {report.project}")
    print(report.summary())
    print()
    next_parts: list[str] = []
    if report.agent_lane_files_written and report.agent_lane:
        next_parts.append(
            "run `koru autonomous up --project . --agent-lane auto` "
            "(sets lane env; optional: source `.planfile/.koru/shell-env.sh` "
            "for other terminals)",
        )
    if report.autopilot_host_setup_written:
        next_parts.append(
            "run `./.planfile/.koru/setup-autopilot-host.sh` "
            "(or `koru autopilot setup-host`) to check injectors / apt vs human steps",
        )
    if report.host_environment_written:
        next_parts.append(
            "read `.planfile/.koru/host-environment.md` for this machine's autopilot checklist",
        )
    next_parts.extend(
        [
            "run `koru` for the LLM brief",
            "`koru --queue --loop` to drain the starter sprint",
        ],
    )
    print("Next: " + "; ".join(next_parts) + ".")
    emit_management_event(
        tool="koru.init",
        action="completed",
        status="completed",
        message=report.summary(),
        queue=args.queue_name,
        details={
            "project": str(args.project),
            "sprint": args.sprint,
            "used_starter_pipeline": report.used_starter_pipeline,
            "agent_lane": report.agent_lane,
            "agent_lane_files_written": report.agent_lane_files_written,
            "autopilot_host_setup_written": report.autopilot_host_setup_written,
            "koru_project_pipeline_yaml_written": report.koru_project_pipeline_yaml_written,
            "host_environment_written": report.host_environment_written,
        },
    )
    return 0


def _init_agent_lane_main(args: argparse.Namespace) -> int:
    try:
        report = refresh_init_agent_lane(
            args.project,
            agent_lane=args.agent_lane,
            prepare_host_environment=not args.skip_host_environment,
        )
    except FileNotFoundError as exc:
        print(f"koru init-agent-lane: {exc}")
        return 2
    print(f"koru init-agent-lane: ✓ {report.project}")
    print(report.summary())
    print()
    next_parts: list[str] = []
    if report.agent_lane_files_written and report.agent_lane:
        next_parts.append(
            "run `koru autonomous up --project . --agent-lane auto` "
            "(sets lane env; optional: source `.planfile/.koru/shell-env.sh` "
            "for other terminals)",
        )
    elif report.agent_lane is None:
        next_parts.append("shell helpers removed (use --agent-lane auto to restore)")
    if report.autopilot_host_setup_written:
        next_parts.append(
            "`./.planfile/.koru/setup-autopilot-host.sh` or `koru autopilot setup-host`",
        )
    if report.host_environment_written:
        next_parts.append("read `.planfile/.koru/host-environment.md` for this machine")
    print("Next: " + "; ".join(next_parts or ["no shell helpers to run"]) + ".")
    emit_management_event(
        tool="koru.init_agent_lane",
        action="completed",
        status="completed",
        message=report.summary(),
        queue=args.queue_name,
        details={
            "project": str(args.project),
            "agent_lane": report.agent_lane,
            "agent_lane_files_written": report.agent_lane_files_written,
            "autopilot_host_setup_written": report.autopilot_host_setup_written,
            "host_environment_written": report.host_environment_written,
        },
    )
    return 0


def _context_main(args: argparse.Namespace) -> int:
    ctx = build_context(
        project=args.project,
        ticket_id=args.ticket,
        queue_name=args.queue_name,
        include_fixtures=getattr(args, "include_fixtures", None),
    )
    if args.output_format == "markdown":
        print(render_markdown_handoff(ctx))
    else:
        print(json.dumps(ctx, indent=2, sort_keys=True))
    return 0


def _bootstrap_main(args: argparse.Namespace) -> int:
    emit_management_event(
        tool="koru.bootstrap",
        action="started",
        status="running",
        message=str(args.from_file or ""),
        queue=args.queue_name,
        details={"project": str(args.project), "sprint": args.sprint},
    )
    if args.from_file is None:
        parser = _build_parser()
        parser.error("--bootstrap requires --from PATH")
    try:
        report = import_flat_pipeline(
            args.from_file,
            args.project,
            sprint=args.sprint,
            overwrite=args.force,
        )
    except FileExistsError as exc:
        print(f"koru bootstrap: {exc}")
        emit_management_event(
            tool="koru.bootstrap",
            action="failed",
            status="failed",
            level="error",
            message=str(exc),
            queue=args.queue_name,
        )
        return 1
    except (FileNotFoundError, ValueError) as exc:
        print(f"koru bootstrap: {exc}")
        emit_management_event(
            tool="koru.bootstrap",
            action="failed",
            status="failed",
            level="error",
            message=str(exc),
            queue=args.queue_name,
        )
        return 2
    print("koru bootstrap: ✓ imported")
    print(report.summary())
    emit_management_event(
        tool="koru.bootstrap",
        action="completed",
        status="completed",
        message=report.summary(),
        queue=args.queue_name,
        details={"project": str(args.project), "sprint": args.sprint},
    )
    return 0


def _watch_main(args: argparse.Namespace) -> int:
    emit_management_event(
        tool="koru.watch",
        action="started",
        status="running",
        message=args.ws_url,
        queue=args.queue_name,
    )
    try:
        seen = asyncio.run(watch_planfile_events(args.ws_url, max_events=args.max_events))
    except RuntimeError as exc:
        print(f"koru watch: {exc}")
        emit_management_event(
            tool="koru.watch",
            action="failed",
            status="failed",
            level="error",
            message=str(exc),
            queue=args.queue_name,
        )
        return 1
    emit_management_event(
        tool="koru.watch",
        action="completed",
        status="completed",
        message=f"seen={seen}",
        queue=args.queue_name,
        details={"ws_url": args.ws_url, "seen": seen},
    )
    return 0


def _queue_run_main(args: argparse.Namespace) -> int:
    from .queue_cli_helpers import (
        emit_queue_run_started,
        open_queue_run_log,
        run_queue_loop_mode,
        run_queue_single_mode,
    )

    emit_queue_run_started(args)
    run_log = open_queue_run_log(args)
    runners = {
        "planfile_runner": _queue_run_process,
        "shell_runner": _queue_run_shell_command,
        "api_runner": _queue_run_api_request,
        "llm_runner": _queue_run_llm_request,
        "prompt_runner": _queue_default_human_prompt,
    }
    if args.loop:
        return run_queue_loop_mode(args, run_log, **runners)
    return run_queue_single_mode(args, run_log, **runners)


def _command_loop_main(args: argparse.Namespace) -> int:
    emit_management_event(
        tool="koru.loop",
        action="started",
        status="running",
        message=args.command,
        details={"workspace": str(args.workspace), "include": args.include},
    )
    repositories = discover_repositories(args.workspace, args.include)
    command = shlex.split(args.command)

    report = run_closed_loop(
        command=command,
        repositories=repositories,
        max_rounds=args.max_rounds,
    )

    print(
        f"koru: repos={len(report.succeeded) + len(report.failed)} "
        f"succeeded={len(report.succeeded)} failed={len(report.failed)} "
        f"rounds={report.rounds_executed}",
    )
    for repository in report.failed:
        print(f"FAILED: {repository}")

    exit_code = 0 if not report.failed else 1
    emit_management_event(
        tool="koru.loop",
        action="completed" if exit_code == 0 else "failed",
        status="completed" if exit_code == 0 else "failed",
        level="error" if exit_code else "info",
        message=(
            f"repos={len(report.succeeded) + len(report.failed)} "
            f"succeeded={len(report.succeeded)} failed={len(report.failed)}"
        ),
        details={"failed": [str(item) for item in report.failed]},
    )
    return exit_code


def main() -> int:
    raw_args = sys.argv[1:]
    if raw_args and raw_args[0] in _SUBCOMMANDS:
        return _SUBCOMMANDS[raw_args[0]](raw_args[1:])

    args = _build_parser().parse_args(raw_args)

    if _is_bare_invocation(args):
        args.context = True
        args.output_format = "markdown"

    if args.doctor:
        return _doctor_main(args, raw_args)
    if args.init_agent_lane:
        return _init_agent_lane_main(args)
    if args.init:
        return _init_main(args)
    if args.context:
        return _context_main(args)
    if args.bootstrap:
        return _bootstrap_main(args)
    if args.watch:
        return _watch_main(args)
    if args.queue:
        return _queue_run_main(args)

    if not args.command:
        parser = _build_parser()
        parser.error("--command is required unless --queue is used")

    return _command_loop_main(args)


if __name__ == "__main__":
    raise SystemExit(main())
