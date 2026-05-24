"""Project discovery helpers for the koru dashboard."""

from __future__ import annotations

import contextlib
import json
import os
from pathlib import Path
from typing import Any, cast
from urllib.parse import unquote, urlparse

from koru.wizard.project import _candidates_from_running_ide, propose_projects
from koruide.ide import RunningIDE, detect_running_ides

_VSCODE_LIKE_IDE_DIRS: dict[str, tuple[str, ...]] = {
    "cursor": ("Cursor",),
    "vscode": ("Code", "Code - OSS"),
    "vscodium": ("VSCodium",),
    "windsurf": ("Windsurf",),
}

_SHELL_BINARIES = {"bash", "zsh", "fish", "sh", "dash", "ksh", "tcsh", "csh"}


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


def _running_ide_to_detected(row: RunningIDE) -> Any:
  """Adapt ``RunningIDE`` to the duck-typed shape expected by project discovery."""

  class _Adapter:
    def __init__(self, ide: RunningIDE) -> None:
      self.id = ide.id
      self.label = ide.label
      self.pid = ide.pid
      self.running = True

  return _Adapter(row)


def _read_workspace_folder(storage_dir: Path) -> Path | None:
  """Return the folder referenced by VS Code-like ``workspace.json``."""
  workspace_file = storage_dir / "workspace.json"
  try:
    data = json.loads(workspace_file.read_text(encoding="utf-8"))
  except (OSError, ValueError):
    return None
  folder = data.get("folder") if isinstance(data, dict) else None
  if not isinstance(folder, str) or not folder:
    return None
  parsed = urlparse(folder)
  if parsed.scheme not in ("", "file"):
    return None
  candidate = Path(unquote(parsed.path)).expanduser()
  if not candidate.exists() or not candidate.is_dir():
    return None
  return candidate.resolve()


def _workspace_storage_projects(ide_id: str) -> list[dict[str, str]]:
  """Read ``~/.config/<IDE>/User/workspaceStorage/*/workspace.json`` for *ide_id*."""
  dirs = _VSCODE_LIKE_IDE_DIRS.get(ide_id, ())
  rows: list[tuple[float, Path]] = []
  for ide_label in dirs:
    storage_root = Path("~").expanduser() / ".config" / ide_label / "User" / "workspaceStorage"
    if not storage_root.is_dir():
      continue
    try:
      entries = list(storage_root.iterdir())
    except OSError:
      continue
    for entry in entries:
      if not entry.is_dir():
        continue
      folder = _read_workspace_folder(entry)
      if folder is None:
        continue
      try:
        mtime = (entry / "workspace.json").stat().st_mtime
      except OSError:
        mtime = 0.0
      rows.append((mtime, folder))
  rows.sort(key=lambda item: item[0], reverse=True)
  seen: set[Path] = set()
  out: list[dict[str, str]] = []
  for _, path in rows:
    if path in seen:
      continue
    seen.add(path)
    out.append({"path": str(path), "source": f"{ide_id} workspace storage"})
  return out


def _read_proc_comm(pid: int) -> str:
  try:
    return Path(f"/proc/{pid}/comm").read_text(encoding="utf-8").strip()
  except OSError:
    return ""


def _read_proc_children(pid: int) -> list[int]:
  """Return direct child PIDs via ``/proc/<pid>/task/*/children`` (Linux)."""
  task_root = Path(f"/proc/{pid}/task")
  if not task_root.is_dir():
    return []
  out: list[int] = []
  try:
    for task_dir in task_root.iterdir():
      children_file = task_dir / "children"
      try:
        raw = children_file.read_text(encoding="utf-8").strip()
      except OSError:
        continue
      for token in raw.split():
        with contextlib.suppress(ValueError):
          out.append(int(token))
  except OSError:
    return out
  return out


def _walk_descendant_pids(root_pid: int, *, max_pids: int = 256) -> list[int]:
  seen: set[int] = set()
  stack = [root_pid]
  while stack and len(seen) < max_pids:
    pid = stack.pop()
    if pid in seen:
      continue
    seen.add(pid)
    for child in _read_proc_children(pid):
      if child not in seen:
        stack.append(child)
  seen.discard(root_pid)
  return list(seen)


def _read_proc_cwd_path(pid: int) -> Path | None:
  try:
    target = os.readlink(f"/proc/{pid}/cwd")
  except OSError:
    return None
  candidate = Path(target)
  return candidate if candidate.exists() and candidate.is_dir() else None


def integrated_terminal_cwds(pid: int) -> list[Path]:
  """Return unique cwd paths from shell processes inside an IDE's process tree."""
  found: list[Path] = []
  seen: set[Path] = set()
  for descendant in _walk_descendant_pids(pid):
    comm = _read_proc_comm(descendant)
    if comm not in _SHELL_BINARIES:
      continue
    cwd = _read_proc_cwd_path(descendant)
    if cwd is None:
      continue
    resolved = cwd.resolve()
    if resolved in seen:
      continue
    seen.add(resolved)
    found.append(resolved)
  return found


def _looks_like_real_project(path: Path) -> bool:
  """Same as :func:`looks_like_project` but rejects ``$HOME`` itself."""
  if not looks_like_project(path):
    return False
  try:
    home = Path("~").expanduser().resolve()
  except OSError:
    home = Path.home()
  return path.resolve() != home


def _project_entry_from_terminal_cwd(term_cwd: Path, ide_id: str) -> dict[str, str] | None:
  target = term_cwd
  if not _looks_like_real_project(target):
    walked = target
    for _ in range(4):
      if _looks_like_real_project(walked) or walked.parent == walked:
        break
      walked = walked.parent
    if _looks_like_real_project(walked):
      target = walked
    else:
      return None
  return {"path": str(target), "source": f"{ide_id} integrated shell"}


def _dedupe_project_entries(entries: list[dict[str, str]]) -> list[dict[str, str]]:
  seen: set[str] = set()
  deduped: list[dict[str, str]] = []
  for entry in entries:
    if entry["path"] in seen:
      continue
    seen.add(entry["path"])
    deduped.append(entry)
  return deduped


def _collect_projects_for_ide(ide: RunningIDE) -> list[dict[str, str]]:
  collected: list[dict[str, str]] = []
  with contextlib.suppress(Exception):
    candidates = _candidates_from_running_ide(_running_ide_to_detected(ide))
    for item in candidates:
      if _looks_like_real_project(item.path):
        collected.append({"path": str(item.path), "source": item.source})
  with contextlib.suppress(Exception):
    for entry in _workspace_storage_projects(ide.id):
      if _looks_like_real_project(Path(entry["path"])):
        collected.append(entry)
  if ide.pid is not None:
    with contextlib.suppress(Exception):
      for term_cwd in integrated_terminal_cwds(ide.pid):
        entry = _project_entry_from_terminal_cwd(term_cwd, ide.id)
        if entry is not None:
          collected.append(entry)
  return _dedupe_project_entries(collected)


def projects_by_ide(ides: list[RunningIDE] | None = None) -> dict[str, list[dict[str, str]]]:
  """Return ``{ide_id: [{path, source}, …]}`` derived from cmdline/cwd + workspace storage."""
  rows = list(ides) if ides is not None else list(detect_running_ides())
  out: dict[str, list[dict[str, str]]] = {}
  for ide in rows:
    out[ide.id] = _collect_projects_for_ide(ide)
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
  for rows in projects_by_ide().values():
    for row in rows:
      with contextlib.suppress(Exception):
        allowed.add(Path(row["path"]).resolve())
  if candidate in allowed:
    return candidate
  raise ValueError(f"project is not available in this dashboard: {candidate}")
