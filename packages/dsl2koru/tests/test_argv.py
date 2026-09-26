"""Pin ``to_cli_args`` argv construction for every dispatched verb."""

from __future__ import annotations

import pytest
from dsl2koru.handlers.argv import to_cli_args


@pytest.mark.parametrize(
    ("payload", "expected"),
    [
        # TEXT: without a target it degrades to status.
        ({"verb": "TEXT", "target": ""}, ["status"]),
        (
            {"verb": "TEXT", "target": "continue"},
            ["text", "continue"],
        ),
        (
            {"verb": "TEXT", "target": "continue", "llm": True},
            ["text", "continue", "--llm"],
        ),
        (
            {"verb": "TEXT", "target": "continue", "shell": "bash"},
            ["text", "continue", "--shell", "bash"],
        ),
        (
            {
                "verb": "TEXT",
                "target": "continue",
                "llm": True,
                "shell": "bash",
                "single_action": True,
            },
            ["text", "continue", "--llm", "--shell", "bash", "--single-action"],
        ),
        ({"verb": "CHAT"}, ["chat"]),
        (
            {"verb": "CHAT", "llm": True, "shell": "sh", "single_action": True},
            ["chat", "--llm", "--shell", "sh", "--single-action"],
        ),
        ({"verb": "AUTO"}, ["auto"]),
        (
            {"verb": "AUTO", "shell": "bash", "auto_args": "--llm -q"},
            ["auto", "--shell", "bash", "--llm", "-q"],
        ),
        (
            {"verb": "AUTO", "auto_args": ["--count", 2]},
            ["auto", "--count", "2"],
        ),
        ({"verb": "ENSURE"}, ["ensure"]),
        ({"verb": "ENSURE", "install": True}, ["ensure", "--install"]),
        ({"verb": "LANE"}, ["lane"]),
        ({"verb": "LANE", "ide": "vscode", "instance": "default"}, ["lane", "vscode", "default"]),
        ({"verb": "LANE", "lane_status": True, "ide": "vscode"}, ["lane-status", "vscode"]),
        ({"verb": "STATUS"}, ["status"]),
        ({"verb": "STATUS", "probe": True}, ["status", "--probe"]),
        ({"verb": "DOCTOR"}, ["doctor"]),
        ({"verb": "DOCTOR", "fix": True}, ["doctor", "--fix"]),
        (
            {"verb": "DOCTOR", "fix": True, "probe": True, "probe_prompt": "ready"},
            ["doctor", "--fix", "--probe", "--probe-prompt", "ready"],
        ),
        ({"verb": "CALIBRATION"}, ["calibration"]),
        (
            {
                "verb": "CALIBRATION",
                "skip_fix": True,
                "skip_desktop": True,
                "skip_bridge": True,
            },
            ["calibration", "--skip-fix", "--skip-desktop", "--skip-bridge"],
        ),
        (
            {"verb": "CALIBRATION", "skip_fix": True, "probe_prompt": "ready"},
            ["calibration", "--skip-fix", "--probe-prompt", "ready"],
        ),
        ({"verb": "REPAIR_RUN"}, ["repair", "run"]),
        (
            {"verb": "REPAIR_RUN", "fix": True, "ide": "vscode", "instance": "default"},
            ["repair", "run", "--fix", "vscode", "default"],
        ),
        ({"verb": "REPAIR_HISTORY"}, ["repair", "history"]),
        ({"verb": "SYNC"}, ["sync"]),
        ({"verb": "SYNC", "all_ides": True}, ["sync", "--all-ides"]),
        ({"verb": "ENV"}, ["env"]),
        ({"verb": "ENV", "file": "a.env"}, ["env", "--file", "a.env"]),
        ({"verb": "ENV", "default_file": "b.env"}, ["env", "--file", "b.env"]),
        ({"verb": "QUERY", "target": "lane"}, ["lane"]),
        ({"verb": "QUERY", "target": "Lane-Status"}, ["lane"]),
        ({"verb": "QUERY", "target": "AUTO"}, ["auto"]),
        ({"verb": "QUERY", "target": "other"}, ["status"]),
    ],
)
def test_to_cli_args(payload: dict[str, object], expected: list[str]) -> None:
    assert to_cli_args(payload) == expected


def test_unknown_verb_falls_back_to_text() -> None:
    assert to_cli_args({"verb": "SOMETHING", "target": "x"}) == ["text", "SOMETHING x"]
    assert to_cli_args({"verb": "SOMETHING"}) == ["text", "SOMETHING"]
