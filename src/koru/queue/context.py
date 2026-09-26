"""Project context assembly for executor.kind=llm tickets.

Builds a bounded, secret-free snapshot of repository files so that an
LLM executor can answer ticket prompts with evidence from the actual
project rather than making generic assumptions.

Opt-in contract (ticket ``inputs`` fields):
  include_project_context: true   – auto-include file tree + common project files
  context_files: [path, ...]      – explicit file list (relative to project root)
  context_globs: ["src/**/*.py"]  – glob patterns (relative to project root)
  max_context_chars: 32000        – optional explicit per-ticket cap

Security defaults:
  - Secrets, credentials, private keys, .env files are *always* excluded.
  - node_modules, vendor, generated files, and VCS internals are excluded.
  - Opt-in for any sensitive path is not supported; the exclusions are
    non-negotiable so context assembly can never leak secrets.

Module layout (PLF-039): the security exclusion policy lives in
:mod:`koru.queue.context_exclusions`, file selection and safe reads in
:mod:`koru.queue.context_files`, and focused slicing of oversized files
in :mod:`koru.queue.context_slicing`. This module keeps the assembly
pipeline (:func:`build_project_context` → ``_context_file_sections`` →
``_truncate_context_text``) and re-exports the moved names (redundant
aliases) so every pre-split ``koru.queue.context`` import — including the
private ``_is_excluded`` and ``_resolve_target_symbol_and_line`` used by
tests — keeps working unchanged.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from koru.queue.context_exclusions import _is_excluded as _is_excluded
from koru.queue.context_files import _collect_auto_files as _collect_auto_files
from koru.queue.context_files import _collect_glob_files as _collect_glob_files
from koru.queue.context_files import (
    _context_files_to_include as _context_files_to_include,
)
from koru.queue.context_files import (
    _context_nothing_requested as _context_nothing_requested,
)
from koru.queue.context_files import _read_file_content as _read_file_content
from koru.queue.context_files import _read_file_tree as _read_file_tree
from koru.queue.context_slicing import (
    LARGE_FILE_SLICE_THRESHOLD_CHARS as LARGE_FILE_SLICE_THRESHOLD_CHARS,
)
from koru.queue.context_slicing import _CodeSlice as _CodeSlice
from koru.queue.context_slicing import _extract_line_slice as _extract_line_slice
from koru.queue.context_slicing import (
    _extract_python_symbol_slice as _extract_python_symbol_slice,
)
from koru.queue.context_slicing import _focused_file_slice as _focused_file_slice
from koru.queue.context_slicing import _FocusedSlice as _FocusedSlice
from koru.queue.context_slicing import (
    _resolve_target_symbol_and_line as _resolve_target_symbol_and_line,
)
from koru.queue.context_slicing import _TargetRef as _TargetRef

# Default maximum context characters applied when a ticket does not specify an explicit limit
DEFAULT_MAX_CONTEXT_CHARS: int = 32_000

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


def _context_file_sections(
    project: Path,
    files_to_include: list[str],
    request: dict[str, Any] | None = None,
) -> tuple[list[str], list[str]]:
    """Return ``(markdown_sections, included_files)`` for readable files.

    Oversized files are narrowed to a focused slice by
    :func:`_focused_file_slice` when target symbol or line metadata is
    present.
    """
    sections: list[str] = []
    included_files: list[str] = []
    for rel in files_to_include:
        content = _read_file_content(project, rel)
        if content is None:
            continue
        lang = Path(rel).suffix.lstrip(".")
        focused = _focused_file_slice(rel, content, lang, request)
        header = f"## {rel}" + (f" ({focused.note})" if focused.note else "")
        sections.append(f"{header}\n\n```{lang}\n{focused.content}\n```")
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
    sections: list[str] = []

    file_sections, included_files = _context_file_sections(
        project, _context_files_to_include(project, request), request=request
    )
    sections.extend(file_sections)

    # The tree is useful orientation, but it must not evict explicitly named
    # source files from a bounded prompt.
    tree = _read_file_tree(project)
    if tree:
        sections.append(f"## Project file tree\n\n```\n{tree}\n```")

    if not sections:
        return None

    full_text = "\n\n".join(sections)
    max_chars = request.get("max_context_chars")
    if max_chars is None:
        max_chars = DEFAULT_MAX_CONTEXT_CHARS

    if int(max_chars) > 0:
        full_text, truncated, total_chars = _truncate_context_text(
            full_text, int(max_chars)
        )
    else:
        truncated, total_chars = False, 0

    visible_files = [
        rel for rel in included_files if f"## {rel}" in full_text
    ]
    return ContextResult(
        text=full_text,
        included_files=visible_files,
        truncated=truncated,
        total_chars=total_chars,
    )
