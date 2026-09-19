"""Tests for koru.autonomy.monag_discovery."""

from __future__ import annotations

import json
import subprocess
from collections.abc import Sequence
from pathlib import Path

import pytest
import yaml

import koru.queue.ticket
from koru.autonomy import monag_discovery as md


def _write_sprint(project: Path, sprint: str, tickets: dict[str, str]) -> None:
    path = project / ".planfile" / "sprints" / f"{sprint}.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {"sprint": {"tickets": {key: {"id": key, "status": status} for key, status in tickets.items()}}}
    path.write_text(yaml.safe_dump(data), encoding="utf-8")


def _remaining(
    project: Path, ticket_id: str, *, sprint: str = "backlog", status: str = "open", priority: str = "high",
) -> dict:
    return {
        "id": ticket_id,
        "status": status,
        "title": ticket_id,
        "priority": priority,
        "source": str(project / ".planfile" / "sprints" / f"{sprint}.yaml"),
        "priority_conflict": False,
    }


def _resume(project: Path, tickets: list[dict], checkouts: list[dict] | None = None) -> str:
    return json.dumps(
        {
            "schema": "monag.resume/v1",
            "projects": [
                {
                    "path": str(project),
                    "checkouts": checkouts or [],
                    "planfile": {"remaining": len(tickets), "remaining_tickets": tickets},
                },
            ],
        },
    )


class _Runner:
    def __init__(self, resume_stdout: str, *, resume_rc: int = 0, move_rc: int = 0) -> None:
        self.resume_stdout = resume_stdout
        self.resume_rc = resume_rc
        self.move_rc = move_rc
        self.calls: list[list[str]] = []

    def __call__(self, cmd: Sequence[str], cwd: Path) -> subprocess.CompletedProcess[str]:
        self.calls.append(list(cmd))
        if "resume" in cmd:
            return subprocess.CompletedProcess(list(cmd), self.resume_rc, stdout=self.resume_stdout, stderr="boom")
        return subprocess.CompletedProcess(list(cmd), self.move_rc, stdout="", stderr="move failed")

    @property
    def moves(self) -> list[str]:
        return [call[3] for call in self.calls if call[:2] == ["planfile", "ticket"] and call[2] == "move"]


