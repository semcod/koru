"""Project discovery helpers for the koru dashboard."""

from __future__ import annotations

import contextlib
import os
from pathlib import Path
from typing import Any, cast

from koru.wizard.project import propose_projects
from koruide.ide import detect_running_ides


def dashboard_workspace(project: Path, configured_workspace: Path | None) -> Path:
  raw = os.environ.get("KORU_SERVE_WORKSPACE", "").strip()
  if raw:
    return Path(raw).expanduser().resolve()
  if configured_workspace is not None:
    return configured_workspace.expanduser().resolve()
  return project.resolve().parent


def project_label(path: Path) -> str:
  return path.name or str(path)


def project_candidate_dict(path: Path, source: str) -> dict[str, Any]:
  path = path.expanduser().resolve()
  return {
    "path": str(path),
    "name": project_label(path),
    "source": source,
    "planfile": (path / ".planfile" / "config.yaml").is_file(),
    "git": (path / ".git").exists(),
  }


def looks_like_project(path: Path) -> bool:
  return any(
    (path / marker).exists()
    for marker in (
      ".git",
      ".planfile",
      "pyproject.toml",
      "package.json",
      "Cargo.toml",
      "go.mod",
      "Taskfile.yml",
      "Makefile",
    )
  )


def workspace_project_candidates(workspace: Path, *, max_results: int) -> list[Path]:
  workspace = workspace.expanduser().resolve()
  rows: list[Path] = []
  if looks_like_project(workspace):
    rows.append(workspace)
  try:
    children = sorted(workspace.iterdir(), key=lambda item: item.name.lower())
  except OSError:
    return rows
  for child in children:
    if len(rows) >= max_results:
      break
    if child.name.startswith(".") or not child.is_dir():
      continue
    if looks_like_project(child):
      rows.append(child.resolve())
  return rows


def discover_dashboard_projects(
  project: Path,
  configured_workspace: Path | None,
  *,
  max_results: int = 80,
) -> list[dict[str, Any]]:
  """Return projects the LAN dashboard may operate on."""
  rows: list[dict[str, Any]] = [project_candidate_dict(project, "serve project")]
  with contextlib.suppress(Exception):
    for item in propose_projects(cast(Any, detect_running_ides()), max_results=16):
      rows.append(project_candidate_dict(item.path, item.source))
  workspace = dashboard_workspace(project, configured_workspace)
  with contextlib.suppress(Exception):
    for candidate in workspace_project_candidates(workspace, max_results=max_results):
      rows.append(project_candidate_dict(candidate, f"workspace {workspace}"))

  seen: set[str] = set()
  out: list[dict[str, Any]] = []
  for row in rows:
    path = str(row["path"])
    if path in seen:
      continue
    seen.add(path)
    out.append(row)
    if len(out) >= max_results:
      break
  return out


def resolve_dashboard_project(
  project: Path,
  configured_workspace: Path | None,
  raw: object | None,
) -> Path:
  if raw is None or not str(raw).strip():
    return project.resolve()
  candidate = Path(str(raw)).expanduser().resolve()
  allowed = {
    Path(str(row["path"])).resolve()
    for row in discover_dashboard_projects(project, configured_workspace)
  }
  if candidate in allowed:
    return candidate
  raise ValueError(f"project is not available in this dashboard: {candidate}")