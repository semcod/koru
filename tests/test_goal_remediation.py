from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from koru.cli_goal_remediation import (
    GoalProposalError,
    consume_goal_proposal,
    goal_remediation_main,
)
from koru.task_models import CreatedTask


def _proposal() -> dict:
    return {
        "schema": "planfile.ticket-proposal.v1",
        "proposal_id": "goal-governance/GOV-INTENT-003/abcdef0123456789",
        "dedupe_key": "goal-governance:GOV-INTENT-003",
        "name": "Naprawa governance: GOV-INTENT-003",
        "description": "Goal failed with GOV-INTENT-003.",
        "priority": "high",
        "source": {
            "tool": "goal",
            "tool_version": "2.2.0",
            "finding_id": "GOV-INTENT-003",
            "artifact_digest": "sha256:" + "a" * 64,
        },
        "labels": ["goal", "governance"],
        "files": [".governance/diagnostics.json"],
        "acceptance_criteria": ["Run the managed governance check."],
        "evidence_refs": [".governance/diagnostics.json#GOV-INTENT-003"],
    }


def _write_proposal(project: Path, payload: dict | None = None) -> Path:
    path = project / ".planfile" / ".koru" / "goal-remediation" / "proposal.json"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(payload or _proposal()), encoding="utf-8")
    return path


def test_consumes_proposal_into_one_automatic_deduplicated_ticket(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    proposal_path = _write_proposal(project)
    calls: list[tuple[Path, str, dict]] = []

    def create_task(path, text, **kwargs):
        calls.append((path, text, kwargs))
        return CreatedTask(
            ticket_id="PLF-041",
            sprint="current",
            path=path / ".planfile/sprints/current.yaml",
            name=kwargs["scaffold"]["title"],
        )

    result = consume_goal_proposal(project, proposal_path, create_task=create_task)

    assert result.ticket_id == "PLF-041"
    assert result.reused is False
    assert len(calls) == 1
    path, text, kwargs = calls[0]
    scaffold = kwargs["scaffold"]
    assert path == project
    assert "Acceptance criteria" in text
    assert kwargs["priority"] == "high"
    assert scaffold["source_context"]["dedupe_key"] == "goal-governance:GOV-INTENT-003"
    assert scaffold["executor_kind"] == "llm"
    assert scaffold["executor_mode"] == "automatic"
    assert scaffold["max_attempts"] == 1
    assert scaffold["inputs"]["include_project_context"] is True
    assert "executor" not in scaffold["source_context"]
    assert scaffold["files"] == [".governance/diagnostics.json"]


def test_strict_contract_rejects_execution_authority(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    payload = _proposal()
    payload["executor"] = {"kind": "shell"}
    proposal_path = _write_proposal(project, payload)

    with pytest.raises(GoalProposalError, match="TicketProposalV1 validation"):
        consume_goal_proposal(project, proposal_path)


def test_proposal_must_be_inside_target_project(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    outside = tmp_path / "proposal.json"
    outside.write_text(json.dumps(_proposal()), encoding="utf-8")

    with pytest.raises(GoalProposalError, match="inside the target project"):
        consume_goal_proposal(project, outside)


def test_cli_writes_the_delegated_ticket_to_planfile(tmp_path: Path, capsys) -> None:
    project = tmp_path / "project"
    project.mkdir()
    subprocess.run(["git", "init", "--quiet"], cwd=project, check=True)
    proposal_path = _write_proposal(project)

    assert (
        goal_remediation_main(
            [
                "--project",
                str(project),
                "--proposal",
                str(proposal_path),
                "--format",
                "json",
            ]
        )
        == 0
    )

    output = json.loads(capsys.readouterr().out)
    assert output["ticket_id"] == "PLF-001"
    sprint = (project / ".planfile/sprints/current.yaml").read_text(encoding="utf-8")
    assert "PLF-001" in sprint
    assert "executor" in sprint
    assert "llm" in sprint
    exclude = subprocess.run(
        ["git", "rev-parse", "--git-path", "info/exclude"],
        cwd=project,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    excluded = Path(exclude if Path(exclude).is_absolute() else project / exclude)
    contents = excluded.read_text(encoding="utf-8")
    assert ".planfile/" in contents
    assert ".koru/" in contents
    status = subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=all"],
        cwd=project,
        check=True,
        capture_output=True,
        text=True,
    )
    assert status.stdout == ""
