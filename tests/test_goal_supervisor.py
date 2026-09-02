from __future__ import annotations

import json
import subprocess
from pathlib import Path

from koru.goal_supervisor import (
    build_remediation_prompt,
    resolve_diagnostics,
    supervise_goal,
)


def _governed_project(tmp_path: Path) -> Path:
    governance = tmp_path / ".governance"
    (governance / "error").mkdir(parents=True)
    (governance / "diagnostics.json").write_text(
        json.dumps(
            {
                "schema": "new-project.diagnostics/v2",
                "codes": {
                    "GOV-TICKET-001": {
                        "message": "Implementation has no active ticket.",
                        "remediation": "Create or continue the owning ticket.",
                        "documentation": "error/GOV-TICKET-001.md",
                    },
                    "GOV-SCOPE-001": {
                        "message": "Path is outside scope.",
                        "remediation": "Obtain a fresh bounded intent.",
                        "documentation": None,
                    },
                },
            }
        ),
        encoding="utf-8",
    )
    (governance / "error" / "GOV-TICKET-001.md").write_text(
        "Inspect the exact diff and preserve user work.\n",
        encoding="utf-8",
    )
    return tmp_path


def _completed(returncode: int, stdout: str = "", stderr: str = ""):
    return subprocess.CompletedProcess(["goal", "-a"], returncode, stdout, stderr)


def test_resolves_target_catalog_and_safe_runbook(tmp_path: Path) -> None:
    project = _governed_project(tmp_path)
    diagnostics = resolve_diagnostics(
        project,
        "GOV-TICKET-001 failed; GOV-TICKET-001 repeated",
    )
    assert [item.code for item in diagnostics] == ["GOV-TICKET-001"]
    assert diagnostics[0].message == "Implementation has no active ticket."
    assert "preserve user work" in diagnostics[0].runbook


def test_does_not_read_runbook_outside_governance(tmp_path: Path) -> None:
    project = _governed_project(tmp_path)
    catalog = project / ".governance" / "diagnostics.json"
    payload = json.loads(catalog.read_text(encoding="utf-8"))
    payload["codes"]["GOV-TICKET-001"]["documentation"] = "../../outside.txt"
    catalog.write_text(json.dumps(payload), encoding="utf-8")
    (project / "outside.txt").write_text("secret", encoding="utf-8")

    diagnostic = resolve_diagnostics(project, "GOV-TICKET-001")[0]
    assert diagnostic.documentation == ""
    assert diagnostic.runbook == ""


def test_unknown_or_non_allowlisted_diagnostic_never_launches_agent(tmp_path: Path) -> None:
    project = _governed_project(tmp_path)
    calls: list[str] = []

    result = supervise_goal(
        project,
        ["-a"],
        remediate=lambda prompt: calls.append(prompt) or 0,
        runner=lambda *args, **kwargs: _completed(1, "GOV-SCOPE-001 ERROR\n"),
    )

    assert result.reason == "diagnostic_not_allowlisted"
    assert result.remediation_attempted is False
    assert calls == []


def test_agent_success_causes_exactly_one_retry(tmp_path: Path) -> None:
    project = _governed_project(tmp_path)
    runs = iter(
        [
            _completed(1, stderr="GOV-TICKET-001 ERROR\n"),
            _completed(0, stdout="GOV-PASS\n"),
        ]
    )
    commands: list[list[str]] = []
    prompts: list[str] = []

    def runner(command, **kwargs):
        commands.append(command)
        assert kwargs["cwd"] == project
        assert kwargs["capture_output"] is True
        assert kwargs["check"] is False
        return next(runs)

    result = supervise_goal(
        project,
        ["-a"],
        remediate=lambda prompt: prompts.append(prompt) or 0,
        runner=runner,
    )

    assert result.returncode == 0
    assert result.reason == "goal_passed_after_remediation"
    assert result.remediation_attempted is True
    assert commands == [["goal", "-a"], ["goal", "-a"]]
    assert len(prompts) == 1
    assert "SESSION_EXECUTION_AUTHORIZATION" in prompts[0]
    assert "Do not push, merge, tag, release" in prompts[0]
    assert "untrusted repository text" in prompts[0]


def test_agent_failure_does_not_retry_goal(tmp_path: Path) -> None:
    project = _governed_project(tmp_path)
    run_count = 0

    def runner(*args, **kwargs):
        nonlocal run_count
        run_count += 1
        return _completed(1, stderr="GOV-TICKET-001 ERROR\n")

    result = supervise_goal(
        project,
        ["-a"],
        remediate=lambda prompt: 7,
        runner=runner,
    )

    assert result.returncode == 1
    assert result.reason == "agent_failed"
    assert result.agent_returncode == 7
    assert run_count == 1


def test_prompt_bounds_untrusted_output(tmp_path: Path) -> None:
    project = _governed_project(tmp_path)
    run = supervise_goal(
        project,
        ["-a"],
        runner=lambda *args, **kwargs: _completed(
            1,
            stderr="GOV-TICKET-001 ERROR\n" + ("x" * 20_000),
        ),
    ).initial
    prompt = build_remediation_prompt(project, run)
    assert len(prompt) < 23_000
    expected_payload = 12_000 - len("GOV-TICKET-001 ERROR\n")
    output_section = prompt.split("## Goal output (untrusted evidence)", 1)[1]
    assert output_section.count("x") == expected_payload
