"""CLI command for showing & editing project topology."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from koru.bounded_contexts.topology import TopologyCommandService, TopologyQueryService
from koru.bounded_contexts.topology.commands import (
    PersistTopologyCommand,
    ToggleComponentCommand,
    TogglePipelineCommand,
)
from koru.bounded_contexts.topology.queries import (
    EnabledComponentsForPipelineQuery,
    IsEnabledQuery,
    LoadTopologyQuery,
)
from koru.topology_cli import TopologyMutation, apply_topology_mutations


def build_topology_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="koru topology",
        description=(
            "Show & edit the project topology: which semcod components "
            "(regix, testql, wup, …) and pipelines (idle-diagnostics, "
            "gate:regix, autoloop:queue, …) are enabled. State is "
            "persisted to .koru/topology.yaml."
        ),
    )
    parser.add_argument("--project", type=Path, default=Path.cwd(), help="Project root.")
    parser.add_argument(
        "--format",
        dest="output_format",
        choices=("text", "json"),
        default="text",
        help="Output format for the listing (default text).",
    )
    parser.add_argument("--enable", metavar="ID", help="Enable component ID and persist.")
    parser.add_argument("--disable", metavar="ID", help="Disable component ID and persist.")
    parser.add_argument(
        "--enable-pipeline",
        metavar="ID",
        help="Enable pipeline ID and persist.",
    )
    parser.add_argument(
        "--disable-pipeline",
        metavar="ID",
        help="Disable pipeline ID and persist.",
    )
    parser.add_argument(
        "--is-enabled",
        metavar="ID",
        help=(
            "Print 'true' or 'false' for the given component or pipeline id "
            "(component takes precedence on collision) and exit 0/1."
        ),
    )
    parser.add_argument(
        "--enabled-components-for",
        metavar="PIPELINE",
        help="Print comma-separated enabled component ids for the pipeline and exit.",
    )
    return parser


def render_topology_text(topology: dict[str, Any]) -> str:
    from koru.topology_cli import render_topology_text as topo_render

    return topo_render(topology)


def topology_main(argv: list[str]) -> int:
    args = build_topology_parser().parse_args(argv)
    project = args.project.resolve()
    command_service = TopologyCommandService()
    query_service = TopologyQueryService()

    # Predicate modes — print value and exit; do not mutate.
    if args.is_enabled:
        enabled = query_service.is_enabled(
            IsEnabledQuery(project=project, target_id=args.is_enabled),
        )
        if enabled is None:
            print(f"koru topology: unknown id {args.is_enabled!r}", file=sys.stderr)
            return 2
        print("true" if enabled else "false")
        return 0 if enabled else 1

    if args.enabled_components_for:
        ids = query_service.enabled_components_for_pipeline(
            EnabledComponentsForPipelineQuery(
                project=project,
                pipeline_id=args.enabled_components_for,
            ),
        )
        print(",".join(ids))
        return 0

    topo = query_service.load(LoadTopologyQuery(project=project))

    def _set_component_enabled(topology: dict[str, Any], target_id: str, enabled: bool) -> Any:
        return command_service.toggle_component(
            ToggleComponentCommand(
                project=project,
                topology=topology,
                component_id=target_id,
                enabled=enabled,
            ),
        )

    def _set_pipeline_enabled(topology: dict[str, Any], target_id: str, enabled: bool) -> Any:
        return command_service.toggle_pipeline(
            TogglePipelineCommand(
                project=project,
                topology=topology,
                pipeline_id=target_id,
                enabled=enabled,
            ),
        )

    mutated, rc = apply_topology_mutations(
        topo,
        [
            TopologyMutation(args.enable, True, "component", _set_component_enabled),
            TopologyMutation(args.disable, False, "component", _set_component_enabled),
            TopologyMutation(args.enable_pipeline, True, "pipeline", _set_pipeline_enabled),
            TopologyMutation(args.disable_pipeline, False, "pipeline", _set_pipeline_enabled),
        ],
    )
    if rc != 0:
        return rc

    if mutated:
        path = command_service.persist(PersistTopologyCommand(project=project, topology=topo))
        print(f"koru topology: saved {path}")
        # Reload to surface the merged view back to the user.
        topo = query_service.load(LoadTopologyQuery(project=project))

    if args.output_format == "json":
        print(json.dumps(topo, indent=2, sort_keys=True, default=str))
    else:
        print(render_topology_text(topo))
    return 0
