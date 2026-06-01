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
        DetectedIDE(
            id="cursor",
            label="Cursor",
            running=True,
            pid=123,
            path="/opt/Cursor/cursor",
        ),
        DetectedIDE(
            id="vscode",
            label="VS Code",
            running=False,
            pid=None,
            path="/usr/bin/code",
        ),
    ]
    prompter = ScriptedPrompter(["architecture", "ddd"])

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


def test_run_wizard_auto_picks_terminal_host_ide(
    monkeypatch, project_with_planfile: Path
) -> None:
    monkeypatch.delenv("KORU_AUTOPILOT_INSTANCE", raising=False)
    monkeypatch.delenv("KORU_AUTOPILOT_IDE", raising=False)
    monkeypatch.setattr(
        "koru.wizard.orchestrator.detect_terminal_host_ide_id",
        lambda: "vscodium",
    )
    ides = [
        DetectedIDE(
            id="cursor",
            label="Cursor",
            running=True,
            pid=123,
            path="/opt/Cursor/cursor",
        ),
        DetectedIDE(
            id="vscodium",
            label="VSCodium",
            running=True,
            pid=456,
            path="/usr/bin/codium",
        ),
    ]
    prompter = ScriptedPrompter(["quality", "cc_refactor"])

    result = run_wizard(
        prompter=prompter,
        project_override=project_with_planfile,
        ide_override=ides,
        project_candidates_override=[],
        create=False,
        use_llx=False,
    )

    assert result.chosen_ide is not None
    assert result.chosen_ide.id == "vscodium"
    assert result.path == ["quality", "cc_refactor"]


def test_run_wizard_prompts_when_multiple_running_ides_are_ambiguous(
    monkeypatch, project_with_planfile: Path
) -> None:
    monkeypatch.delenv("KORU_AUTOPILOT_INSTANCE", raising=False)
    monkeypatch.delenv("KORU_AUTOPILOT_IDE", raising=False)
    monkeypatch.setattr(
        "koru.wizard.orchestrator.detect_terminal_host_ide_id",
        lambda: None,
    )
    ides = [
        DetectedIDE(
            id="cursor",
            label="Cursor",
            running=True,
            pid=123,
            path="/opt/Cursor/cursor",
        ),
        DetectedIDE(
            id="vscodium",
            label="VSCodium",
            running=True,
            pid=456,
            path="/usr/bin/codium",
        ),
    ]
    prompter = ScriptedPrompter(["cursor", "quality", "cc_refactor"])

    result = run_wizard(
        prompter=prompter,
        project_override=project_with_planfile,
        ide_override=ides,
        project_candidates_override=[],
        create=False,
        use_llx=False,
    )

    assert result.chosen_ide is not None
    assert result.chosen_ide.id == "cursor"
    assert result.path == ["quality", "cc_refactor"]


def test_run_wizard_no_ide_skip_install_continues(
    monkeypatch, project_with_planfile: Path
) -> None:
    from koru.wizard import ide as wizard_ide
    from koru.wizard import orchestrator as wizard_orchestrator

    monkeypatch.setattr(wizard_ide, "discover_installed_ides", lambda: [])
    monkeypatch.setattr(wizard_orchestrator, "discover_installed_ides", lambda: [])
    monkeypatch.setattr(wizard_orchestrator, "detect_terminal_host_ide_id", lambda: None)
    prompter = ScriptedPrompter(["__none", "quality", "cc_refactor"])

    result = run_wizard(
        prompter=prompter,
        project_override=project_with_planfile,
        create=False,
        use_llx=False,
    )

    assert result.chosen_ide is None
    assert result.path == ["quality", "cc_refactor"]


def test_run_wizard_no_ide_install_command_path(monkeypatch, project_with_planfile: Path) -> None:
    from koru.wizard import ide_install as wizard_ide_install
    from koru.wizard import orchestrator as wizard_orchestrator

    monkeypatch.delenv("KORU_AUTOPILOT_INSTANCE", raising=False)
    monkeypatch.delenv("KORU_AUTOPILOT_IDE", raising=False)
    monkeypatch.setattr(wizard_orchestrator, "detect_terminal_host_ide_id", lambda: None)

    state = {"n": 0}

    def fake_discover() -> list[DetectedIDE]:
        state["n"] += 1
        if state["n"] == 1:
            return []
        return [
            DetectedIDE(
                id="vscode",
                label="VS Code",
                running=False,
                pid=None,
                path="/usr/bin/code",
            )
        ]

    executed: list[tuple[str, ...]] = []
    monkeypatch.setattr(wizard_orchestrator, "discover_installed_ides", fake_discover)
    monkeypatch.setattr(wizard_ide_install, "discover_installed_ides", fake_discover)
    monkeypatch.setattr(wizard_ide_install, "_available_install_managers", lambda: {"snap"})
    monkeypatch.setattr(
        wizard_ide_install,
        "_run_install_command",
        lambda argv, _out: executed.append(argv) or True,
    )

    prompter = ScriptedPrompter(
        [
            "install_vscode",
            "install_snap",
            "vscode",
            "quality",
            "cc_refactor",
        ],
        yes_no_answers=[True],
    )
    result = run_wizard(
        prompter=prompter,
        project_override=project_with_planfile,
        create=False,
        use_llx=False,
    )

    assert executed
    assert "snap" in executed[0]
    assert result.chosen_ide is not None
    assert result.chosen_ide.id == "vscode"


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


