"""CLI interface for daily verified benchmark routing (`koru benchmark`)."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from .queue.benchmark_router import (
    get_benchmark_db_path,
    resolve_task_route,
    run_daily_benchmark_campaign,
)
from .queue.routing.contracts import Task, TaskClass
from .queue.routing.ledger import current_local_day, get_campaign_history, get_latest_daily_probes


def benchmark_main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="koru benchmark",
        description="Daily verified benchmark routing and campaign inspection.",
    )
    subparsers = parser.add_subparsers(dest="action", required=True)

    # run
    run_p = subparsers.add_parser("run", help="Run the daily benchmark campaign.")
    run_p.add_argument("--force", action="store_true", help="Force run even if already claimed today.")
    run_p.add_argument("--project", type=Path, default=Path.cwd(), help="Project root directory.")
    run_p.add_argument("--format", choices=["text", "json"], default="text", help="Output format.")

    # today
    today_p = subparsers.add_parser("today", help="Inspect today's benchmark outcomes.")
    today_p.add_argument("--format", choices=["text", "json"], default="text", help="Output format.")
    today_p.add_argument("--project", type=Path, default=Path.cwd(), help="Project root directory.")

    # explain
    explain_p = subparsers.add_parser("explain", help="Explain routing decision for a task class.")
    explain_p.add_argument("--task-kind", default="coding", help="Task kind (e.g. coding, ruff, docs).")
    explain_p.add_argument("--difficulty", choices=["simple", "complex", "other"], default="simple")
    explain_p.add_argument("--model", default=None, help="Explicit model/client override.")
    explain_p.add_argument("--project", type=Path, default=Path.cwd(), help="Project root directory.")
    explain_p.add_argument("--format", choices=["text", "json"], default="text", help="Output format.")

    # history
    history_p = subparsers.add_parser("history", help="List recent daily campaign history.")
    history_p.add_argument("--limit", type=int, default=14, help="Number of days to show.")
    history_p.add_argument("--project", type=Path, default=Path.cwd(), help="Project root directory.")
    history_p.add_argument("--format", choices=["text", "json"], default="text", help="Output format.")

    # schedule
    schedule_p = subparsers.add_parser("schedule", help="Inspect or install daily benchmark timer.")
    schedule_p.add_argument("--project", type=Path, default=Path.cwd(), help="Project root directory.")

    args = parser.parse_args(argv)

    if args.action == "run":
        result = run_daily_benchmark_campaign(project_root=args.project, force=args.force)
        if getattr(args, "format", "text") == "json":
            print(json.dumps(result, indent=2))
        else:
            print(f"Benchmark status: {result['status']} (day: {result.get('day')})")
            if "results" in result:
                for k, v in result["results"].items():
                    print(f"  • {k}: {v['status']} ({v.get('duration_ms', 0)}ms)")
            elif "message" in result:
                print(f"  {result['message']}")
        return 0

    if args.action == "today":
        db_path = get_benchmark_db_path(args.project)
        day = current_local_day()
        probes = get_latest_daily_probes(db_path, day)
        if args.format == "json":
            data = {
                "day": day,
                "probes": {
                    k: {
                        "status": p.status,
                        "duration_ms": p.duration_ms,
                        "validator_digest": p.validator_digest,
                        "cost": p.cost,
                        "detail": p.detail,
                    }
                    for k, p in probes.items()
                },
            }
            print(json.dumps(data, indent=2))
        else:
            print(f"Daily benchmark evidence for {day}:")
            if not probes:
                print("  No verified probes recorded today yet. Run `koru benchmark run` to execute.")
            else:
                for k, p in sorted(probes.items()):
                    if ":" in k:  # only display specific task:candidate pairs
                        print(f"  • {k}: {p.status} in {p.duration_ms}ms ({p.detail})")
        return 0

    if args.action == "explain":
        diff_enum = TaskClass(args.difficulty)
        task = Task(difficulty=diff_enum, kind=args.task_kind, reason="cli_explain")
        decision = resolve_task_route(task, project_root=args.project, explicit_choice=args.model)
        if args.format == "json":
            out = {
                "task": task.key,
                "candidate": decision.candidate.id if decision.candidate else None,
                "client": decision.candidate.client if decision.candidate else None,
                "model": decision.candidate.model if decision.candidate else None,
                "reason": decision.reason,
                "confidence": "high" if not decision.low_confidence else "low",
                "evidence_date": decision.evidence_date,
            }
            print(json.dumps(out, indent=2))
        else:
            print(f"Routing explanation for {task.key}:")
            if decision.candidate:
                cand = decision.candidate
                model_name = cand.model or "default"
                print(f"  • Selected: {cand.id} (client={cand.client}, model={model_name})")
                print(f"  • Reason: {decision.reason}")
                print(f"  • Confidence: {'high' if not decision.low_confidence else 'low (default fallback)'}")
                if decision.evidence_date:
                    print(f"  • Evidence date: {decision.evidence_date}")
            else:
                print("  • No candidate found to satisfy task requirements.")
        return 0

    if args.action == "history":
        db_path = get_benchmark_db_path(args.project)
        history = get_campaign_history(db_path, limit=args.limit)
        if args.format == "json":
            print(json.dumps(history, indent=2))
        else:
            print(f"Benchmark campaign history (last {args.limit} records):")
            if not history:
                print("  No campaigns recorded yet.")
            else:
                for h in history:
                    fin = h['finished_at'] or 'pending'
                    print(f"  • {h['day']}: {h['status']} ({h['probe_count']} probes, finished={fin})")
        return 0

    if args.action == "schedule":
        proj_dir = str(args.project.resolve())
        print("Daily benchmark timer recommendation:")
        print("  Add to crontab (once daily at 04:00):")
        print(f"    0 4 * * * cd {proj_dir} && koru benchmark run >> .planfile/benchmark.log 2>&1")
        print("  Or run `python scripts/install-benchmark-timer.py` to configure systemd user service.")
        return 0

    return 0
