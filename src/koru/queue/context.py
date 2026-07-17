"""Project context assembly for executor.kind=llm tickets.

Builds a bounded, secret-free snapshot of repository files so that an
LLM executor can answer ticket prompts with evidence from the actual
project rather than making generic assumptions.

Opt-in contract (ticket ``inputs`` fields):
  include_project_context: true   – auto-include file tree + common project files
  context_files: [path, ...]      – explicit file list (relative to project root)
  context_globs: ["src/**/*.py"]  – glob patterns (relative to project root)
  max_context_chars: 32000        – hard cap; default is DEFAULT_MAX_CONTEXT_CHARS

Security defaults:
  - Secrets, credentials, private keys, .env files are *always* excluded.
  - node_modules, vendor, generated files, and VCS internals are excluded.
  - Opt-in for any sensitive path is not supported; the exclusions are
    non-negotiable so context assembly can never leak secrets.
"""

from __future__ import annotations

import fnmatch
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

_logger = logging.getLogger(__name__)

DEFAULT_MAX_CONTEXT_CHARS: int = 32_000

# --- Security exclusions (always applied, non-negotiable) -------------------

_ALWAYS_EXCLUDED_NAMES: frozenset[str] = frozenset(
    {
        # Secrets / credentials
        ".env",
        "secrets",
        "credentials",
        # VCS
        ".git",
        # Generated / binary / large dependency trees
        "node_modules",
        "vendor",
        "__pycache__",
        ".venv",
        "venv",
        "dist",
        "build",
        ".eggs",
        # IDE / OS
        ".DS_Store",
    }
)

_ALWAYS_EXCLUDED_SUFFIXES: tuple[str, ...] = (
    # Credentials / keys
    ".env",
    ".key",
    ".pem",
    ".p12",
    ".pfx",
    ".crt",
    ".cert",
    ".cer",
    ".jks",
    ".der",
    # Compiled / binary
    ".pyc",
    ".pyo",
    ".so",
    ".dll",
    ".exe",
    ".bin",
    ".whl",
    ".zip",
    ".tar",
    ".gz",
    ".bz2",
    # Databases / dumps
    ".sqlite",
    ".db",
    ".sql",
    # Media
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".svg",
    ".ico",
    ".mp4",
    ".mp3",
    ".webm",
    # Lock files (large, mostly generated)
    ".lock",
)

_ALWAYS_EXCLUDED_GLOB_PATTERNS: tuple[str, ...] = (
    "*.env.*",
    ".env.*",
    "*.secret",
    "secrets/**",
    "credentials/**",
    ".git/**",
    "node_modules/**",
    "vendor/**",
    "__pycache__/**",
    "**/__pycache__/**",
    ".venv/**",
    "venv/**",
    "dist/**",
    "build/**",
    ".eggs/**",
    "*.egg-info/**",
    ".coverage",
    "coverage.xml",
    "*.log",
)

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


@dataclass
class ContextResult:
    """Output of a single context-assembly pass."""

    text: str
    """The assembled context string ready to embed in an LLM message."""

    included_files: list[str] = field(default_factory=list)
    """Relative paths of files whose content was included."""

    truncated: bool = False
    """True when the assembled text was cut at ``max_context_chars``."""

    total_chars: int = 0
    """Total characters before truncation (0 when not truncated)."""


def _is_excluded(rel_path: str) -> bool:
    """Return True when *rel_path* must never appear in context output."""
    # Check each path component for excluded directory names
    parts = Path(rel_path).parts
    for part in parts:
        if part in _ALWAYS_EXCLUDED_NAMES:
            return True
    # Suffix check on the final component
    name = parts[-1] if parts else rel_path
    suffix = Path(name).suffix.lower()
    if suffix in _ALWAYS_EXCLUDED_SUFFIXES:
        return True
    # Glob pattern check
    for pattern in _ALWAYS_EXCLUDED_GLOB_PATTERNS:
        if fnmatch.fnmatch(rel_path, pattern) or fnmatch.fnmatch(name, pattern):
            return True
    return False


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
    """Ordered unique relative paths to embed from request inputs."""
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

    if include_project_context:
        for rel in _collect_auto_files(project):
            _add(rel)
    for rel in ticket_files:
        _add(rel)
    for rel in context_files:
        _add(rel)
    if context_globs:
        for rel in _collect_glob_files(project, context_globs):
            _add(rel)
    return files_to_include


def _context_file_sections(
    project: Path, files_to_include: list[str]
) -> tuple[list[str], list[str]]:
    """Return ``(markdown_sections, included_files)`` for readable files."""
    sections: list[str] = []
    included_files: list[str] = []
    for rel in files_to_include:
        content = _read_file_content(project, rel)
        if content is None:
            continue
        lang = Path(rel).suffix.lstrip(".")
        sections.append(f"## {rel}\n\n```{lang}\n{content}\n```")
        included_files.append(rel)
    return sections, included_files


def _truncate_context_text(full_text: str, max_chars: int) -> tuple[str, bool, int]:
    """Return ``(text, truncated, total_chars_before)``."""
    if len(full_text) <= max_chars:
        return full_text, False, 0
    total_chars = len(full_text)
    annotation = f"\n\n... [context truncated at {max_chars} chars; {total_chars} total]"
    return full_text[: max_chars - len(annotation)] + annotation, True, total_chars


def build_project_context(
    project: Path,
    request: dict[str, Any],
) -> ContextResult | None:
    """Assemble project context from the ticket request inputs.

    Returns ``None`` when no context was requested so the caller can skip
    adding a context block without changing existing behaviour.

    The returned :class:`ContextResult` contains:
    - ``text``           — the assembled string ready to embed
    - ``included_files`` — relative paths of files whose content was added
    - ``truncated``      — whether the text was cut at ``max_context_chars``
    - ``total_chars``    — size before truncation (0 if not truncated)
    """
    if _context_nothing_requested(request):
        return None

    project = project.resolve()
    max_chars: int = int(request.get("max_context_chars") or DEFAULT_MAX_CONTEXT_CHARS)
    sections: list[str] = []

    tree = _read_file_tree(project)
    if tree:
        sections.append(f"## Project file tree\n\n```\n{tree}\n```")

    file_sections, included_files = _context_file_sections(
        project, _context_files_to_include(project, request)
    )
    sections.extend(file_sections)

    if not sections:
        return None

    full_text, truncated, total_chars = _truncate_context_text(
        "\n\n".join(sections), max_chars
    )
    return ContextResult(
        text=full_text,
        included_files=included_files,
        truncated=truncated,
        total_chars=total_chars,
    )
