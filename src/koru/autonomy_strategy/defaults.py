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
            "trigger": "no_tickets_after_scan_and_code2llm",
            "prompt": (
                "Co jeszcze zostalo do wykonania? "
                "zrob z tego nastepne tickety do planfile."
            ),
            "expected_output": "new_planfile_tickets_only",
        },
        "tools": {
            "automated": ["koru_scan", "code2llm"],
            "artifact_sources": ["redup", "testql"],
            "advisory": ["prefact", "metrun"],
        },
    },
    "planning_assistant": {
        "enabled": True,
        "provider_order": ["openrouter", "ide_llm"],
        "openrouter": {
            "model": "openrouter/qwen/qwen3-coder-next",
            "api_key_env": "OPENROUTER_API_KEY",
            "mode": "prompt_or_explicit_call",
        },
        "ide_llm": {
            "mode": "prepared_prompt",
            "target": "active_autopilot_lane",
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
