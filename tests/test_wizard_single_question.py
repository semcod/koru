"""One-question onboarding: wizard caps the interview and auto-picks defaults."""

from __future__ import annotations

from pathlib import Path

import pytest

from koru.autonomous_onboarding import _onboarding_max_questions
from koru.wizard.cli import ScriptedPrompter, run_wizard


@pytest.fixture()
def project_with_planfile(tmp_path: Path) -> Path:
    (tmp_path / ".planfile").mkdir()
    return tmp_path


def test_single_question_auto_picks_leaf(project_with_planfile: Path) -> None:
    # Only the first (area) answer is scripted; deeper levels must auto-pick.
    prompter = ScriptedPrompter(["frontend"])

    result = run_wizard(
        prompter=prompter,
        project_override=project_with_planfile,
        create=False,
        ide_override=[],
        max_questions=1,
    )

    assert result.path[0] == "frontend"
    assert len(result.path) >= 2  # auto-picked at least the leaf
    assert result.ticket_title


def test_full_interview_still_asks_every_level(project_with_planfile: Path) -> None:
    prompter = ScriptedPrompter(["frontend", "design_system"])

    result = run_wizard(
        prompter=prompter,
        project_override=project_with_planfile,
        create=False,
        ide_override=[],
        max_questions=None,
    )

    assert list(result.path[:2]) == ["frontend", "design_system"]


def test_zero_questions_auto_picks_everything(project_with_planfile: Path) -> None:
    prompter = ScriptedPrompter([])  # must never be asked

    result = run_wizard(
        prompter=prompter,
        project_override=project_with_planfile,
        create=False,
        ide_override=[],
        max_questions=0,
    )

    assert result.ticket_title
    assert len(result.path) >= 1


class TestEnvBudget:
    def test_default_is_one(self, monkeypatch):
        monkeypatch.delenv("KORU_ONBOARDING_MAX_QUESTIONS", raising=False)
        assert _onboarding_max_questions() == 1

    def test_explicit_number(self, monkeypatch):
        monkeypatch.setenv("KORU_ONBOARDING_MAX_QUESTIONS", "2")
        assert _onboarding_max_questions() == 2

    def test_all_restores_full_interview(self, monkeypatch):
        monkeypatch.setenv("KORU_ONBOARDING_MAX_QUESTIONS", "all")
        assert _onboarding_max_questions() is None

    def test_negative_means_full_interview(self, monkeypatch):
        monkeypatch.setenv("KORU_ONBOARDING_MAX_QUESTIONS", "-1")
        assert _onboarding_max_questions() is None

    def test_garbage_falls_back_to_one(self, monkeypatch):
        monkeypatch.setenv("KORU_ONBOARDING_MAX_QUESTIONS", "banana")
        assert _onboarding_max_questions() == 1
