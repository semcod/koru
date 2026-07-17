"""Discover and bootstrap koru across many sibling projects in one workspace.

``koru fleet bootstrap`` walks a parent folder (e.g. ``~/github/subactor``),
finds child git repositories, and ensures each has ``.planfile/`` plus
``.planfile/.koru/policy.yaml`` so ``koru fleet ls`` / ``koru fleet up`` can
see them.

Critical safety contract (learned the hard way): never call
``koru --init --force`` just to add a missing policy marker. Projects that
already have tickets must get a **soft ensure** (policy stub + gitignore
only). ``--force`` remains available but is never the default.
"""

from __future__ import annotations

import fnmatch
import os
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from koru.init import (
    _ensure_gitignore_entry,
    _write_policy_stub_if_absent,
    init_project,
)
from koru.runtime import planfile_dir, runtime_dir

# Default noise to skip when scanning workspace children.
_DEFAULT_EXCLUDE_GLOBS: tuple[str, ...] = (
    "backups",
    "backups/*",
    "node_modules",
    "node_modules/*",
    ".venv",
    ".venv/*",
    "venv",
    "venv/*",
    "__pycache__",
    "__pycache__/*",
    "dist",
    "dist/*",
    "build",
    "build/*",
    ".git",
    ".git/*",
)


class BootstrapStatus(str, Enum):
    SKIPPED = "skipped"
    INITIALIZED = "initialized"
    POLICY_ADDED = "policy_added"
    WOULD_INIT = "would_init"
    WOULD_ADD_POLICY = "would_add_policy"
    ERROR = "error"
    EXCLUDED = "excluded"


@dataclass
class BootstrapResult:
    project: Path
    status: BootstrapStatus
    detail: str = ""

    def line(self) -> str:
        rel = str(self.project)
        if self.detail:
            return f"  [{self.status.value}] {rel} — {self.detail}"
        return f"  [{self.status.value}] {rel}"


@dataclass
class BootstrapSummary:
    workspace: Path
    results: list[BootstrapResult] = field(default_factory=list)

    def counts(self) -> dict[str, int]:
        out: dict[str, int] = {}
        for row in self.results:
            out[row.status.value] = out.get(row.status.value, 0) + 1
        return out

    def report_text(self) -> str:
        counts = self.counts()
        parts = [f"{k}={v}" for k, v in sorted(counts.items())]
        lines = [
            f"koru fleet bootstrap: {len(self.results)} candidate(s) under {self.workspace}",
            *([f"  summary: {', '.join(parts)}"] if parts else []),
            *(r.line() for r in self.results),
        ]
        return "\n".join(lines)


def is_koru_managed(project: Path) -> bool:
    """True when ``.planfile/.koru/policy.yaml`` exists (fleet discovery marker)."""
    return (runtime_dir(project) / "policy.yaml").is_file()


def has_planfile_config(project: Path) -> bool:
    return (planfile_dir(project) / "config.yaml").is_file()


def _is_git_project(path: Path) -> bool:
    git = path / ".git"
    return git.is_dir() or git.is_file()  # file = worktree / submodule pointer


