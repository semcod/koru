"""Context and handoff payload helpers for the koru dashboard API."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from koru.context import build_context, render_markdown_handoff


def dashboard_context_payload(project: Path, queue_name: str | None) -> dict[str, Any]:
  context = build_context(project=project, queue_name=queue_name)
  context["dashboard_project"] = str(project)
  return context


def dashboard_handoff_markdown(project: Path, queue_name: str | None) -> str:
  return render_markdown_handoff(dashboard_context_payload(project, queue_name))