from __future__ import annotations

import json
from argparse import Namespace
from pathlib import Path
from types import SimpleNamespace

from koru import autonomous_onboarding as onboarding
from koru.wizard.ide import DetectedIDE


def test_should_run_interactive_onboarding_for_auto_tty(monkeypatch) -> None:
    args = Namespace(
        action="up",
        onboarding=None,
        emit_events="human",
        _invoked_as_auto=True,
    )
    monkeypatch.setattr(onboarding.sys, "stdin", SimpleNamespace(isatty=lambda: True))
    monkeypatch.setattr(onboarding.sys, "stdout", SimpleNamespace(isatty=lambda: True))
    assert onboarding.should_run_interactive_onboarding(args) is True


def test_should_not_run_interactive_onboarding_when_not_auto(monkeypatch) -> None:
    args = Namespace(
        action="up",
        onboarding=None,
        emit_events="human",
        _invoked_as_auto=False,
    )
    monkeypatch.setattr(onboarding.sys, "stdin", SimpleNamespace(isatty=lambda: True))
    monkeypatch.setattr(onboarding.sys, "stdout", SimpleNamespace(isatty=lambda: True))
    assert onboarding.should_run_interactive_onboarding(args) is False


def test_should_not_run_interactive_onboarding_when_project_has_koru_dir(
    monkeypatch, tmp_path: Path
) -> None:
    (tmp_path / ".koru").mkdir()
    args = Namespace(
        action="up",
        onboarding=None,
        emit_events="human",
        _invoked_as_auto=True,
        project=tmp_path,
    )
    monkeypatch.setattr(onboarding.sys, "stdin", SimpleNamespace(isatty=lambda: True))
    monkeypatch.setattr(onboarding.sys, "stdout", SimpleNamespace(isatty=lambda: True))

    assert onboarding.should_run_interactive_onboarding(args) is False


def test_should_not_run_interactive_onboarding_when_project_has_legacy_runtime_dir(
    monkeypatch, tmp_path: Path
) -> None:
    (tmp_path / ".planfile" / ".koru").mkdir(parents=True)
    args = Namespace(
        action="up",
        onboarding=None,
        emit_events="human",
        _invoked_as_auto=True,
        project=tmp_path,
    )
    monkeypatch.setattr(onboarding.sys, "stdin", SimpleNamespace(isatty=lambda: True))
    monkeypatch.setattr(onboarding.sys, "stdout", SimpleNamespace(isatty=lambda: True))

    assert onboarding.should_run_interactive_onboarding(args) is False


def test_explicit_onboarding_ignores_existing_project_koru_dir(
    monkeypatch, tmp_path: Path
) -> None:
    (tmp_path / ".koru").mkdir()
    args = Namespace(
        action="up",
        onboarding=True,
        emit_events="human",
        _invoked_as_auto=True,
        project=tmp_path,
    )
    monkeypatch.setattr(onboarding.sys, "stdin", SimpleNamespace(isatty=lambda: True))
    monkeypatch.setattr(onboarding.sys, "stdout", SimpleNamespace(isatty=lambda: True))

    assert onboarding.should_run_interactive_onboarding(args) is True


def test_ensure_project_state_writes_project_metadata(tmp_path: Path) -> None:
    onboarding.ensure_project_state(tmp_path, source="test")

    data = json.loads((tmp_path / ".koru" / "project.json").read_text(encoding="utf-8"))
    assert data["schema"] == "koru.project/v1"
    assert data["runtime_dir"] == ".planfile/.koru"
    assert data["source"] == "test"


def test_discover_ide_candidates_delegates_to_wizard(monkeypatch) -> None:
    expected = [
        DetectedIDE(
            id="vscode",
            label="VS Code",
            running=False,
            pid=None,
            path="/usr/bin/code",
        )
    ]
    monkeypatch.setattr(onboarding, "discover_installed_ides", lambda: expected)
    assert onboarding.discover_ide_candidates() == expected


def test_load_strategy_tree_prefers_project_override(tmp_path: Path) -> None:
    custom = tmp_path / ".koru" / "strategies.json"
    custom.parent.mkdir(parents=True)
    custom.write_text(
        """
{
  "version": 1,
  "root": "root",
  "language_default": "pl",
  "nodes": {
    "root": {
      "prompt": "root?",
      "options": [{"id": "go", "label": "go", "ticket": "t1"}]
    }
  },
  "tickets": {
    "t1": {
      "title": "ticket",
      "body": "body"
    }
  }
}
""".strip(),
        encoding="utf-8",
    )

    tree = onboarding.load_strategy_tree(tmp_path)
    assert tree.root_id == "root"
    assert tree.ticket("t1").title == "ticket"


def test_run_interactive_onboarding_updates_args_from_wizard(monkeypatch, tmp_path: Path) -> None:
    args = Namespace(
        action="up",
        onboarding=True,
        emit_events="human",
        _invoked_as_auto=True,
        project=tmp_path,
        autopilot_ide="auto",
        agent_lane="auto",
        queue_name="default",
    )

    monkeypatch.setattr(onboarding.sys, "stdin", SimpleNamespace(isatty=lambda: True))
    monkeypatch.setattr(onboarding.sys, "stdout", SimpleNamespace(isatty=lambda: True))
    monkeypatch.setattr(onboarding, "llx_available", lambda: False)

    chosen_project = tmp_path.resolve()
    wizard_result = SimpleNamespace(
        chosen_ide=DetectedIDE(
            id="vscode",
            label="VS Code",
            running=True,
            pid=11,
            path="/usr/bin/code",
        ),
        chosen_project=chosen_project,
        path=["quality", "cc_refactor"],
        ticket_id="PLF-001",
        ticket_title="Quality: reduce complexity",
    )
    wizard_kwargs: dict[str, object] = {}

    def fake_run_wizard(**kwargs):
        wizard_kwargs.update(kwargs)
        return wizard_result

    monkeypatch.setattr(onboarding, "run_wizard", fake_run_wizard)

    logs: list[str] = []
    out = onboarding.run_interactive_onboarding(
        args,
        stdio_info=logs.append,
    )

    assert out is not None
    assert args.autopilot_ide == "vscode"
    assert args.agent_lane == "vscode"
    assert args.project == chosen_project
    assert out.created_ticket_id == "PLF-001"
    assert out.strategy_path == ("quality", "cc_refactor")
    assert wizard_kwargs["project_override"] == tmp_path.resolve()
    assert any("created ticket" in line for line in logs)

    state = json.loads((chosen_project / ".koru" / "onboarding.json").read_text(encoding="utf-8"))
    assert state["schema"] == "koru.onboarding/v1"
    assert state["selected_ide"] == "vscode"
    assert state["created_ticket_id"] == "PLF-001"
    history = (chosen_project / ".koru" / "history.jsonl").read_text(encoding="utf-8")
    assert "onboarding.completed" in history
