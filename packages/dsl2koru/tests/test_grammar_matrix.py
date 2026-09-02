from __future__ import annotations

from typing import Any

import pytest
from dsl2koru.grammar import parse_line, to_text
from dsl2koru.schema_registry import all_verbs

CASES: list[tuple[str, dict[str, str], dict[str, Any], str]] = [
    ("AUTO workspace", {}, {"verb": "AUTO", "target": "workspace"}, "AUTO workspace"),
    (
        "CALIBRATION --skip-fix --skip-desktop --probe-prompt ready",
        {},
        {"verb": "CALIBRATION", "skip_fix": True, "skip_desktop": True, "probe_prompt": "ready"},
        "CALIBRATION --skip-fix --skip-desktop --probe-prompt ready",
    ),
    (
        "CHAT --llm --shell bash --single-action",
        {},
        {"verb": "CHAT", "llm": True, "shell": "bash", "single_action": True},
        "CHAT --llm --shell bash --single-action",
    ),
    (
        "DOCTOR --fix --probe --probe-prompt ready",
        {},
        {"verb": "DOCTOR", "fix": True, "probe": True, "probe_prompt": "ready"},
        "DOCTOR --fix --probe --probe-prompt ready",
    ),
    ("ENSURE --install", {}, {"verb": "ENSURE", "install": True}, "ENSURE --install"),
    ("ENV", {"default_file": "koru.env"}, {"verb": "ENV", "file": "koru.env"}, "ENV --file koru.env"),
    (
        "LANE --ide cursor --instance primary --file lane.json",
        {},
        {"verb": "LANE", "ide": "cursor", "instance": "primary", "file": "lane.json"},
        "LANE --ide cursor --instance primary --file lane.json",
    ),
    ("QUERY current state", {}, {"verb": "QUERY", "target": "current state"}, "QUERY current state"),
    (
        "QUERY_LANE_STATUS IDE cursor INSTANCE primary",
        {},
        {"verb": "QUERY_LANE_STATUS", "ide": "cursor", "instance": "primary"},
        "QUERY_LANE_STATUS IDE cursor INSTANCE primary",
    ),
    (
        "QUERY_REPAIR_HISTORY PROJECT /repo LIMIT 3 CODE E_TEST",
        {},
        {"verb": "QUERY_REPAIR_HISTORY", "project": "/repo", "limit": 3, "code": "E_TEST"},
        "QUERY_REPAIR_HISTORY PROJECT /repo LIMIT 3 CODE E_TEST",
    ),
    ("REPAIR_HISTORY", {}, {"verb": "REPAIR_HISTORY"}, "REPAIR_HISTORY"),
    (
        "REPAIR_RUN IDE cursor INSTANCE primary PROJECT /repo",
        {},
        {
            "verb": "REPAIR_RUN",
            "ide": "cursor",
            "instance": "primary",
            "project": "/repo",
            "trigger": "manual",
        },
        "REPAIR_RUN IDE cursor INSTANCE primary PROJECT /repo",
    ),
    (
        'RESOLVE "fix the build" PROJECT /repo',
        {},
        {"verb": "RESOLVE", "prompt": "fix the build", "project": "/repo"},
        'RESOLVE "fix the build" PROJECT /repo',
    ),
    ("STATUS --probe", {}, {"verb": "STATUS", "probe": True}, "STATUS --probe"),
    ("SYNC --all-ides", {}, {"verb": "SYNC", "all_ides": True}, "SYNC --all-ides"),
    (
        "TEXT continue --llm --single-action",
        {},
        {"verb": "TEXT", "target": "continue", "llm": True, "single_action": True},
        "TEXT continue --llm --single-action",
    ),
    (
        "UI_CAPTURE IMAGE shot.png WINDOW main EXECUTE 0",
        {},
        {"verb": "UI_CAPTURE", "image": "shot.png", "window": "main", "execute": False},
        "UI_CAPTURE --image shot.png --window main EXECUTE 0",
    ),
    (
        'UI_CLICK "save button" IMAGE shot.png',
        {},
        {"verb": "UI_CLICK", "image": "shot.png", "execute": True, "target": "save button"},
        'UI_CLICK --image shot.png "save button"',
    ),
    ("UI_KEY ctrl+s", {}, {"verb": "UI_KEY", "execute": True, "keys": "ctrl+s"}, "UI_KEY ctrl+s"),
    (
        'UI_NL "click save"',
        {},
        {"verb": "UI_NL", "execute": True, "prompt": "click save"},
        'UI_NL "click save"',
    ),
    (
        'UI_TYPE "hello" IN "chat box" WINDOW main',
        {},
        {"verb": "UI_TYPE", "window": "main", "execute": True, "value": "hello", "field": "chat box"},
        'UI_TYPE --window main "hello" IN "chat box"',
    ),
    (
        "VALIDATE_LANE IDE cursor INSTANCE primary",
        {},
        {"verb": "VALIDATE_LANE", "ide": "cursor", "instance": "primary"},
        "VALIDATE_LANE IDE cursor INSTANCE primary",
    ),
]


def test_matrix_covers_every_schema_verb() -> None:
    assert {expected["verb"] for _, _, expected, _ in CASES} == set(all_verbs())


@pytest.mark.parametrize(("line", "context", "expected", "canonical"), CASES)
def test_all_verb_parse_serialize_matrix(
    line: str,
    context: dict[str, str],
    expected: dict[str, Any],
    canonical: str,
) -> None:
    payload = parse_line(line, **context)
    assert payload == expected
    assert to_text(payload) == canonical
    assert parse_line(canonical) == expected


@pytest.mark.parametrize(
    ("line", "context", "expected"),
    [
        ("DIAGNOSE --probe", {}, {"verb": "STATUS", "probe": True}),
        ("AUTONOMOUS workspace", {}, {"verb": "AUTO", "target": "workspace"}),
        ("ASK --llm", {}, {"verb": "CHAT", "llm": True}),
        (
            "LANE_STATUS --ide cursor",
            {},
            {"verb": "LANE", "lane_status": True, "ide": "cursor"},
        ),
        ("REPAIR --fix --ide cursor", {}, {"verb": "REPAIR_RUN", "fix": True, "ide": "cursor"}),
        ("ENVFILE", {"default_file": "koru.env"}, {"verb": "ENV", "file": "koru.env"}),
    ],
)
def test_compatibility_aliases(line: str, context: dict[str, str], expected: dict[str, Any]) -> None:
    assert parse_line(line, **context) == expected


def test_empty_comment_and_unknown_input() -> None:
    assert parse_line("") == {}
    assert parse_line("  # ignored") == {}
    with pytest.raises(ValueError, match="unknown DSL verb"):
        parse_line("UNKNOWN")
