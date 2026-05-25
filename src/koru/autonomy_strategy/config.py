"""Persistence for the ``autonomy.strategy`` block in ``koru.yaml``."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from koru.autonomy_strategy.defaults import (
    DEFAULT_AUTONOMY_STRATEGY,
    default_autonomy_strategy_yaml_block,
)


@dataclass(frozen=True)
class AutonomyStrategyEnsureResult:
    path: Path
    created_koru_yaml: bool
    added_strategy: bool
    strategy_id: str


def load_autonomy_strategy(project: Path) -> dict[str, Any] | None:
    from koru.project_pipeline import load_koru_project_pipeline
    data = load_koru_project_pipeline(project)
    if not isinstance(data, dict):
        return None
    autonomy = data.get("autonomy")
    if not isinstance(autonomy, dict):
        return None
    strategy = autonomy.get("strategy")
    return strategy if isinstance(strategy, dict) else None


def ensure_autonomy_strategy_config(project: Path) -> AutonomyStrategyEnsureResult:
    """Ensure project ``koru.yaml`` contains ``autonomy.strategy``.

    Existing files are preserved when possible. If ``koru.yaml`` lacks any
    ``autonomy`` top-level key, append the new block instead of reserializing
    the whole file so comments and local formatting survive.
    """
    from koru.project_pipeline import (
        load_koru_project_pipeline,
        project_pipeline_path,
        write_koru_project_pipeline_if_absent,
    )
    project = project.resolve()
    path = project_pipeline_path(project)
    created = write_koru_project_pipeline_if_absent(project)
    if load_autonomy_strategy(project) is not None:
        return AutonomyStrategyEnsureResult(
            path=path,
            created_koru_yaml=created,
            added_strategy=False,
            strategy_id=str(DEFAULT_AUTONOMY_STRATEGY["id"]),
        )

    data = load_koru_project_pipeline(project)
    if data is None:
        data = {}
    added = _persist_missing_strategy(path, data)
    return AutonomyStrategyEnsureResult(
        path=path,
        created_koru_yaml=created,
        added_strategy=added,
        strategy_id=str(DEFAULT_AUTONOMY_STRATEGY["id"]),
    )


def _persist_missing_strategy(path: Path, data: dict[str, Any]) -> bool:
    autonomy = data.get("autonomy")
    if autonomy is None and path.is_file():
        text = path.read_text(encoding="utf-8")
        suffix = "\n\n# Default Koru autonomy strategy.\n" + default_autonomy_strategy_yaml_block()
        path.write_text(text.rstrip() + suffix, encoding="utf-8")
        return True

    if not isinstance(autonomy, dict):
        data["autonomy"] = {}
    data["autonomy"]["strategy"] = DEFAULT_AUTONOMY_STRATEGY
    path.write_text(
        yaml.safe_dump(data, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
    return True


__all__ = [
    "AutonomyStrategyEnsureResult",
    "ensure_autonomy_strategy_config",
    "load_autonomy_strategy",
]
