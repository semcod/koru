"""Tests for planfile ticket selection in koru queue."""

from __future__ import annotations

import json

from koru.queue.ticket import parse_next_ticket


def test_parse_next_ticket_skips_operator_human_when_not_interactive() -> None:
    tickets = [
        {
            "id": "REFACTOR-005",
            "status": "open",
            "priority": "high",
            "executor": {"kind": "human"},
            "execution": {"queue": "operator"},
            "labels": ["operator"],
        },
        {
            "id": "REFACTOR-006",
            "status": "open",
            "priority": "normal",
            "executor": {"kind": "shell", "handler": "echo ok"},
            "execution": {"queue": "default"},
        },
    ]

    picked = parse_next_ticket(json.dumps(tickets), interactive=False)

    assert picked is not None
    assert picked["id"] == "REFACTOR-006"


def test_parse_next_ticket_keeps_operator_human_when_interactive() -> None:
    tickets = [
        {
            "id": "REFACTOR-005",
            "status": "open",
            "priority": "high",
            "executor": {"kind": "human"},
            "execution": {"queue": "operator"},
        }
    ]

    picked = parse_next_ticket(json.dumps(tickets), interactive=True)

    assert picked is not None
    assert picked["id"] == "REFACTOR-005"


def test_parse_next_ticket_defers_human_behind_runnable_work() -> None:
    """A human ticket must not stall the drain while llm/shell work remains."""
    tickets = [
        {
            "id": "REFACTOR-010",
            "status": "open",
            "priority": "critical",
            "created_at": "2026-01-01",
            "executor": {"kind": "human"},
            "execution": {"queue": "default"},
        },
        {
            "id": "REFACTOR-011",
            "status": "open",
            "priority": "low",
            "created_at": "2026-02-01",
            "executor": {"kind": "llm"},
            "inputs": {"prompt": "do it"},
            "execution": {"queue": "default"},
        },
    ]

    picked = parse_next_ticket(json.dumps(tickets), interactive=False)

    assert picked is not None
    assert picked["id"] == "REFACTOR-011"


def test_parse_next_ticket_returns_human_when_nothing_else_runnable() -> None:
    tickets = [
        {
            "id": "REFACTOR-012",
            "status": "open",
            "priority": "normal",
            "executor": {"kind": "human"},
            "execution": {"queue": "default"},
        },
    ]

    picked = parse_next_ticket(json.dumps(tickets), interactive=False)

    assert picked is not None
    assert picked["id"] == "REFACTOR-012"


def test_parse_next_ticket_defers_missing_executor_as_human() -> None:
    """A ticket without executor.kind resolves to human and must defer too."""
    tickets = [
        {
            "id": "REFACTOR-013",
            "status": "open",
            "priority": "high",
            "created_at": "2026-01-01",
            "execution": {"queue": "default"},
        },
        {
            "id": "REFACTOR-014",
            "status": "open",
            "priority": "normal",
            "created_at": "2026-02-01",
            "executor": {"kind": "shell", "handler": "echo ok"},
            "execution": {"queue": "default"},
        },
    ]

    picked = parse_next_ticket(json.dumps(tickets), interactive=False)

    assert picked is not None
    assert picked["id"] == "REFACTOR-014"


def test_parse_next_ticket_keeps_human_first_when_interactive() -> None:
    tickets = [
        {
            "id": "REFACTOR-015",
            "status": "open",
            "priority": "critical",
            "created_at": "2026-01-01",
            "executor": {"kind": "human"},
            "execution": {"queue": "default"},
        },
        {
            "id": "REFACTOR-016",
            "status": "open",
            "priority": "low",
            "created_at": "2026-02-01",
            "executor": {"kind": "shell", "handler": "echo ok"},
            "execution": {"queue": "default"},
        },
    ]

    picked = parse_next_ticket(json.dumps(tickets), interactive=True)

    assert picked is not None
    assert picked["id"] == "REFACTOR-015"
