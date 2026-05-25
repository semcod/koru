"""Runtime-context helpers for the koru dashboard API."""

from __future__ import annotations

import importlib
from pathlib import Path
from typing import Any

from koru.interface_registry import iter_interfaces, summarize_interfaces_by_family
from koruapi.runtime_insights import collect_runtime_insights


def _interface_runtime_payload() -> dict[str, Any]:
  items = iter_interfaces()
  return {
    "count": len(items),
    "families": summarize_interfaces_by_family(),
    "interactive_control": [
      item.id for item in items
      if item.family in {"ide_control", "desktop_control", "browser_control"}
    ],
    "observation": [
      item.id for item in items
      if item.family == "observation"
    ],
  }


def runtime_context_payload(project: Path) -> dict[str, Any]:
  runtime_context = importlib.import_module("planfile.runtime_context")
  runtime = runtime_context.build_runtime_context(project)
  runtime["dashboard_project"] = str(project)
  runtime["insights"] = collect_runtime_insights(project)
  runtime["interfaces"] = _interface_runtime_payload()
  return runtime


def runtime_context_error_payload(project: Path, exc: Exception) -> dict[str, Any]:
  runtime = {"error": str(exc), "type": type(exc).__name__}
  runtime["dashboard_project"] = str(project)
  runtime["insights"] = collect_runtime_insights(project)
  runtime["interfaces"] = _interface_runtime_payload()
  return runtime


def save_runtime_context_config(project: Path, body: dict[str, Any]) -> dict[str, Any]:
  runtime_context = importlib.import_module("planfile.runtime_context")
  current = runtime_context.load_runtime_context_config(project)
  merged = {
    "enabled": {
      **(current.get("enabled") or {}),
      **(body.get("enabled") or {}),
    },
    "overrides": {
      **(current.get("overrides") or {}),
      **(body.get("overrides") or {}),
    },
  }
  return runtime_context.save_runtime_context_config(project, merged)
