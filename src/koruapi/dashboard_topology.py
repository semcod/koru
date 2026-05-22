"""Topology payload helpers for the koru dashboard API."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from koru.topology import load_topology
from koruapi.topology_post import apply_topology_post_update


def dashboard_topology_payload(project: Path) -> dict[str, Any]:
  topology = load_topology(project)
  topology["dashboard_project"] = str(project)
  return topology


def apply_dashboard_topology_update(
  project: Path,
  body: dict[str, Any],
) -> tuple[dict[str, Any] | None, dict[str, Any] | None, int]:
  return apply_topology_post_update(project, body)