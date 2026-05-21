"""Topology POST update use-case for the dashboard API."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from koru.topology import load_topology, save_topology, set_component_enabled, set_pipeline_enabled

LoadTopology = Callable[[Path], dict[str, Any]]
SaveTopology = Callable[[Path, dict[str, Any]], Path]


def apply_topology_post_update(
    project: Path,
    body: dict[str, Any],
    *,
    load_topology_fn: LoadTopology = load_topology,
    save_topology_fn: SaveTopology = save_topology,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None, int]:
    """Apply topology enable/disable edits from a POST body."""
    components = body.get("components") or {}
    pipelines = body.get("pipelines") or {}
    if not isinstance(components, dict) or not isinstance(pipelines, dict):
        return None, {"error": "`components` and `pipelines` must be objects"}, 400
    if not components and not pipelines:
        return (
            None,
            {"error": "empty update; provide `components` and/or `pipelines`"},
            400,
        )

    topo = load_topology_fn(project)
    errors: list[str] = []
    applied: list[dict[str, Any]] = []

    for component_id, enabled in components.items():
        if not isinstance(enabled, bool):
            errors.append(f"component {component_id!r}: value must be boolean")
            continue
        result = set_component_enabled(topo, str(component_id), enabled)
        if not result.found:
            errors.append(f"unknown component: {component_id!r}")
            continue
        applied.append({"kind": "component", "id": result.id, "enabled": result.current})

    for pipeline_id, enabled in pipelines.items():
        if not isinstance(enabled, bool):
            errors.append(f"pipeline {pipeline_id!r}: value must be boolean")
            continue
        result = set_pipeline_enabled(topo, str(pipeline_id), enabled)
        if not result.found:
            errors.append(f"unknown pipeline: {pipeline_id!r}")
            continue
        applied.append({"kind": "pipeline", "id": result.id, "enabled": result.current})

    if errors:
        return None, {"error": "invalid topology update", "details": errors}, 400

    saved = save_topology_fn(project, topo)
    merged = load_topology_fn(project)
    merged["path"] = str(saved)
    merged["saved"] = applied
    return merged, None, 200


__all__ = ["apply_topology_post_update"]