def _rel_key(workspace: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(workspace.resolve()).as_posix()
    except ValueError:
        return path.name


def _matches_any(key: str, patterns: list[str]) -> bool:
    name = Path(key).name
    for pattern in patterns:
        if fnmatch.fnmatch(key, pattern) or fnmatch.fnmatch(name, pattern):
            return True
        # Also match "foo/*" style against direct children named foo
        if pattern.endswith("/*") and (key == pattern[:-2] or name == pattern[:-2]):
            return True
    return False


def discover_bootstrap_candidates(
    workspace: Path,
    *,
    depth: int = 1,
    include: list[str] | None = None,
    exclude: list[str] | None = None,
    require_git: bool = True,
    umbrella: bool = False,
) -> list[Path]:
    """Find project roots under *workspace* that should receive koru markers.

    - *depth*: ``1`` = immediate children only; higher values walk nested dirs.
    - *require_git*: skip directories without a ``.git`` entry (default True).
    - *umbrella*: also consider the workspace root itself (git optional).
    - *include* / *exclude*: fnmatch globs against the path relative to workspace
      (and against the basename). Default excludes cover ``backups``, venvs, etc.
    """
    workspace = workspace.expanduser().resolve()
    if not workspace.is_dir():
        raise NotADirectoryError(f"workspace is not a directory: {workspace}")

    include_globs = list(include or [])
    exclude_globs = list(_DEFAULT_EXCLUDE_GLOBS)
    if exclude:
        exclude_globs.extend(exclude)

    found: list[Path] = []

    def _accept(path: Path, *, git_required: bool, skip_include: bool = False) -> bool:
        if not path.is_dir():
            return False
        if path.name.startswith(".") and path != workspace:
            return False
        key = "." if path == workspace else _rel_key(workspace, path)
        name = path.name
        if _matches_any(key, exclude_globs) or _matches_any(name, exclude_globs):
            return False
        # --include filters children; umbrella root is opted in via --umbrella.
        if include_globs and not skip_include:
            if not (_matches_any(key, include_globs) or _matches_any(name, include_globs)):
                return False
        if git_required and not _is_git_project(path):
            return False
        return True

    if umbrella and _accept(workspace, git_required=False, skip_include=True):
        found.append(workspace)

    max_depth = max(1, int(depth))
    for dirpath, dirnames, _filenames in os.walk(workspace):
        base = Path(dirpath)
        try:
            rel_parts = base.resolve().relative_to(workspace).parts
        except ValueError:
            dirnames[:] = []
            continue
        current_depth = len(rel_parts)
        if current_depth >= max_depth:
            dirnames[:] = []
            continue
        # Prune obvious junk early
        dirnames[:] = [
            d
            for d in dirnames
            if not d.startswith(".")
            and d not in {"node_modules", "backups", "__pycache__", "dist", "build"}
            and not d.endswith(".egg-info")
        ]
        for name in list(dirnames):
            child = base / name
            child_depth = current_depth + 1
            if child_depth > max_depth:
                continue
            if _accept(child, git_required=require_git):
                found.append(child.resolve())

    # Stable unique order
    seen: set[Path] = set()
    ordered: list[Path] = []
    for p in found:
        if p not in seen:
            seen.add(p)
            ordered.append(p)
    return sorted(ordered)


def ensure_koru_project(
    project: Path,
    *,
    force: bool = False,
    dry_run: bool = False,
    agent_lane: str = "auto",
    prepare_host_environment: bool = False,
) -> BootstrapResult:
    """Ensure *project* is koru-managed without clobbering existing tickets.

    Paths:
      1. Already has ``policy.yaml`` and not *force* → skipped.
      2. Has ``.planfile/config.yaml`` but no policy → soft ensure (policy only).
      3. Fresh tree → ``init_project`` (starter tickets only when brand new).
      4. *force* → ``init_project(..., force=True)`` (dangerous; backups exist).
    """
    project = project.expanduser().resolve()
    try:
        if is_koru_managed(project) and not force:
            return BootstrapResult(
                project,
                BootstrapStatus.SKIPPED,
                "already managed (.planfile/.koru/policy.yaml)",
            )

        if has_planfile_config(project) and not force:
            if dry_run:
                return BootstrapResult(
                    project,
                    BootstrapStatus.WOULD_ADD_POLICY,
                    "planfile exists; would write policy.yaml only (no ticket changes)",
                )
            policy_written = _write_policy_stub_if_absent(project)
            gitignore_updated = _ensure_gitignore_entry(project)
            bits = []
            if policy_written:
                bits.append("policy.yaml written")
            else:
                bits.append("policy.yaml already present")
            if gitignore_updated:
                bits.append(".gitignore updated")
            return BootstrapResult(
                project,
                BootstrapStatus.POLICY_ADDED,
                ", ".join(bits),
            )

        if dry_run:
            return BootstrapResult(
                project,
                BootstrapStatus.WOULD_INIT,
                "would run koru --init (fresh planfile + policy)",
            )

        report = init_project(
            project,
            force=force,
            agent_lane=agent_lane,
            prepare_host_environment=prepare_host_environment,
        )
        return BootstrapResult(
            project,
            BootstrapStatus.INITIALIZED,
            report.summary(),
        )
    except Exception as exc:  # noqa: BLE001 — surface per-project, keep going
        return BootstrapResult(project, BootstrapStatus.ERROR, str(exc))


def bootstrap_workspace(
    workspace: Path,
    *,
    depth: int = 1,
    include: list[str] | None = None,
    exclude: list[str] | None = None,
    require_git: bool = True,
    umbrella: bool = False,
    force: bool = False,
    dry_run: bool = False,
    agent_lane: str = "auto",
    prepare_host_environment: bool = False,
) -> BootstrapSummary:
    """Discover candidates and ensure each is koru-managed."""
    workspace = workspace.expanduser().resolve()
    candidates = discover_bootstrap_candidates(
        workspace,
        depth=depth,
        include=include,
        exclude=exclude,
        require_git=require_git,
        umbrella=umbrella,
    )
    summary = BootstrapSummary(workspace=workspace)
    for project in candidates:
        summary.results.append(
            ensure_koru_project(
                project,
                force=force,
                dry_run=dry_run,
                agent_lane=agent_lane,
                prepare_host_environment=prepare_host_environment,
            )
        )
    return summary


__all__ = [
    "BootstrapResult",
    "BootstrapStatus",
    "BootstrapSummary",
    "bootstrap_workspace",
    "discover_bootstrap_candidates",
    "ensure_koru_project",
    "has_planfile_config",
    "is_koru_managed",
]
