"""Consume Goal governance proposals into the local Planfile queue."""

from __future__ import annotations

import argparse
import io
import json
import subprocess
import sys
from collections.abc import Callable
from contextlib import redirect_stdout
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from koru.tasks import CreatedTask, create_nl_task


@dataclass(frozen=True)
class GoalRemediationTicket:
    """Ticket result returned by the proposal consumer."""

    ticket_id: str
    name: str
    reused: bool
    proposal_id: str
    proposal_hash: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "koru.goal-remediation/v1",
            "ticket_id": self.ticket_id,
            "name": self.name,
            "reused": self.reused,
            "proposal_id": self.proposal_id,
            "proposal_hash": self.proposal_hash,
        }


class GoalProposalError(ValueError):
    """Raised when a Goal proposal is not safe to consume."""


_LOCAL_RUNTIME_EXCLUDES = (".planfile/", ".koru/", ".planfile_analysis/")


def _mark_tracked_runtime(project: Path) -> None:
    """Keep tracked legacy runtime files out of the local implementation diff."""
    result = subprocess.run(
        ["git", "ls-files", "-z", "--", *_LOCAL_RUNTIME_EXCLUDES],
        cwd=project,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0 or not result.stdout:
        return
    subprocess.run(
        ["git", "update-index", "--skip-worktree", "-z", "--stdin"],
        cwd=project,
        input=result.stdout,
        capture_output=True,
        check=False,
    )


def _exclude_local_runtime(project: Path) -> None:
    """Keep Koru's local queue state out of the target's implementation diff."""
    result = subprocess.run(
        ["git", "rev-parse", "--git-path", "info/exclude"],
        cwd=project,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0 or not result.stdout.strip():
        return
    raw_path = Path(result.stdout.strip())
    exclude_path = raw_path if raw_path.is_absolute() else project / raw_path
    try:
        existing = exclude_path.read_text(encoding="utf-8") if exclude_path.exists() else ""
        lines = set(existing.splitlines())
        additions = [pattern for pattern in _LOCAL_RUNTIME_EXCLUDES if pattern not in lines]
        if additions:
            prefix = "" if not existing or existing.endswith("\n") else "\n"
            block = (
                prefix
                + "# Koru/Goal local remediation queue runtime\n"
                + "\n".join(additions)
                + "\n"
            )
            exclude_path.parent.mkdir(parents=True, exist_ok=True)
            with exclude_path.open("a", encoding="utf-8") as stream:
                stream.write(block)
    except OSError:
        # A read-only or nonstandard checkout must not prevent ticket intake.
        pass
    _mark_tracked_runtime(project)


def _proposal_path(project: Path, raw_path: Path) -> Path:
    candidate = raw_path if raw_path.is_absolute() else project / raw_path
    resolved = candidate.resolve()
    try:
        resolved.relative_to(project.resolve())
    except ValueError as error:
        raise GoalProposalError("proposal must be located inside the target project") from error
    return resolved


def _load_proposal(project: Path, proposal_path: Path):
    from planfile.contracts import TicketProposalV1
    from pydantic import ValidationError

    path = _proposal_path(project, proposal_path)
    try:
        if path.stat().st_size > 128_000:
            raise GoalProposalError("proposal exceeds the 128 KiB intake limit")
        payload = json.loads(path.read_text(encoding="utf-8"))
    except GoalProposalError:
        raise
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise GoalProposalError(f"cannot read proposal: {error}") from error
    try:
        return TicketProposalV1.model_validate(payload)
    except ValidationError as error:
        raise GoalProposalError(f"proposal failed TicketProposalV1 validation: {error}") from error


def consume_goal_proposal(
    project: Path,
    proposal_path: Path,
    *,
    create_task: Callable[..., CreatedTask] = create_nl_task,
) -> GoalRemediationTicket:
    """Validate one Goal proposal and create or reuse its Planfile ticket."""
    project = project.expanduser().resolve()
    if not project.is_dir():
        raise GoalProposalError(f"project is not a directory: {project}")
    proposal = _load_proposal(project, proposal_path)
    criteria = "\n".join(f"- {criterion}" for criterion in proposal.acceptance_criteria)
    text = proposal.description
    if criteria:
        text = f"{text}\n\nAcceptance criteria:\n{criteria}"
    scaffold = {
        "title": proposal.name,
        "source_tool": proposal.source.tool,
        "source_context": {
            "dedupe_key": proposal.dedupe_key,
            "proposal_id": proposal.proposal_id,
            "proposal_hash": proposal.proposal_hash,
            "finding_id": proposal.source.finding_id,
            **(
                {"artifact_digest": proposal.source.artifact_digest}
                if proposal.source.artifact_digest
                else {}
            ),
        },
        "labels": [*proposal.labels, "koru-delegated", "goal-remediation"],
        "files": list(proposal.files),
        "executor_kind": "llm",
        "executor_mode": "automatic",
        "max_attempts": 1,
        "inputs": {
            "include_project_context": True,
            "context_files": list(proposal.files),
            "max_context_chars": 20_000,
            "system_prompt": (
                "This is a bounded governance remediation. Read AGENTS.md and "
                "the target-owned diagnostic runbook, preserve user work, "
                "and do not weaken governance or publish changes."
            ),
        },
    }
    created = create_task(
        project,
        text,
        priority=proposal.priority,
        scaffold=scaffold,
    )
    _exclude_local_runtime(project)
    return GoalRemediationTicket(
        ticket_id=created.ticket_id,
        name=created.name,
        reused=created.reused,
        proposal_id=proposal.proposal_id,
        proposal_hash=proposal.proposal_hash,
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="koru goal-remediation",
        description="Create a Planfile ticket from a validated Goal proposal.",
    )
    parser.add_argument("--project", type=Path, default=Path.cwd())
    parser.add_argument("--proposal", type=Path, required=True)
    parser.add_argument("--format", choices=("text", "json"), default="text")
    return parser


def goal_remediation_main(argv: list[str]) -> int:
    args = _build_parser().parse_args(argv)
    activity_output = io.StringIO()
    try:
        output_stream = activity_output if args.format == "json" else sys.stdout
        with redirect_stdout(output_stream):
            result = consume_goal_proposal(args.project, args.proposal)
    except GoalProposalError as error:
        if activity_output.getvalue():
            print(activity_output.getvalue(), file=sys.stderr, end="")
        print(f"koru goal-remediation: {error}", file=sys.stderr)
        return 2
    if activity_output.getvalue():
        print(activity_output.getvalue(), file=sys.stderr, end="")
    if args.format == "json":
        print(json.dumps(result.to_dict(), indent=2, sort_keys=True))
    else:
        action = "reused" if result.reused else "created"
        print(f"koru goal-remediation: {action} {result.ticket_id} ({result.name})")
    return 0


__all__ = [
    "GoalProposalError",
    "GoalRemediationTicket",
    "consume_goal_proposal",
    "goal_remediation_main",
]
