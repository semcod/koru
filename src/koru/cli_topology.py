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


def _run_topology_is_enabled(
    args: argparse.Namespace,
    project: Path,
    query_service: TopologyQueryService,
) -> int | None:
    if not args.is_enabled:
        return None
    enabled = query_service.is_enabled(
        IsEnabledQuery(project=project, target_id=args.is_enabled),
    )
    if enabled is None:
        print(f"koru topology: unknown id {args.is_enabled!r}", file=sys.stderr)
        return 2
    print("true" if enabled else "false")
    return 0 if enabled else 1


def _run_topology_enabled_components(
    args: argparse.Namespace,
    project: Path,
    query_service: TopologyQueryService,
) -> int | None:
    if not args.enabled_components_for:
        return None
    ids = query_service.enabled_components_for_pipeline(
        EnabledComponentsForPipelineQuery(
            project=project,
            pipeline_id=args.enabled_components_for,
        ),
    )
    print(",".join(ids))
    return 0


def _topology_component_toggler(
    command_service: TopologyCommandService,
    project: Path,
):
    def _set_component_enabled(topology: dict[str, Any], target_id: str, enabled: bool) -> Any:
        return command_service.toggle_component(
            ToggleComponentCommand(
                project=project,
                topology=topology,
                component_id=target_id,
                enabled=enabled,
            ),
        )

    return _set_component_enabled


def _topology_pipeline_toggler(
    command_service: TopologyCommandService,
    project: Path,
):
    def _set_pipeline_enabled(topology: dict[str, Any], target_id: str, enabled: bool) -> Any:
        return command_service.toggle_pipeline(
            TogglePipelineCommand(
                project=project,
                topology=topology,
                pipeline_id=target_id,
                enabled=enabled,
            ),
        )

    return _set_pipeline_enabled


def _apply_topology_cli_mutations(
    args: argparse.Namespace,
    project: Path,
    topo: dict[str, Any],
    command_service: TopologyCommandService,
) -> tuple[bool, int]:
    set_component = _topology_component_toggler(command_service, project)
    set_pipeline = _topology_pipeline_toggler(command_service, project)
    return apply_topology_mutations(
        topo,
        [
            TopologyMutation(args.enable, True, "component", set_component),
            TopologyMutation(args.disable, False, "component", set_component),
            TopologyMutation(args.enable_pipeline, True, "pipeline", set_pipeline),
            TopologyMutation(args.disable_pipeline, False, "pipeline", set_pipeline),
        ],
    )


def _print_topology(topo: dict[str, Any], output_format: str) -> None:
    if output_format == "json":
        print(json.dumps(topo, indent=2, sort_keys=True, default=str))
    else:
        print(render_topology_text(topo))


def topology_main(argv: list[str]) -> int:
    args = build_topology_parser().parse_args(argv)
    project = args.project.resolve()
    command_service = TopologyCommandService()
    query_service = TopologyQueryService()

    predicate_rc = _run_topology_is_enabled(args, project, query_service)
    if predicate_rc is not None:
        return predicate_rc

    components_rc = _run_topology_enabled_components(args, project, query_service)
    if components_rc is not None:
        return components_rc

    topo = query_service.load(LoadTopologyQuery(project=project))
    mutated, rc = _apply_topology_cli_mutations(args, project, topo, command_service)
    if rc != 0:
        return rc

    if mutated:
        path = command_service.persist(PersistTopologyCommand(project=project, topology=topo))
        print(f"koru topology: saved {path}")
        topo = query_service.load(LoadTopologyQuery(project=project))

    _print_topology(topo, args.output_format)
    return 0
