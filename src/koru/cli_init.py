"""CLI command for initializing koru projects."""

from __future__ import annotations

import argparse

from koru.events import emit_management_event
from koru.init import init_project, refresh_init_agent_lane


def init_main(args: argparse.Namespace) -> int:
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
    print(f"Next: {'; '.join(next_parts)}.")
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


def init_agent_lane_main(args: argparse.Namespace) -> int:
    try:
        report = refresh_init_agent_lane(
            args.project,
            agent_lane=args.agent_lane,
            prepare_host_environment=not args.skip_host_environment,
        )
    except FileNotFoundError as exc:
        print(f"koru init agent-lane: {exc}")
        return 2
    except (ValueError, RuntimeError) as exc:
        print(f"koru init agent-lane: {exc}")
        return 2
    print(f"koru init agent-lane: ✓ refreshed at {report.project}")
    print(report.summary())
    emit_management_event(
        tool="koru.init.agent-lane",
        action="completed",
        status="completed",
        message=report.summary(),
        queue=args.queue_name,
        details={
            "project": str(args.project),
            "agent_lane": report.agent_lane,
            "agent_lane_files_written": report.agent_lane_files_written,
            "host_environment_written": report.host_environment_written,
        },
    )
    return 0

def init_ci_main(_argv: list[str]) -> int:
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
