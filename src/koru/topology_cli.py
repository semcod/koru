"""CLI helpers for ``koru topology``."""

from __future__ import annotations

import sys
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class TopologyMutation:
    target_id: str | None
    enabled: bool
    kind: str
    setter: Callable[[dict[str, Any], str, bool], Any]


def render_topology_text(topology: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append(f"koru topology: {topology['project']}")
    status = "present" if topology["exists"] else "defaults only"
    lines.append(f"  config: {topology['path']} ({status})")
    lines.append("")
    lines.extend(_render_component_rows(topology))
    lines.append("")
    lines.extend(_render_pipeline_rows(topology))
    return "\n".join(lines)


def _render_component_rows(topology: dict[str, Any]) -> list[str]:
    lines = ["Components:", f"  {'id':<12} {'enabled':<7} {'available':<9} {'via':<8} role"]
    for cid, comp in (topology.get("components") or {}).items():
        en = "yes" if comp.get("enabled") else "no"
        avail = "yes" if comp.get("available") else "no"
        via = (comp.get("via") or "")[:8]
        role = (comp.get("role") or "")[:60]
        lines.append(f"  {cid:<12} {en:<7} {avail:<9} {via:<8} {role}")
    return lines


def _render_pipeline_rows(topology: dict[str, Any]) -> list[str]:
    lines = ["Pipelines:", f"  {'id':<22} {'enabled':<7} {'trigger':<16} description"]
    for pid, pipe in (topology.get("pipelines") or {}).items():
        en = "yes" if pipe.get("enabled") else "no"
        trig = (pipe.get("trigger") or "")[:16]
        desc = (pipe.get("description") or "")[:60]
        comps = ", ".join(pipe.get("components") or [])
        lines.append(f"  {pid:<22} {en:<7} {trig:<16} {desc}")
        if comps:
            lines.append(f"  {'':<22} {'':<7} {'':<16}   components: {comps}")
    return lines


def apply_topology_mutations(
    topo: dict[str, Any],
    mutations: list[TopologyMutation],
) -> tuple[bool, int]:
    """Apply enable/disable mutations. Returns (mutated, exit_code)."""
    mutated = False
    for mutation in mutations:
        if not mutation.target_id:
            continue
        res = mutation.setter(topo, mutation.target_id, mutation.enabled)
        if not res.found:
            print(
                f"koru topology: unknown {mutation.kind} {mutation.target_id!r}",
                file=sys.stderr,
            )
            return mutated, 2
        mutated = True
        print(
            f"koru topology: {mutation.kind} {res.id} {res.previous} -> {res.current}",
        )
    return mutated, 0
