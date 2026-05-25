"""Context and handoff payload helpers for the koru dashboard API."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from koru.context import build_context, render_markdown_handoff
from koru.interface_registry import iter_interfaces, summarize_interfaces_by_family


def dashboard_context_payload(project: Path, queue_name: str | None) -> dict[str, Any]:
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
