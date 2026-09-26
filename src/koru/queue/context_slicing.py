"""Focused slicing of oversized context files.

When a requested file exceeds ``LARGE_FILE_SLICE_THRESHOLD_CHARS`` and the
ticket request carries target symbol or line metadata, these helpers
narrow the embedded content to a focused slice — an AST window around the
target symbol for Python files, or a line window around the target line —
instead of dumping the whole file into a bounded prompt.

Split from ``koru.queue.context`` (PLF-039); the facade re-exports the
moved names so existing ``koru.queue.context`` imports stay stable.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path
from typing import Any, NamedTuple

# Files exceeding this size will be sliced when target symbol or line metadata is available
LARGE_FILE_SLICE_THRESHOLD_CHARS: int = 12_000


class _TargetRef(NamedTuple):
    """Resolved target symbol / line metadata for one context file."""

    symbol: str | None
    line: int | None


def _resolve_target_symbol_and_line(
    rel_path: str, request: dict[str, Any]
) -> _TargetRef:
    """Resolve target symbol name and line number for rel_path from request metadata."""
    symbol = request.get("target_symbol")
    line = request.get("target_line")
    if symbol is not None or line is not None:
        return _TargetRef(
            str(symbol) if symbol else None, int(line) if line is not None else None
        )

    # Inspect prompt and ticket_description for code smell / location markers
    text_corpus = " ".join(
        [
            str(request.get("prompt") or ""),
            str(request.get("ticket_description") or ""),
        ]
    )
    if not text_corpus:
        return _TargetRef(None, None)

    filename = Path(rel_path).name
    # Match path:line, e.g. vdisplay_client.py:2442 or src/foo.py:123
    line_pattern = rf"(?:[\w./\-]+/)?{re.escape(filename)}:(\d+)"
    m_line = re.search(line_pattern, text_corpus)
    if m_line and line is None:
        try:
            line = int(m_line.group(1))
        except ValueError:
            pass

    # Match symbol name in common reports (e.g. God Function: func_name or Function 'func_name')
    symbol_patterns = (
        r"`(?:God Function|Feature Envy|Long Method|Shotgun Surgery|Data Clump):\s*([a-zA-Z0-9_]+)`",
        r"(?:Function|Method|class|function|def)\s+['\"`]?([a-zA-Z0-9_]+)['\"`]?",
        r"`([a-zA-Z0-9_]+)`\s+with\s+CC=",
    )
    for pat in symbol_patterns:
        m_sym = re.search(pat, text_corpus)
        if m_sym and symbol is None:
            candidate = m_sym.group(1).strip()
            if candidate and not candidate.isdigit() and len(candidate) > 1:
                symbol = candidate
                break

    return _TargetRef(
        str(symbol) if symbol else None, int(line) if line is not None else None
    )


class _CodeSlice(NamedTuple):
    """Extracted source slice with its original line span."""

    text: str
    start_line: int
    end_line: int


def _extract_python_symbol_slice(
    content: str, symbol_name: str, context_lines: int = 15
) -> _CodeSlice | None:
    """Extract a focused AST slice around symbol_name in Python code."""
    try:
        tree = ast.parse(content)
    except SyntaxError:
        return None

    lines = content.splitlines()
    import_lines: list[str] = []
    # Collect top-level imports to preserve module context
    for node in tree.body:
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            end = getattr(node, "end_lineno", node.lineno)
            import_lines.extend(lines[node.lineno - 1 : end])
        elif not isinstance(node, ast.Expr):
            # Stop collecting imports once definition bodies start
            if len(import_lines) >= 20:
                break

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            if node.name == symbol_name:
                start = max(1, node.lineno - context_lines)
                end = min(len(lines), getattr(node, "end_lineno", node.lineno) + context_lines)
                header_parts = []
                if import_lines:
                    header_parts.append("\n".join(import_lines[:30]))
                header_parts.append(
                    f"# ... [focused AST slice for '{symbol_name}': lines {start}-{end} of {len(lines)}] ..."
                )
                body = "\n".join(lines[start - 1 : end])
                header_parts.append(body)
                return _CodeSlice("\n\n".join(header_parts), start, end)
    return None


def _extract_line_slice(
    content: str, target_line: int, window: int = 80
) -> _CodeSlice:
    """Extract a window of lines around target_line."""
    lines = content.splitlines()
    start = max(1, target_line - window)
    end = min(len(lines), target_line + window)
    header = f"# ... [focused slice around line {target_line}: lines {start}-{end} of {len(lines)}] ..."
    body = "\n".join(lines[start - 1 : end])
    return _CodeSlice(f"{header}\n\n{body}", start, end)


class _FocusedSlice(NamedTuple):
    """Focused replacement content for one file, plus its header note."""

    content: str
    note: str | None


def _focused_file_slice(
    rel: str,
    content: str,
    lang: str,
    request: dict[str, Any] | None,
) -> _FocusedSlice:
    """Return focused slice content for one file.

    When the file exceeds ``LARGE_FILE_SLICE_THRESHOLD_CHARS`` and target
    symbol or line metadata is present in ``request``, a focused slice is
    generated instead of dumping the entire file; otherwise the content is
    returned unchanged.
    """
    if not request or len(content) <= LARGE_FILE_SLICE_THRESHOLD_CHARS:
        return _FocusedSlice(content, None)

    target = _resolve_target_symbol_and_line(rel, request)
    if target.symbol and lang == "py":
        code_slice = _extract_python_symbol_slice(content, target.symbol)
        if code_slice:
            return _FocusedSlice(
                code_slice.text,
                f"focused slice for '{target.symbol}',"
                f" lines {code_slice.start_line}-{code_slice.end_line}",
            )
    elif target.line is not None:
        code_slice = _extract_line_slice(content, target.line)
        return _FocusedSlice(
            code_slice.text,
            f"focused slice around line {target.line},"
            f" lines {code_slice.start_line}-{code_slice.end_line}",
        )
    return _FocusedSlice(content, None)