def test_run_wizard_quick_mode_skips_prompts(project_with_planfile: Path) -> None:
    """--quick must not call ask_choice at all and use the default path."""
    prompter = ScriptedPrompter([])

    result = run_wizard(
        prompter=prompter,
        project_override=project_with_planfile,
        ide_override=[],
        project_candidates_override=[],
        create=True,
        quick=True,
    )

    assert result.quick_mode is True
    assert result.path == ["quality", "cc_refactor"]
    assert result.ticket_id is not None
    assert result.next_steps


def test_run_wizard_quick_with_explicit_strategy(project_with_planfile: Path) -> None:
    prompter = ScriptedPrompter([])

    result = run_wizard(
        prompter=prompter,
        project_override=project_with_planfile,
        ide_override=[],
        project_candidates_override=[],
        create=False,
        quick=True,
        quick_strategy="architecture.ddd",
    )

    assert result.quick_mode is True
    assert result.path == ["architecture", "ddd"]
    assert result.ticket_title.lower().startswith("architektura: wytycz")


def test_run_wizard_quick_invalid_strategy_raises(project_with_planfile: Path) -> None:
    prompter = ScriptedPrompter([])

    with pytest.raises(KeyError, match="no option 'nope'"):
        run_wizard(
            prompter=prompter,
            project_override=project_with_planfile,
            ide_override=[],
            project_candidates_override=[],
            create=False,
            quick=True,
            quick_strategy="architecture.nope",
        )


def test_run_wizard_emits_next_steps(project_with_planfile: Path) -> None:
    prompter = ScriptedPrompter(["quality", "cc_refactor"])

    result = run_wizard(
        prompter=prompter,
        project_override=project_with_planfile,
        ide_override=[],
        project_candidates_override=[],
        create=True,
    )

    assert result.next_steps
    rendered = "\n".join(result.next_steps)
    assert "koru scan" in rendered or "code2llm" in rendered


def test_stdin_prompter_question_mark_shows_help(monkeypatch) -> None:
    from koru.wizard.tree import TreeOption

    options = (
        TreeOption(id="a", label="Option A", help="A is for Apple"),
        TreeOption(id="b", label="Option B", help="B is for Banana"),
    )
    out_buf = io.StringIO()
    p = StdinPrompter(stream_in=io.StringIO("?1\n2\n"), stream_out=out_buf)
    chosen = p.ask_choice("Pick:", options)
    assert chosen.id == "b"
    rendered = out_buf.getvalue()
    assert "A is for Apple" in rendered
    assert "Option A" in rendered


def test_stdin_prompter_question_mark_lists_all_help() -> None:
    from koru.wizard.tree import TreeOption

    options = (
        TreeOption(id="a", label="A", help="apple"),
        TreeOption(id="b", label="B", help="banana"),
    )
    out_buf = io.StringIO()
    p = StdinPrompter(stream_in=io.StringIO("?\n1\n"), stream_out=out_buf)
    p.ask_choice("Pick:", options)
    rendered = out_buf.getvalue()
    assert "apple" in rendered and "banana" in rendered


def test_wizard_cli_bilingual_flag_renders_both_labels(project_with_planfile: Path) -> None:
    """--bilingual must produce labels that include the separator."""
    from koru.wizard.tree import load_tree as _load_tree

    tree = _load_tree(language="pl,en")
    labels = [opt.label for opt in tree.root().options]
    assert any(" · " in label for label in labels)
    assert any("Architektura" in label and "Project" in label for label in labels)


def test_cli_quick_creates_ticket_via_main(tmp_path: Path, monkeypatch) -> None:
    project = tmp_path / "demo"
    project.mkdir()
    (project / ".planfile").mkdir()
    (project / "pyproject.toml").write_text("[project]\nname='demo'\n", encoding="utf-8")
    monkeypatch.chdir(project)

    rc = wizard_main(["--quick", "--project", str(project)])

    assert rc == 0
    sprint = project / ".planfile" / "sprints" / "current.yaml"
    assert sprint.exists()
    import yaml as _yaml

    data = _yaml.safe_load(sprint.read_text(encoding="utf-8"))
    tickets = data["sprint"]["tickets"]
    assert tickets
    first = next(iter(tickets.values()))
    assert "koru-wizard" in first.get("labels", [])
