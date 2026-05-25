"""Autonomy strategy configuration helpers."""

from __future__ import annotations

from typing import Any


def __getattr__(name: str) -> Any:
    if name in {
        "AutonomyStrategyEnsureResult",
        "ensure_autonomy_strategy_config",
        "load_autonomy_strategy",
    }:
        from koru.autonomy_strategy import config

        return getattr(config, name)
    if name == "build_strategy_heuristics":
        from koru.autonomy_strategy.heuristics import build_strategy_heuristics

        return build_strategy_heuristics
    if name == "build_strategy_update_prompt":
        from koru.autonomy_strategy.prompts import build_strategy_update_prompt

        return build_strategy_update_prompt
    raise AttributeError(name)

__all__ = [
    "AutonomyStrategyEnsureResult",
    "build_strategy_heuristics",
    "build_strategy_update_prompt",
    "ensure_autonomy_strategy_config",
    "load_autonomy_strategy",
]
