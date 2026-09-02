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
