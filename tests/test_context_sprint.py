"""Unit tests for extracted koru.context_sprint module."""

from __future__ import annotations

from pathlib import Path

from koru.context_sprint import (
    _SPRINT_YAML_CACHE,
    _auto_promote_blocking_tickets,
    _fast_yaml_load,
    _find_blocking_tickets,
    _load_sprint_data,
    _promote_blocking_to_critical,
    _promote_bug_priority,
    _write_sprint_data,
)


def test_find_blocking_tickets() -> None:
    tickets = {
        "PLF-01": {"id": "PLF-01", "blocked_by": "PLF-02"},
        "PLF-02": {"id": "PLF-02", "blocked_by": ["PLF-03", "PLF-04"]},
        "PLF-03": {"id": "PLF-03", "blocked_by": []},
    }
    blocking = _find_blocking_tickets(tickets)
    assert blocking == {"PLF-02", "PLF-03", "PLF-04"}


def test_promote_blocking_to_critical() -> None:
    tickets = {
        "PLF-01": {"id": "PLF-01", "priority": "normal"},
        "PLF-02": {"id": "PLF-02", "priority": "critical"},
    }
    promoted = _promote_blocking_to_critical(tickets, {"PLF-01", "PLF-02"})
    assert promoted is True
    assert tickets["PLF-01"]["priority"] == "critical"
    assert tickets["PLF-02"]["priority"] == "critical"


def test_promote_bug_priority() -> None:
    tickets = {
        "PLF-01": {"id": "PLF-01", "priority": "normal", "labels": ["bug"], "status": "open"},
        "PLF-02": {"id": "PLF-02", "priority": "low", "labels": ["bug"], "status": "ready"},
        "PLF-03": {"id": "PLF-03", "priority": "high", "labels": ["feature"], "status": "open"},
    }
    promoted = _promote_bug_priority(tickets)
    assert promoted is True
    assert tickets["PLF-01"]["priority"] == "high"
    assert tickets["PLF-02"]["priority"] == "normal"
    assert tickets["PLF-03"]["priority"] == "high"


def test_sprint_yaml_cache_and_io(tmp_path: Path) -> None:
    sprints_dir = tmp_path / ".planfile" / "sprints"
    sprints_dir.mkdir(parents=True)
    current_yaml = sprints_dir / "current.yaml"

    data = {
        "sprint": {
            "name": "current",
            "tickets": {
                "PLF-10": {
                    "id": "PLF-10",
                    "priority": "normal",
                    "blocked_by": ["PLF-11"],
                },
                "PLF-11": {
                    "id": "PLF-11",
                    "priority": "normal",
                },
            },
        }
    }
    _write_sprint_data(tmp_path, data)
    assert current_yaml.is_file()

    loaded = _load_sprint_data(tmp_path)
    assert loaded is not None
    assert "tickets" in loaded["sprint"]

    # Verify cached
    key = str(current_yaml)
    assert key in _SPRINT_YAML_CACHE

    # Auto promote
    _auto_promote_blocking_tickets(tmp_path)
    updated = _fast_yaml_load(current_yaml)
    assert updated["sprint"]["tickets"]["PLF-11"]["priority"] == "critical"
