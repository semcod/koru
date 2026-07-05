"""Context and handoff payload helpers for the koru dashboard API."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from koru.context import build_context, render_markdown_handoff
from koru.interface_registry import iter_interfaces, summarize_interfaces_by_family

# The dashboard polls /api/context every ~5s. build_context() shells out to
# the planfile CLI ~6x and (before caching) reparsed a 1MB sprint YAML — ~2.5s
# per hit. Cache the whole payload keyed on the sprint file's mtime+size so a
# poll with no ticket change is served instantly; a stale-time ceiling still
# forces a periodic refresh for non-ticket inputs (config/env).
_CONTEXT_CACHE: dict[tuple[str, str | None], tuple[int, int, float, dict[str, Any]]] = {}
_CONTEXT_MAX_AGE_S = 20.0


def _sprint_signature(project: Path) -> tuple[int, int]:
  try:
    from koru.runtime import planfile_dir

    stat = (planfile_dir(project) / "sprints" / "current.yaml").stat()
    return stat.st_mtime_ns, stat.st_size
  except OSError:
    return 0, 0


def dashboard_context_payload(project: Path, queue_name: str | None) -> dict[str, Any]:
  key = (str(project), queue_name)
  mtime_ns, size = _sprint_signature(project)
  cached = _CONTEXT_CACHE.get(key)
  if (
    cached is not None
    and cached[0] == mtime_ns
    and cached[1] == size
    and (time.monotonic() - cached[2]) < _CONTEXT_MAX_AGE_S
  ):
    return cached[3]

  payload = _build_dashboard_context_payload(project, queue_name)
  _CONTEXT_CACHE[key] = (mtime_ns, size, time.monotonic(), payload)
  return payload


def _build_dashboard_context_payload(project: Path, queue_name: str | None) -> dict[str, Any]:
  context = build_context(project=project, queue_name=queue_name)
  context["dashboard_project"] = str(project)
  context["interfaces"] = {
    "count": len(iter_interfaces()),
    "families": summarize_interfaces_by_family(),
    "notable": [
      item.id for item in iter_interfaces()
      if item.id in {
        "mcp_stdio_server",
        "dashboard_rest",
        "plugin_socket_vscode_family",
        "antigravity_native_send",
        "filesystem_planfile",
      }
    ],
  }
  return context


def dashboard_handoff_markdown(project: Path, queue_name: str | None) -> str:
  return render_markdown_handoff(dashboard_context_payload(project, queue_name))
