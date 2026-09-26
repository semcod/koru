"""File selection and safe reads for project context assembly.

Decides which repository files a context snapshot embeds — explicit
request lists, glob expansion and the auto-include set — and reads them
safely: path escape out of the project root is blocked and the
non-negotiable exclusion policy from :mod:`koru.queue.context_exclusions`
is applied to every candidate.

Split from ``koru.queue.context`` (PLF-039); the facade re-exports the
moved names so existing ``koru.queue.context`` imports stay stable.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from koru.queue.context_exclusions import _is_excluded

_logger = logging.getLogger(__name__)

# --- Auto-include patterns (used when include_project_context=true) ----------

_AUTO_INCLUDE_FILENAMES: tuple[str, ...] = (
    "koru.yaml",
    "Dockerfile",
    "docker-compose.yml",
    "docker-compose.yaml",
    "README.md",
    "README.rst",
    "README.txt",
    "pyproject.toml",
    "setup.cfg",
    "setup.py",
    "package.json",
    "Makefile",
    "Taskfile.yml",
    ".planfile/config.yaml",
    ".planfile/config.yml",
)

_AUTO_INCLUDE_GLOBS: tuple[str, ...] = (
    "docker-compose*.yml",
    "docker-compose*.yaml",
    ".koru/*.yaml",
    ".koru/*.yml",
)


# ---------------------------------------------------------------------------


def _read_file_tree(project: Path, *, max_entries: int = 500) -> str:
    """Return a compact directory listing of the project root."""
    lines: list[str] = []
    count = 0
    try:
        for path in sorted(project.rglob("*")):
            if count >= max_entries:
                lines.append(f"  ... (listing truncated at {max_entries} entries)")
                break
            try:
                rel = path.relative_to(project)
            except ValueError:
                continue
            rel_str = rel.as_posix()
            if _is_excluded(rel_str):
                continue
            indent = "  " + "  " * (len(rel.parts) - 1)
            suffix = "/" if path.is_dir() else ""
            lines.append(f"{indent}{path.name}{suffix}")
            count += 1
    except OSError as exc:
        _logger.debug("context: file tree error: %s", exc)
    return "\n".join(lines)


def _read_file_content(project: Path, rel_path: str) -> str | None:
    """Return UTF-8 text of *rel_path* inside *project*, or None on error."""
    abs_path = (project / rel_path).resolve()
    # Safety: must stay inside project root
    try:
        abs_path.relative_to(project.resolve())
    except ValueError:
        _logger.warning("context: path escape attempt blocked: %s", rel_path)
        return None
    if not abs_path.is_file():
        return None
    if _is_excluded(rel_path):
        return None
    try:
        return abs_path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        _logger.debug("context: cannot read %s: %s", rel_path, exc)
        return None


def _collect_auto_files(project: Path) -> list[str]:
    """Return relative paths for the auto-include file set."""
    found: list[str] = []
    for filename in _AUTO_INCLUDE_FILENAMES:
        candidate = project / filename
        if candidate.is_file():
            found.append(filename)
    for glob_pattern in _AUTO_INCLUDE_GLOBS:
        for match in sorted(project.glob(glob_pattern)):
            rel = match.relative_to(project).as_posix()
            if rel not in found and not _is_excluded(rel):
                found.append(rel)
    return found


def _collect_glob_files(project: Path, globs: list[str]) -> list[str]:
    """Expand a list of glob patterns relative to *project*."""
    found: list[str] = []
    seen: set[str] = set()
    for pattern in globs:
        try:
            for match in sorted(project.glob(pattern)):
                if not match.is_file():
                    continue
                rel = match.relative_to(project).as_posix()
                if rel in seen or _is_excluded(rel):
                    continue
                seen.add(rel)
                found.append(rel)
        except OSError as exc:
            _logger.debug("context: glob %r error: %s", pattern, exc)
    return found


def _context_nothing_requested(request: dict[str, Any]) -> bool:
    return not (
        request.get("include_project_context")
        or request.get("context_files")
        or request.get("context_globs")
        or request.get("ticket_files")
    )


def _context_files_to_include(project: Path, request: dict[str, Any]) -> list[str]:
    """Ordered unique relative paths to embed from request inputs.

    Explicit ticket targets must precede convenience context.  The final
    payload is bounded, so putting README and build metadata first can consume
    the whole budget while ``included_files`` misleadingly names a source file
    the model never received.
    """
    include_project_context = request.get("include_project_context")
    context_files: list[str] = list(request.get("context_files") or [])
    context_globs: list[str] = list(request.get("context_globs") or [])
    ticket_files: list[str] = list(request.get("ticket_files") or [])

    files_to_include: list[str] = []
    seen: set[str] = set()

    def _add(rel: str) -> None:
        if rel not in seen and not _is_excluded(rel):
            seen.add(rel)
            files_to_include.append(rel)

    for rel in ticket_files:
        _add(rel)
    for rel in context_files:
        _add(rel)
    if context_globs:
        for rel in _collect_glob_files(project, context_globs):
            _add(rel)
    if include_project_context:
        for rel in _collect_auto_files(project):
            _add(rel)
    return files_to_include
