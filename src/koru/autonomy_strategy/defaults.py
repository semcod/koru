"""Default autonomy strategy embedded into project ``koru.yaml``."""

from __future__ import annotations

from typing import Any

import yaml

DEFAULT_AUTONOMY_STRATEGY: dict[str, Any] = {
    "schema": "1.0",
    "id": "accordion_detail_to_general",
    "description": (
        "Default autonomy rhythm: execute concrete planfile tickets first; "
        "when the queue is empty, broaden to whole-project discovery and "
        "turn findings back into focused planfile tickets."
    ),
    "source_of_truth": "planfile",
    "default_pipeline": {
        "order": [
            "planfile_queue",
            "idle_scan",
            "whole_project_discovery",
            "ticket_generation",
            "queue_execution",
        ],
        "proposal_policy": "explain_before_mutating",
    },
    "idle_discovery": {
        "enabled": True,
        "min_interval_seconds": 60,
        "duplicate_cooldown_behavior": "continue_to_general_discovery",
        "ide_follow_up": {
            "enabled": True,
            "workflow": "standardized_project_discovery_ticket",
            "trigger": "no_tickets_after_scan_code2llm_todo2code_ticket2dsl",
            "prompt": (
                "Co jeszcze zostalo do wykonania? "
                "zrob z tego nastepne tickety do planfile."
            ),
            "expected_output": "new_planfile_tickets_only",
        },
        "tools": {
            "automated": ["koru_scan", "code2llm", "todo2code", "ticket2dsl"],
            "artifact_sources": [
                "jscpd",
                "redup",
                "testql",
                "vallm",
                "pyqual",
                "prefact",
                "regix",
                "redsl",
                "metrun",
                "pfix",
                "todo2code",
            ],
            "advisory": ["goal", "costs"],
        },
    },
    "planning_assistant": {
        "enabled": True,
        "provider_order": ["subllm_cursor"],
        "subllm_cursor": {
            "application": "koru-agent",
            "function": "planning-assistant",
            "mode": "cursor_sdk",
            "fail_closed": True,
        },
        "editable_sections": [
            "autonomy.strategy",
            "when",
            "environment",
        ],
        "update_policy": "propose_yaml_patch",
    },
    "heuristics": {
        "signals": [
            "open_planfile_tickets",
            "idle_streak",
            "scan_duplicate_cooldown",
            "code2llm_artifact_age",
            "semcod_tool_availability",
            "test_health",
        ],
        "prefer_specific_work_until_queue_empty": True,
        "prefer_general_discovery_when_idle": True,
    },
}


def default_autonomy_strategy_document() -> dict[str, Any]:
    return {"autonomy": {"strategy": DEFAULT_AUTONOMY_STRATEGY}}


def default_autonomy_strategy_yaml_block() -> str:
    return yaml.safe_dump(
        default_autonomy_strategy_document(),
        sort_keys=False,
        allow_unicode=True,
    )


__all__ = [
    "DEFAULT_AUTONOMY_STRATEGY",
    "default_autonomy_strategy_document",
    "default_autonomy_strategy_yaml_block",
]
