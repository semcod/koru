"""Argument parser helpers for the legacy ``koru`` CLI entrypoint."""

from __future__ import annotations

import argparse
import importlib.metadata
from pathlib import Path


def _command_value(value: str) -> str:
    stripped = value.strip()
    if not stripped:
        raise argparse.ArgumentTypeError("Command cannot be empty")
    return stripped


def _cli_version() -> str:
    try:
        return importlib.metadata.version("koru")
    except importlib.metadata.PackageNotFoundError:
        return "unknown"


def _add_common_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--version", action="version", version=f"koru {_cli_version()}")
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


def _add_queue_arguments(parser: argparse.ArgumentParser) -> None:
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


def _add_watch_arguments(parser: argparse.ArgumentParser) -> None:
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


def _add_bootstrap_and_init_arguments(parser: argparse.ArgumentParser) -> None:
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


def _add_doctor_and_context_arguments(parser: argparse.ArgumentParser) -> None:
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
        "--repair",
        action="store_true",
        help=(
            "With --doctor, apply safe autopilot repairs, then rerun diagnostics."
        ),
    )
    parser.add_argument(
        "--catalog",
        action="store_true",
        help=(
            "With --doctor, include a catalog of known problems and their "
            "detection rules."
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


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run closed-loop automation on semcod repositories.",
    )
    _add_common_arguments(parser)
    _add_queue_arguments(parser)
    _add_watch_arguments(parser)
    _add_bootstrap_and_init_arguments(parser)
    _add_doctor_and_context_arguments(parser)
    return parser
