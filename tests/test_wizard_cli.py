"""Smoke tests for the wizard CLI orchestrator."""

from __future__ import annotations

import io
import json
from pathlib import Path

import pytest
import yaml

from koru.wizard.cli import (
    ScriptedPrompter,
    StdinPrompter,
    run_wizard,
    wizard_main,
)
from koru.wizard.ide import DetectedIDE
from koru.wizard.project import ProjectCandidate


@pytest.fixture()
def project_with_planfile(tmp_path: Path) -> Path:
    project = tmp_path / "demo-svc"
    project.mkdir()
    (project / ".planfile").mkdir()
    (project / "pyproject.toml").write_text("[project]\nname='demo-svc'\n", encoding="utf-8")
    return project


def test_run_wizard_creates_ticket_from_default_tree(project_with_planfile: Path) -> None:
    prompter = ScriptedPrompter(["quality", "cc_refactor"])

    result = run_wizard(
        prompter=prompter,
        project_override=project_with_planfile,
        ide_override=[],
        project_candidates_override=[],
        create=True,
        use_llx=False,
    )

    assert result.path == ["quality", "cc_refactor"]
    assert result.ticket_id is not None
    assert "-" in result.ticket_id
    sprint_yaml = project_with_planfile / ".planfile" / "sprints" / "current.yaml"
    assert sprint_yaml.exists()
    data = yaml.safe_load(sprint_yaml.read_text(encoding="utf-8"))
    tickets = data["sprint"]["tickets"]
    assert any("koru-wizard" in ticket.get("labels", []) for ticket in tickets.values())


def test_run_wizard_no_create_skips_planfile_write(project_with_planfile: Path) -> None:
    prompter = ScriptedPrompter(["frontend", "design_system"])

    result = run_wizard(
        prompter=prompter,
        project_override=project_with_planfile,
        ide_override=[],
        project_candidates_override=[],
        create=False,
        use_llx=False,
    )

    assert result.ticket_id is None
    assert result.skipped_creation is True
    assert result.ticket_title.lower().startswith("frontend")
    assert not (project_with_planfile / ".planfile" / "sprints").exists()


def test_run_wizard_offers_running_ide(project_with_planfile: Path) -> None:
    ides = [
        DetectedIDE(id="cursor", label="Cursor", running=True, pid=123, path="/opt/Cursor/cursor"),
        DetectedIDE(id="vscode", label="VS Code", running=False, pid=None, path="/usr/bin/code"),
    ]
    prompter = ScriptedPrompter(["cursor", "architecture", "ddd"])

    result = run_wizard(
        prompter=prompter,
        project_override=project_with_planfile,
        ide_override=ides,
        project_candidates_override=[
            ProjectCandidate(path=project_with_planfile, source="Cursor workspace"),
        ],
        create=False,
        use_llx=False,
    )

    assert result.chosen_ide is not None
    assert result.chosen_ide.id == "cursor"
    assert result.path == ["architecture", "ddd"]


def test_stdin_prompter_accepts_numeric_and_id(monkeypatch) -> None:
    from koru.wizard.tree import TreeOption

    options = (TreeOption(id="a", label="A"), TreeOption(id="b", label="B"))

    p = StdinPrompter(stream_in=io.StringIO("2\n"), stream_out=io.StringIO())
    assert p.ask_choice("?", options).id == "b"

    p2 = StdinPrompter(stream_in=io.StringIO("a\n"), stream_out=io.StringIO())
    assert p2.ask_choice("?", options).id == "a"


def test_wizard_detect_only_json_output(capsys) -> None:
    rc = wizard_main(["--detect-only", "--format", "json"])
    captured = capsys.readouterr()
    assert rc == 0
    payload = json.loads(captured.out)
    assert "ides" in payload and "projects" in payload and "llx_available" in payload
