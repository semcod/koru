"""Tests for koru.autonomy.ticket2dsl."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from koru.autonomy import ticket2dsl as t2d


def _write_sprint(project: Path, tickets: dict) -> None:
    sprint_dir = project / ".planfile" / "sprints"
    sprint_dir.mkdir(parents=True)
    (sprint_dir / "current.yaml").write_text(
        yaml.safe_dump({"sprint": {"id": "current", "tickets": tickets}}),
        encoding="utf-8",
    )


def test_skips_without_sprint(tmp_path: Path) -> None:
    outcome = t2d.run_ticket2dsl(tmp_path)
    assert outcome.ran is False
    assert "no planfile sprint" in (outcome.skipped_reason or "")


def test_builds_units_for_useful_tickets_only(tmp_path: Path) -> None:
    _write_sprint(
        tmp_path,
        {
            "PLF-1": {
                "name": "[todo2code] Implement rate limiter",
                "status": "open",
                "priority": "high",
                "files": ["src/rate.py"],
                "description": "Add rate limiter",
                "source": {
                    "tool": "koru-todo2code-discovery",
                    "context": {
                        "plan_id": "CPLAN-abc",
                        "plan_hash": "a" * 64,
                        "diagnostic_ids": ["DIAG-1"],
                    },
                },
            },
            "PLF-2": {
                "name": "[todo2code] Fix vendored",
                "status": "open",
                "files": [".testvenv/lib/site-packages/x.py"],
                "source": {"tool": "koru-todo2code-discovery", "context": {}},
            },
            "PLF-3": {
                "name": "Done ticket",
                "status": "done",
                "files": ["src/done.py"],
            },
        },
    )
    outcome = t2d.run_ticket2dsl(tmp_path, max_units=10)
    assert outcome.ran is True
    assert outcome.units_count == 1
    assert outcome.ticket_ids == ["PLF-1"]
    assert outcome.filtered_out_count >= 1
    assert outcome.json_path and Path(outcome.json_path).is_file()
    assert outcome.dsl_path and Path(outcome.dsl_path).is_file()
    assert outcome.intent_path and Path(outcome.intent_path).is_file()

    payload = json.loads(Path(outcome.json_path).read_text(encoding="utf-8"))
    assert payload["schemaVersion"] == "koru.ticket-work-unit-set/v1"
    unit = payload["units"][0]
    assert unit["paths"] == ["src/rate.py"]
    assert unit["planId"] == "CPLAN-abc"
    dsl = Path(outcome.dsl_path).read_text(encoding="utf-8")
    assert "start ticket PLF-1" in dsl
    assert "done ticket PLF-1" in dsl


def test_disabled_via_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("KORU_TICKET2DSL_ENABLE", "0")
    _write_sprint(
        tmp_path,
        {"PLF-1": {"name": "x", "status": "open", "files": ["src/a.py"]}},
    )
    outcome = t2d.run_ticket2dsl(tmp_path)
    assert outcome.ran is False
    assert "disabled" in (outcome.skipped_reason or "")
