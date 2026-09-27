"""Tests for the Voice and NLP control bridge in koru."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from koru.global_control import KILLSWITCH_DIR_ENV, KILLSWITCH_ENV
from koru.voice.cli import nlp_main, voice_main
from koru.voice.dispatcher import (
    ParsedVoiceCommand,
    VoiceDispatcher,
    VoiceIntent,
    levenshtein_distance,
    normalize_text,
)
from koru.voice.executor import VoiceCommandExecutor


@pytest.fixture(autouse=True)
def _isolated_control(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Isolate killswitch directory for every test."""
    monkeypatch.setenv(KILLSWITCH_DIR_ENV, str(tmp_path / "koru-control"))
    monkeypatch.delenv(KILLSWITCH_ENV, raising=False)
    monkeypatch.setenv("KORU_AUTO_SHELL_CLIENT", "0")


@pytest.fixture
def sample_project(tmp_path: Path) -> Path:
    """Fixture creating a temporary project with a sample planfile sprint."""
    proj = tmp_path / "sample_proj"
    sprint_dir = proj / ".planfile" / "sprints"
    sprint_dir.mkdir(parents=True, exist_ok=True)
    sprint_data = {
        "sprint": {
            "id": "current",
            "name": "Current",
            "status": "active",
            "tickets": {
                "PLF-001": {
                    "id": "PLF-001",
                    "name": "Implement voice bridge",
                    "status": "in_progress",
                    "priority": "high",
                    "files": ["src/koru/voice/cli.py"],
                },
                "PLF-002": {
                    "id": "PLF-002",
                    "name": "Audit database indexes",
                    "status": "open",
                    "priority": "normal",
                    "files": ["src/db/schema.sql"],
                },
                "PLF-003": {
                    "id": "PLF-003",
                    "name": "Completed legacy task",
                    "status": "closed",
                    "priority": "low",
                    "files": [],
                },
            },
        }
    }
    (sprint_dir / "current.yaml").write_text(yaml.safe_dump(sprint_data), encoding="utf-8")
    return proj


def test_normalization_and_distance() -> None:
    assert normalize_text("  Zatrzymaj pętlę!  ") == "zatrzymaj petle"
    assert normalize_text("Włącz Koru: natychmiast.") == "wlacz koru natychmiast"
    assert normalize_text("WYŁĄCZ KORU") == "wylacz koru"
    assert normalize_text("Zmień stan kolejki...") == "zmien stan kolejki"
    assert levenshtein_distance("zatrzymaj", "zatrzymaj") == 0
    assert levenshtein_distance("zatrzymaj", "zatrzym") == 2
    assert levenshtein_distance("kolejka", "kolejke") == 1


def test_dispatcher_stop_intents() -> None:
    dispatcher = VoiceDispatcher()
    for phrase in [
        "zatrzymaj pętlę",
        "zatrzymaj",
        "stop",
        "wyłącz",
        "wyłącz koru",
        "pause",
        "przerwij",
        "zatrzymaj bo awaria",
    ]:
        parsed = dispatcher.parse(phrase)
        assert parsed.intent == VoiceIntent.STOP_LOOP, f"Failed for '{phrase}'"


def test_dispatcher_start_intents() -> None:
    dispatcher = VoiceDispatcher()
    for phrase in [
        "wznów",
        "uruchom",
        "włącz",
        "włącz koru",
        "start",
        "resume",
        "kontynuuj",
        "dalej",
    ]:
        parsed = dispatcher.parse(phrase)
        assert parsed.intent == VoiceIntent.START_LOOP, f"Failed for '{phrase}'"


def test_dispatcher_status_intents() -> None:
    dispatcher = VoiceDispatcher()
    for phrase in ["status", "stan", "status pętli", "jaki jest stan", "loop status"]:
        parsed = dispatcher.parse(phrase)
        assert parsed.intent == VoiceIntent.STATUS_LOOP, f"Failed for '{phrase}'"


def test_dispatcher_queue_intents() -> None:
    dispatcher = VoiceDispatcher()
    for phrase in ["status kolejki", "pokaż kolejkę", "co w kolejce", "ile zadań", "kolejka"]:
        parsed = dispatcher.parse(phrase)
        assert parsed.intent == VoiceIntent.QUEUE_STATUS, f"Failed for '{phrase}'"


def test_dispatcher_next_task_intents() -> None:
    dispatcher = VoiceDispatcher()
    for phrase in ["następne zadanie", "aktualne zadanie", "co robisz", "next task"]:
        parsed = dispatcher.parse(phrase)
        assert parsed.intent == VoiceIntent.TASK_NEXT, f"Failed for '{phrase}'"


