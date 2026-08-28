"""Dashboard state payload and operator URL helpers."""

from __future__ import annotations

import contextlib
import socket
from pathlib import Path
from typing import Any

from koruide.ide import autopilot_ide_choices, detect_running_ides

from koru.agents import shell_agent_lane_rows
from koruapi.dashboard_projects import (
  dashboard_workspace,
  discover_dashboard_projects,
  projects_by_ide,
)


def local_lan_addresses() -> list[str]:
  """Return best-effort non-loopback IPv4 addresses for LAN dashboard URLs."""
  found: list[str] = []

  def add(addr: str) -> None:
    if not addr or addr.startswith("127.") or addr == "0.0.0.0":
      return
    if "." not in addr or addr in found:
      return
    found.append(addr)

  with contextlib.suppress(OSError):
    hostname = socket.gethostname()
    _name, _aliases, addrs = socket.gethostbyname_ex(hostname)
    for addr in addrs:
      add(addr)
  with contextlib.suppress(OSError):
    probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
      probe.connect(("8.8.8.8", 80))
      add(str(probe.getsockname()[0]))
    finally:
      probe.close()
  return found


def dashboard_urls(host: str, port: int) -> list[str]:
  """Return URLs worth showing to the operator for this bind config."""
  hosts: list[str]
  if host in {"0.0.0.0", "::"}:
    hosts = ["localhost", *local_lan_addresses()]
  else:
    hosts = [host]
  urls = [f"http://{visible_host}:{port}/" for visible_host in hosts]
  return list(dict.fromkeys(urls))


def dashboard_ide_rows() -> tuple[list[dict[str, Any]], dict[str, list[dict[str, str]]]]:
  """Return ``(ide_rows, projects_by_ide_map)``.

  Each detected IDE gains a ``projects`` list (workspace + cwd) so the dashboard
  can switch the project picker to the project actually loaded in that IDE.
  """
  detected_ides = list(detect_running_ides())
  running = {row.id: row for row in detected_ides}
  by_ide = projects_by_ide(detected_ides)
  rows: list[dict[str, Any]] = [
    {"id": "auto", "label": "Auto", "running": False, "projects": []},
  ]
  for ide_id in autopilot_ide_choices():
    if ide_id == "auto":
      continue
    detected = running.get(ide_id)
    rows.append(
      {
        "id": ide_id,
        "label": detected.label if detected else ide_id,
        "running": detected is not None,
        "pid": detected.pid if detected else None,
        "exe": detected.exe if detected else None,
        "projects": by_ide.get(ide_id, []),
      }
    )
  seen_ids = {row["id"] for row in rows}
  for lane in shell_agent_lane_rows():
    if lane["id"] in seen_ids:
      continue
    rows.append(
      {
        "id": lane["id"],
        "label": f"{lane['label']} · CLI",
        "running": False,
        "kind": "shell",
        "command": lane.get("command"),
        "projects": [],
      }
    )
  return rows, by_ide


# /api/dashboard is polled every ~5s but its payload — running-IDE detection
# (process scan) plus project discovery (filesystem walk + per-project
# integration probes) — is expensive (~2-3s) and rarely changes. Cache it with
# a short TTL so most polls are instant; the ceiling keeps it live-enough.
_STATE_CACHE: dict[tuple[Any, ...], tuple[float, dict[str, Any]]] = {}
_STATE_TTL_S = 15.0


def dashboard_state(
  *,
  project: Path,
  host: str,
  port: int,
  lan: bool,
  configured_workspace: Path | None,
  queue_name: str | None,
) -> dict[str, Any]:
  import time

  key = (str(project), host, port, lan, str(configured_workspace), queue_name)
  cached = _STATE_CACHE.get(key)
  if cached is not None and (time.monotonic() - cached[0]) < _STATE_TTL_S:
    return cached[1]

  payload = _build_dashboard_state(
    project=project,
    host=host,
    port=port,
    lan=lan,
    configured_workspace=configured_workspace,
    queue_name=queue_name,
  )
  _STATE_CACHE[key] = (time.monotonic(), payload)
  return payload


def _build_dashboard_state(
  *,
  project: Path,
  host: str,
  port: int,
  lan: bool,
  configured_workspace: Path | None,
  queue_name: str | None,
) -> dict[str, Any]:
  ide_rows, by_ide = dashboard_ide_rows()
  return {
    "ok": True,
    "host": host,
    "port": port,
    "lan": bool(lan or host in {"0.0.0.0", "::"}),
    "urls": dashboard_urls(host, port),
    "workspace": str(dashboard_workspace(project, configured_workspace)),
    "default_project": str(project.resolve()),
    "projects": discover_dashboard_projects(project, configured_workspace),
    "ides": ide_rows,
    "projects_by_ide": by_ide,
    "queue_name": queue_name or "default",
  }