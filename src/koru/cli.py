"""Command-line entrypoint for koru."""

from __future__ import annotations

import argparse
import asyncio
import json
import shlex
import sys
from pathlib import Path

from .agents import (
    detect_agent_options,
    launch_agent,
    save_agent_prompt,
    select_agent,
)
from .bootstrap import import_flat_pipeline
from .context import build_context, render_markdown_handoff
from .doctor import render_text as render_doctor_text, run_diagnostics
from .events import emit_management_event
from .gate import VALID_MODES as GATE_VALID_MODES, authorize_gate
from .gc import DEFAULT_KEEP_LAST, DEFAULT_MAX_AGE_DAYS, GC_STATUSES, run_gc
from .init import init_project
from .loop import discover_repositories, run_closed_loop
from .planfile_queue import run_next_planfile_task, run_planfile_queue_loop
from .queue_clean import CleanupReport, clean_queue
from .run_log import open_run_log_eagerly
from .scan import ScanResult, run_scan
from .serve import DEFAULT_HOST, DEFAULT_PORT, ServeConfig, serve
from .tasks import create_nl_task
from .watch import watch_planfile_events


def _command_value(value: str) -> str:
    stripped = value.strip()
    if not stripped:
        raise argparse.ArgumentTypeError("Command cannot be empty")
    return stripped


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run closed-loop automation on semcod repositories."
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
        "--init",
        action="store_true",
        help=(
            "Initialise a koru-managed project in --project: import a "
            "flat pipeline (or generate a 2-ticket starter scaffold), "
            "write .planfile/.koru/policy.yaml stub, and add "
            ".planfile/.koru/ to .gitignore. Pass --from <yaml> to "
            "import an existing pipeline; --force to re-init."
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
            s.priority, "·"
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
            "Manage CI/quality gate authorizations on planfile tickets. "
            "Subcommands: authorize."
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
        f"by {auth.authorized_by} at {auth.authorized_at}"
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
            "Comma-separated ticket statuses to clean "
            f"(default: {','.join(sorted(GC_STATUSES))})."
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
    args = _build_gc_parser().parse_args(argv)
    statuses = frozenset(s.strip() for s in args.status.split(",") if s.strip())
    result = run_gc(
        args.project.resolve(),
        apply=args.apply,
        statuses=statuses,
        max_age_days=args.max_age,
        keep_last=args.keep_last,
        sprint=args.sprint,
        archive=not args.no_archive,
    )
    if args.output_format == "json":
        payload = {
            "dry_run": result.dry_run,
            "candidates": [
                {
                    "ticket_id": c.ticket_id,
                    "name": c.name,
                    "status": c.status,
                    "age_days": c.age_days,
                }
                for c in result.candidates
            ],
            "removed": result.removed,
            "kept": result.kept,
            "archived_to": str(result.archived_to) if result.archived_to else None,
            "errors": result.errors,
        }
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        mode = "DRY RUN" if result.dry_run else "APPLIED"
        if not result.candidates:
            print(f"koru gc ({mode}): no stale tickets found (max-age={args.max_age}d)")
        else:
            print(f"koru gc ({mode}): {result.summary()}")
            print()
            for c in result.candidates:
                marker = "✗" if c.ticket_id in result.removed else "·"
                age = f"{c.age_days:.0f}d" if c.age_days != float("inf") else "??d"
                print(f"  {marker} {c.ticket_id:<14} {c.status:<10} {age:>6}  {c.name[:60]}")
            if result.removed:
                print(f"\n  → {'Would remove' if result.dry_run else 'Removed'}: {len(result.removed)} ticket(s)")
            if result.kept:
                print(f"  → Kept: {len(result.kept)} ticket(s)")
            if result.archived_to:
                print(f"  → Archived to: {result.archived_to}")
            if result.errors:
                print(f"  → Errors: {len(result.errors)}")
                for err in result.errors:
                    print(f"    {err}")
    emit_management_event(
        tool="koru.gc",
        action="applied" if args.apply else "previewed",
        status="completed",
        message=result.summary(),
        details={
            "project": str(args.project),
            "removed": result.removed,
            "kept": result.kept,
            "max_age_days": args.max_age,
            "keep_last": args.keep_last,
        },
    )
    return 0


def _build_queue_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="koru queue",
        description=(
            "Manage the planfile queue. Subcommands: clean (sweep stale "
            "test fixtures)."
        ),
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
                f"(use --include-active to override): {', '.join(report.skipped_active)}"
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
            f"--include-active to override): {', '.join(report.skipped_active)}"
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
    return parser


def _task_main(argv: list[str]) -> int:
    args = _build_task_parser().parse_args(argv)
    try:
        created = create_nl_task(
            args.project,
            " ".join(args.text),
            sprint=args.sprint,
            queue_name=args.queue_name,
            priority=args.priority,
        )
    except ValueError as exc:
        print(f"koru task: {exc}")
        return 2
    print(f"koru task: ✓ created {created.ticket_id} in {created.path}")
    print(f"  name:  {created.name}")
    print(f"  queue: {args.queue_name or 'default'}")
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
    args = _build_serve_parser().parse_args(argv)
    config = ServeConfig(
        project=args.project.resolve(),
        host=args.host,
        port=args.port,
        open_browser=args.open_browser,
        queue_name=args.queue_name,
    )
    emit_management_event(
        tool="koru.serve",
        action="started",
        status="running",
        message=f"http://{config.host}:{config.port}/",
        queue=config.queue_name,
        details={"project": str(config.project), "open_browser": config.open_browser},
    )
    exit_code = serve(config)
    emit_management_event(
        tool="koru.serve",
        action="completed" if exit_code == 0 else "failed",
        status="completed" if exit_code == 0 else "failed",
        level="info" if exit_code == 0 else "error",
        message=f"exit={exit_code}",
        queue=config.queue_name,
    )
    return exit_code


def _agent_main(argv: list[str]) -> int:
    args = _build_agent_parser().parse_args(argv)
    project = args.project.resolve()
    agents = detect_agent_options(project)

    if args.list:
        for agent in agents:
            marker = "✓" if agent.available else "·"
            launch = "launchable" if agent.launchable else "manual"
            print(f"{marker} {agent.id:<14} {launch:<10} {agent.reason}")
        return 0

    ctx = build_context(
        project=project,
        ticket_id=args.ticket,
        queue_name=args.queue_name,
    )
    prompt = render_markdown_handoff(ctx)
    if not args.launch:
        save_path = save_agent_prompt(project, prompt)
        print(prompt)
        print(f"\nPrompt saved: {save_path}")
        return 0

    agent = select_agent(
        agents,
        agent_id=args.agent_id,
        interactive=sys.stdin.isatty(),
    )
    if agent is None:
        print("koru agent: no matching agent detected. Use `koru agent --list`.")
        return 2
    return launch_agent(agent, project, prompt)


def _is_bare_invocation(args: argparse.Namespace) -> bool:
    """True when the user typed only ``koru`` (or ``koru --project P``).

    Bare = no action flag (init/bootstrap/context/queue/watch) and no
    ``--command``. We route this to the markdown brief — the friendliest
    starting point for both humans and LLM agents.
    """
    return not (
        args.init
        or args.doctor
        or args.bootstrap
        or args.context
        or args.queue
        or args.watch
        or args.command
    )


def main() -> int:
    raw_args = sys.argv[1:]
    if raw_args and raw_args[0] == "task":
        return _task_main(raw_args[1:])
    if raw_args and raw_args[0] == "agent":
        return _agent_main(raw_args[1:])
    if raw_args and raw_args[0] == "serve":
        return _serve_main(raw_args[1:])
    if raw_args and raw_args[0] == "scan":
        return _scan_main(raw_args[1:])
    if raw_args and raw_args[0] == "gate":
        return _gate_main(raw_args[1:])
    if raw_args and raw_args[0] == "queue":
        return _queue_main(raw_args[1:])
    if raw_args and raw_args[0] == "gc":
        return _gc_main(raw_args[1:])

    args = _build_parser().parse_args(raw_args)

    # Friendliest default: ``koru`` with no action flag emits the
    # markdown brief. LLM agents pasted into a chat just see the rules.
    if _is_bare_invocation(args):
        args.context = True
        args.output_format = "markdown"

    if args.doctor:
        report = run_diagnostics(args.project)
        # Doctor's friendly default is text. We only honour an explicit
        # --format choice; otherwise text wins regardless of the global
        # --format default (which is "json" for context).
        explicit_format = "--format" in raw_args
        if explicit_format and args.output_format == "json":
            print(json.dumps(report.to_dict(), indent=2, sort_keys=True))
        elif explicit_format and args.output_format == "markdown":
            print(render_doctor_text(report))
        else:
            print(render_doctor_text(report))
        emit_management_event(
            tool="koru.doctor",
            action="completed",
            status="failed" if report.has_failures else "completed",
            level="error" if report.has_failures else "info",
            message=", ".join(
                f"{k}={v}" for k, v in report.summary().items() if v
            ),
            queue=args.queue_name,
            details={"project": str(args.project)},
        )
        return 1 if report.has_failures else 0

    if args.init:
        try:
            report = init_project(
                args.project,
                from_file=args.from_file,
                sprint=args.sprint,
                force=args.force,
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
        print("Next: run `koru` to get the LLM brief, or "
              "`koru --queue --loop` to drain the starter sprint.")
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
            },
        )
        return 0

    if args.context:
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

    if args.bootstrap:
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

    if args.watch:
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

    if args.queue:
        emit_management_event(
            tool="koru.queue",
            action="started",
            status="running",
            message="loop" if args.loop else "single",
            queue=args.queue_name,
            details={
                "project": str(args.project),
                "actor": args.actor,
                "dry_run": args.dry_run,
                "interactive": args.interactive,
            },
        )
        # Per-run JSONL log under <project>/.planfile/.koru/runs/.
        # Skip for --dry-run (preserves "dry-run leaves zero trace") and
        # when the operator passes --no-log.
        run_log = None
        if not args.no_log and not args.dry_run:
            run_log = open_run_log_eagerly(args.project, prefix="queue")
            run_log.write_header(
                project=args.project,
                mode="loop" if args.loop else "single",
                actor=args.actor,
                queue_name=args.queue_name,
                interactive=args.interactive,
            )

        if args.loop:
            def _progress(r, i):  # noqa: ANN001 — internal helper
                ticket = r.ticket_id or "-"
                kind = r.executor_kind or "-"
                marker = {
                    "completed": "✓",
                    "failed": "✗",
                    "waiting_input": "⏸",
                    "idle": "•",
                    "dry_run": "?",
                    "unsupported_executor": "!",
                    "planfile_error": "!",
                }.get(r.status, "·")
                print(f"  [{i:>3}] {marker} {r.status:<22} {ticket:<14} ({kind})")
                if run_log is not None:
                    run_log.write_iteration(iteration=i, result=r)
                emit_management_event(
                    tool="koru.queue",
                    action="iteration",
                    status=r.status,
                    level="error" if r.status in {"failed", "planfile_error"} else "info",
                    message=r.message,
                    queue=args.queue_name,
                    details={
                        "iteration": i,
                        "ticket_id": r.ticket_id,
                        "executor_kind": r.executor_kind,
                        "exit_code": r.exit_code,
                    },
                )

            loop_result = run_planfile_queue_loop(
                project=args.project,
                actor=args.actor,
                queue_name=args.queue_name,
                interactive=args.interactive,
                max_iterations=args.max_iterations,
                progress_callback=_progress,
            )
            if run_log is not None:
                run_log.write_footer(summary=loop_result)
            print()
            print(f"koru queue loop: {loop_result.summary()}")
            if loop_result.completed:
                print(f"  completed: {', '.join(loop_result.completed)}")
            if loop_result.failed:
                print(f"  failed:    {', '.join(loop_result.failed)}")
            if loop_result.waiting:
                print(f"  waiting:   {', '.join(loop_result.waiting)}")
            exit_code = 0 if loop_result.last_status in {
                "completed", "idle", "waiting_input", "dry_run"
            } else 1
            emit_management_event(
                tool="koru.queue",
                action="completed" if exit_code == 0 else "failed",
                status=loop_result.last_status,
                level="error" if exit_code else "info",
                message=loop_result.summary(),
                queue=args.queue_name,
                details={
                    "completed": loop_result.completed,
                    "failed": loop_result.failed,
                    "waiting": loop_result.waiting,
                    "iterations": loop_result.iterations,
                },
            )
            return exit_code

        result = run_next_planfile_task(
            project=args.project,
            actor=args.actor,
            dry_run=args.dry_run,
            queue_name=args.queue_name,
            interactive=args.interactive,
        )
        if run_log is not None:
            run_log.write_iteration(iteration=1, result=result)
            # Build a one-shot summary so the footer schema matches loop runs.
            single_summary = type(
                "SingleSummary",
                (),
                {
                    "iterations": 1,
                    "completed": (
                        [result.ticket_id]
                        if result.status == "completed" and result.ticket_id
                        else []
                    ),
                    "failed": (
                        [result.ticket_id]
                        if result.status == "failed" and result.ticket_id
                        else []
                    ),
                    "waiting": (
                        [result.ticket_id]
                        if result.status == "waiting_input" and result.ticket_id
                        else []
                    ),
                    "last_status": result.status,
                },
            )()
            run_log.write_footer(summary=single_summary)
        print(
            f"koru queue: status={result.status} "
            f"ticket={result.ticket_id or '-'} executor={result.executor_kind or '-'}"
        )
        if result.message:
            print(result.message)
        exit_code = 0 if result.status in {"completed", "idle", "waiting_input", "dry_run"} else 1
        emit_management_event(
            tool="koru.queue",
            action="completed" if exit_code == 0 else "failed",
            status=result.status,
            level="error" if exit_code else "info",
            message=result.message,
            queue=args.queue_name,
            details={
                "ticket_id": result.ticket_id,
                "executor_kind": result.executor_kind,
                "exit_code": result.exit_code,
                "dry_run": args.dry_run,
            },
        )
        return exit_code

    if not args.command:
        parser = _build_parser()
        parser.error("--command is required unless --queue is used")

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
        f"rounds={report.rounds_executed}"
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


if __name__ == "__main__":
    raise SystemExit(main())