def test_dispatcher_close_task_intents() -> None:
    dispatcher = VoiceDispatcher()
    p1 = dispatcher.parse("zamknij zadanie PLF-001")
    assert p1.intent == VoiceIntent.TASK_CLOSE
    assert p1.arguments["ticket_id"] == "PLF-001"

    p2 = dispatcher.parse("zakończ zadanie ticket-004")
    assert p2.intent == VoiceIntent.TASK_CLOSE
    assert p2.arguments["ticket_id"] == "ticket-004"

    p3 = dispatcher.parse("zamknij zadanie 42")
    assert p3.intent == VoiceIntent.TASK_CLOSE
    assert p3.arguments["ticket_id"] == "PLF-042"


def test_dispatcher_unknown_intent() -> None:
    dispatcher = VoiceDispatcher()
    parsed = dispatcher.parse("jaka jest pogoda dzisiaj")
    assert parsed.intent == VoiceIntent.UNKNOWN


def test_executor_loop_control(sample_project: Path) -> None:
    executor = VoiceCommandExecutor(project_root=sample_project)

    # 1. Check initial status (active)
    stat = executor.execute(ParsedVoiceCommand(VoiceIntent.STATUS_LOOP, "status", "status"))
    assert stat.success is True
    assert stat.data["disabled"] is False

    # 2. Stop loop
    stop = executor.execute(
        ParsedVoiceCommand(VoiceIntent.STOP_LOOP, "zatrzymaj", "zatrzymaj", {"reason": "test stop"})
    )
    assert stop.success is True
    assert "zatrzymana" in stop.message.lower()

    # 3. Check status (stopped)
    stat2 = executor.execute(ParsedVoiceCommand(VoiceIntent.STATUS_LOOP, "status", "status"))
    assert stat2.data["disabled"] is True
    assert "zatrzymana" in stat2.message.lower()

    # 4. Resume loop
    resume = executor.execute(ParsedVoiceCommand(VoiceIntent.START_LOOP, "wznów", "wznow"))
    assert resume.success is True
    assert "wznowiona" in resume.message.lower()

    # 5. Check status (active again)
    stat3 = executor.execute(ParsedVoiceCommand(VoiceIntent.STATUS_LOOP, "status", "status"))
    assert stat3.data["disabled"] is False


def test_executor_queue_and_tasks(sample_project: Path) -> None:
    executor = VoiceCommandExecutor(project_root=sample_project)

    # 1. Queue Status
    q_stat = executor.execute(ParsedVoiceCommand(VoiceIntent.QUEUE_STATUS, "kolejka", "kolejka"))
    assert q_stat.success is True
    assert q_stat.data["total"] == 3
    assert q_stat.data["open_count"] == 2
    assert q_stat.data["in_progress_count"] == 1

    # 2. Next Task
    next_t = executor.execute(ParsedVoiceCommand(VoiceIntent.TASK_NEXT, "następne zadanie", "nastepne zadanie"))
    assert next_t.success is True
    assert next_t.data["ticket"]["id"] == "PLF-001"

    # 3. Close Task
    close_res = executor.execute(
        ParsedVoiceCommand(VoiceIntent.TASK_CLOSE, "zamknij PLF-001", "zamknij plf-001", {"ticket_id": "PLF-001"})
    )
    assert close_res.success is True
    assert close_res.data["status"] == "closed"

    # 4. Verify Next Task moved to PLF-002
    next_t2 = executor.execute(ParsedVoiceCommand(VoiceIntent.TASK_NEXT, "następne zadanie", "nastepne zadanie"))
    assert next_t2.success is True
    assert next_t2.data["ticket"]["id"] == "PLF-002"


def test_cli_voice_and_nlp(sample_project: Path, capsys: pytest.CaptureFixture[str]) -> None:
    # 1. Run 'koru voice "status kolejki" --json'
    code = voice_main(["status kolejki", "--project", str(sample_project), "--json"])
    assert code == 0
    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert payload["intent"] == "queue_status"
    assert payload["success"] is True

    # 2. Run 'koru nlp "zatrzymaj pętlę"'
    code_nlp = nlp_main(["zatrzymaj pętlę", "--project", str(sample_project)])
    assert code_nlp == 0
    captured_nlp = capsys.readouterr()
    assert "zatrzymana" in captured_nlp.out.lower()

    # 3. Run 'koru voice "wznów"'
    code_resume = voice_main(["wznów", "--project", str(sample_project)])
    assert code_resume == 0
    captured_resume = capsys.readouterr()
    assert "wznowiona" in captured_resume.out.lower()
