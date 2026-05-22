"""Runtime-context helpers for the koru dashboard API."""

from __future__ import annotations

import importlib
from pathlib import Path
from typing import Any

from koruapi.runtime_insights import collect_runtime_insights


def runtime_context_payload(project: Path) -> dict[str, Any]:
  runtime_context = importlib.import_module("planfile.runtime_context")
  runtime = runtime_context.build_runtime_context(project)
  runtime["dashboard_project"] = str(project)
  runtime["insights"] = collect_runtime_insights(project)
  return runtime


def runtime_context_error_payload(project: Path, exc: Exception) -> dict[str, Any]:
  runtime = {"error": str(exc), "type": type(exc).__name__}
  runtime["dashboard_project"] = str(project)
  runtime["insights"] = collect_runtime_insights(project)
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