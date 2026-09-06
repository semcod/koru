"""CLI adapter for supervised Goal governance runs."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Callable
from pathlib import Path

from koru.goal_supervisor import GoalRun, SupervisionResult, supervise_goal
from koru.goal_workspace import GoalProjectResolutionError, resolve_goal_project


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="koru goal",
        description="Run Goal and optionally hand an allowlisted governance repair to one agent.",
    )
    parser.add_argument("--project", type=Path, default=Path.cwd(), help="Target repository.")
    parser.add_argument(
        "--repo",
        default=None,
        help="Relative Git repository path inside an umbrella --project workspace.",
    )
    parser.add_argument("--agent", dest="agent_id", default=None, help="Agent lane to launch.")
    parser.add_argument(
        "--auto-remediate",
        action=argparse.BooleanOptionalAction,
        default=True,
        help=(
            "Launch one agent for GOV-TICKET-001 and retry Goal once "
            "(default: enabled)."
        ),
    )
    parser.add_argument(
        "--format",
        dest="output_format",
        choices=("text", "json"),
        default="text",
    )
    parser.add_argument(
        "--goal-executable",
        default="goal",
        help="Goal executable name or path; it is invoked directly without a shell.",
    )
    parser.add_argument(
        "goal_args",
        nargs=argparse.REMAINDER,
        help="Goal arguments after `--`; defaults to `-a`.",
    )
    return parser


def _goal_args(raw: list[str]) -> list[str]:
    return raw[1:] if raw[:1] == ["--"] else raw


def _print_run(run: GoalRun) -> None:
    if run.stdout:
        print(run.stdout, end="" if run.stdout.endswith("\n") else "\n")
    if run.stderr:
        print(
            run.stderr,
            end="" if run.stderr.endswith("\n") else "\n",
            file=sys.stderr,
        )


def _print_text(result: SupervisionResult) -> None:
    _print_run(result.initial)
    codes = ", ".join(item.code for item in result.initial.diagnostics) or "none"
    print(f"koru goal: diagnostics={codes}; decision={result.reason}", file=sys.stderr)
    if result.final is not result.initial:
        print("koru goal: retry after agent remediation", file=sys.stderr)
        _print_run(result.final)


def _agent_remediator(project: Path, agent_id: str | None) -> Callable[[str], int]:
    def launch(prompt: str) -> int:
        from koru.agents import detect_agent_options, launch_agent, select_agent

        agents = detect_agent_options(project)
        selected = select_agent(agents, agent_id=agent_id, interactive=sys.stdin.isatty())
        if selected is None:
            print(
                "koru goal: no matching agent detected; run `koru agent --list`.",
                file=sys.stderr,
            )
            return 2
        return launch_agent(selected, project, prompt)

    return launch


def goal_main(argv: list[str]) -> int:
    args = _build_parser().parse_args(argv)
    workspace = args.project.expanduser().resolve()
    if not workspace.is_dir():
        print(f"koru goal: project is not a directory: {workspace}", file=sys.stderr)
        return 2
    try:
        project = resolve_goal_project(workspace, args.repo)
    except GoalProjectResolutionError as exc:
        if args.output_format == "json":
            print(json.dumps(exc.to_dict(), indent=2, sort_keys=True))
        else:
            print(f"koru goal: {exc}", file=sys.stderr)
        return 2
    goal_args = _goal_args(args.goal_args) or ["-a"]
    remediate = _agent_remediator(project, args.agent_id) if args.auto_remediate else None
    result = supervise_goal(
        project,
        goal_args,
        executable=args.goal_executable,
        remediate=remediate,
    )
    if args.output_format == "json":
        print(json.dumps(result.to_dict(), indent=2, sort_keys=True))
    else:
        _print_text(result)
        if result.reason == "eligible" and not args.auto_remediate:
            print("koru goal: rerun with --auto-remediate to launch one agent.", file=sys.stderr)
    return result.returncode
