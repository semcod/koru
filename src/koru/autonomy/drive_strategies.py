"""Small strategy runner for autonomous IDE drive fallback chains."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class DriveStrategyContext:
    client: Any
    prompt: str
    submit: bool
    autopilot_ide: str
    require_plugin: bool
    project: Path | None = None
    plugin_reply: dict[str, Any] | None = None


@dataclass(frozen=True)
class DriveStrategy:
    name: str
    run: Callable[[DriveStrategyContext], dict[str, Any] | None]
    return_on_failure: bool = False
    keep_failure: bool = False


def execute_drive_strategies(
    strategies: list[DriveStrategy],
    context: DriveStrategyContext,
) -> tuple[dict[str, Any], bool] | None:
    """Execute strategies until the first success or configured terminal failure."""
    kept_failure: tuple[dict[str, Any], bool] | None = None
    for strategy in strategies:
        reply = strategy.run(context)
        if reply is None:
            continue
        ok = bool(reply.get("ok", True))
        if ok or strategy.return_on_failure:
            return reply, ok
        if strategy.keep_failure:
            kept_failure = (reply, ok)
    return kept_failure


__all__ = ["DriveStrategy", "DriveStrategyContext", "execute_drive_strategies"]