@pytest.fixture()
def project(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monag = tmp_path / "bin" / "monag"
    monag.parent.mkdir()
    monag.write_text("#!/bin/sh\n", encoding="utf-8")
    for name in ("KORU_MONAG_ENABLE", "KORU_MONAG_SPRINTS", "KORU_MONAG_MAX_PROMOTIONS"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("KORU_MONAG_BIN", str(monag))
    monkeypatch.setattr(koru.queue.ticket, "resolve_planfile_base_command", lambda _project: ["planfile"])
    root = tmp_path / "repo"
    root.mkdir()
    return root.resolve()


def test_promotes_open_backlog_tickets_in_monag_order_up_to_limit(
    project: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("KORU_MONAG_MAX_PROMOTIONS", "2")
    _write_sprint(project, "backlog", {"PLF-1": "open", "PLF-2": "open", "PLF-3": "open"})
    _write_sprint(project, "current", {})
    tickets = [_remaining(project, "PLF-2"), _remaining(project, "PLF-1"), _remaining(project, "PLF-3")]
    runner = _Runner(_resume(project, tickets))

    outcome = md.run_monag_discovery(project, runner=runner)

    assert outcome.error is None and outcome.ran
    assert runner.calls[0][1:] == ["--root", str(project), "--json", "resume"]
    assert runner.moves == ["PLF-2", "PLF-1"]
    assert outcome.promoted_ids == ["PLF-2", "PLF-1"]
    assert outcome.to_dict()["applied"] == ["PLF-2", "PLF-1"]


def test_rejects_ambiguous_or_foreign_tickets(project: Path) -> None:
    _write_sprint(project, "backlog", {"DUP": "open", "CONFLICT": "open", "STALE": "done", "OK": "open"})
    _write_sprint(project, "current", {"DUP": "open"})
    worktree_copy = _remaining(project, "WT")
    worktree_copy["source"] = str(project / ".worktrees" / "ticket-001--x" / ".planfile" / "sprints" / "backlog.yaml")
    legacy = _remaining(project, "LEGACY")
    legacy["source"] = str(project / "planfile.yaml")
    runner = _Runner(
        _resume(
            project,
            [
                _remaining(project, "DUP"),
                _remaining(project, "CONFLICT", status="done/open"),
                _remaining(project, "STALE"),
                _remaining(project, "CURRENT", sprint="current"),
                worktree_copy,
                legacy,
                _remaining(project, "OK", priority="low"),
            ],
        ),
    )

    outcome = md.run_monag_discovery(project, runner=runner)

    assert runner.moves == ["OK"]
    assert outcome.promoted_ids == ["OK"]
    assert outcome.skipped_ids == ["DUP", "CONFLICT", "STALE"]


def test_failed_move_is_reported_as_skipped(project: Path) -> None:
    _write_sprint(project, "backlog", {"PLF-1": "open"})
    runner = _Runner(_resume(project, [_remaining(project, "PLF-1")]), move_rc=1)

    outcome = md.run_monag_discovery(project, runner=runner)

    assert outcome.promoted_ids == []
    assert outcome.skipped_ids == ["PLF-1"]


def test_configured_sprints_never_include_current(project: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("KORU_MONAG_SPRINTS", "current, audit")
    _write_sprint(project, "audit", {"A-1": "open"})
    _write_sprint(project, "backlog", {"B-1": "open"})
    runner = _Runner(_resume(project, [_remaining(project, "A-1", sprint="audit"), _remaining(project, "B-1")]))

    outcome = md.run_monag_discovery(project, runner=runner)

    assert outcome.promoted_ids == ["A-1"]


def test_unfinished_ticket_worktrees_are_reported_without_effects(project: Path) -> None:
    checkouts = [
        {"path": str(project), "ticket": None, "unfinished": True, "stage": "modified"},
        {
            "path": str(project / ".worktrees" / "ticket-007--x"),
            "ticket": "ticket-007",
            "unfinished": True,
            "stage": "unmerged commits",
            "readiness": "review ownership",
            "lease_status": "unknown",
        },
    ]
    runner = _Runner(_resume(project, [], checkouts))

    outcome = md.run_monag_discovery(project, runner=runner)

    assert runner.moves == []
    assert [row["ticket"] for row in outcome.unfinished_worktrees] == ["ticket-007"]
    lines = md.format_unfinished_worktrees(outcome)
    assert lines and "ticket-007" in lines[0] and "lease=unknown" in lines[0]
    assert "unfinished_worktrees=1" in md.format_monag_summary(outcome)


@pytest.mark.parametrize(
    ("setup", "expected"),
    [
        ({"env": {"KORU_MONAG_ENABLE": "0"}}, "disabled via KORU_MONAG_ENABLE"),
        ({"bin": "missing"}, "monag not on PATH (set KORU_MONAG_BIN)"),
    ],
)
def test_skips_without_running_when_unavailable(
    project: Path, monkeypatch: pytest.MonkeyPatch, setup: dict, expected: str,
) -> None:
    for name, value in setup.get("env", {}).items():
        monkeypatch.setenv(name, value)
    if setup.get("bin"):
        monkeypatch.setenv("KORU_MONAG_BIN", str(project / "absent-monag"))
    runner = _Runner("{}")

    outcome = md.run_monag_discovery(project, runner=runner)

    assert runner.calls == []
    assert not outcome.ran and outcome.skipped_reason == expected
    assert md.format_monag_summary(outcome).endswith(expected)


def test_errors_never_promote(project: Path) -> None:
    _write_sprint(project, "backlog", {"PLF-1": "open"})
    cases = [
        _Runner(_resume(project, [_remaining(project, "PLF-1")]), resume_rc=2),
        _Runner("not json"),
        _Runner(_resume(project.parent / "other", [_remaining(project, "PLF-1")])),
    ]
    errors = []
    for runner in cases:
        outcome = md.run_monag_discovery(project, runner=runner)
        assert runner.moves == [] and outcome.promoted_ids == []
        errors.append(outcome.error)
    assert errors == ["boom", "monag produced no parseable resume JSON", "monag resume did not report this project"]


def test_timeout_is_an_error(project: Path) -> None:
    def runner(cmd: Sequence[str], cwd: Path) -> subprocess.CompletedProcess[str]:
        raise subprocess.TimeoutExpired(cmd, 60)

    outcome = md.run_monag_discovery(project, runner=runner)

    assert outcome.error == "monag timed out after 60s"
    assert outcome.monag_duration_s is not None
