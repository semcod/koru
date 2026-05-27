"""CLI command for managing the planfile queue."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from koru.events import emit_management_event
from koru.queue_clean import CleanupReport, clean_queue
from koru.ticket_evidence import render_ticket_evidence_report, validate_ticket_evidence


def build_queue_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="koru queue",
        description=(
            "Manage the planfile queue. Subcommands: clean (sweep stale test fixtures), "
            "validate-evidence (check generated-ticket source hashes)."
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
    validate = sub.add_parser(
        "validate-evidence",
        help="Validate source.context.evidence hashes on generated planfile tickets.",
        description=(
            "Check whether generated tickets still match the artifact/file hashes "
            "captured when they were created. Prints regenerate_command for stale "
            "tickets so an IDE LLM can refresh the source artifact before work."
        ),
    )
    validate.add_argument(
        "--ticket",
        default=None,
        help="Validate one ticket id. Default: validate tickets matching --status.",
    )
    validate.add_argument(
        "--status",
        default="open",
        help="Planfile status filter for list mode (default: open; use all for every ticket).",
    )
    validate.add_argument(
        "--project",
        type=Path,
        default=Path.cwd(),
        help="Project root containing .planfile/.",
    )
    validate.add_argument(
        "--format",
        dest="output_format",
        choices=("text", "json"),
        default="text",
        help="Output format for the report.",
    )
    return parser


def render_clean_report_text(report: CleanupReport) -> str:
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


def queue_main(argv: list[str]) -> int:
    args = build_queue_parser().parse_args(argv)
    if args.subcommand == "validate-evidence":
        return _queue_validate_evidence_main(args)
    if args.subcommand != "clean":
        print(f"koru queue: unknown subcommand {args.subcommand!r}", file=sys.stderr)
        return 2
    return _queue_clean_main(args)


def _queue_validate_evidence_main(args: argparse.Namespace) -> int:
    try:
        report = validate_ticket_evidence(
            args.project,
            ticket_id=args.ticket,
            status="" if args.status == "all" else args.status,
        )
    except (RuntimeError, json.JSONDecodeError) as exc:
        print(f"koru queue validate-evidence: {exc}", file=sys.stderr)
        return 1
    if args.output_format == "json":
        print(json.dumps(report.to_dict(), indent=2, sort_keys=True, default=str))
    else:
        print(render_ticket_evidence_report(report))
    return 1 if report.stale_count or report.missing_evidence_count else 0


def _queue_clean_main(args: argparse.Namespace) -> int:
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

    _print_clean_queue_report(report, args.output_format)
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


def _print_clean_queue_report(report: Any, output_format: str) -> None:
    if output_format == "json":
        print(json.dumps(report.to_dict(), indent=2, sort_keys=True, default=str))
    else:
        print(render_clean_report_text(report))


def queue_run_main(args: argparse.Namespace) -> int:
    from koru.queue_cli_helpers import (
        emit_queue_run_started,
        open_queue_run_log,
        run_queue_loop_mode,
        run_queue_single_mode,
    )
    from koru.queue import (
        run_process as _queue_run_process,
        run_shell_command as _queue_run_shell_command,
        run_api_request as _queue_run_api_request,
        run_llm_request as _queue_run_llm_request,
        default_human_prompt as _queue_default_human_prompt,
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
