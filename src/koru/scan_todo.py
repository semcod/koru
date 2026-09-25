"""TODO / FIXME marker scanning engine for repository signals.

Provides pure functions for tokenizing Python comments, filtering ignore patterns,
and scanning directory trees for work-marker backlog tickets. Designed as a clean
atom that can be bound to or replaced by a high-performance native (Rust/PyO3)
scanner.
"""

from __future__ import annotations

import fnmatch
import io
import re
import tokenize
from collections import Counter
from collections.abc import Sequence
from pathlib import Path

from koru.scan_types import Suggestion

MARKER_RE = re.compile(r"\b(TODO|FIXME|XXX|HACK)\b[: ]")

DEFAULT_SCAN_EXCLUDES: frozenset[str] = frozenset(
    {
        ".git",
        "__pycache__",
        ".venv",
        ".venv-test",
        "venv",
        "node_modules",
        "build",
        "dist",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        ".code2llm_cache",
        ".playwright-browsers",
    },
)


def count_todo_markers(text: str) -> int:
    """Count TODO/FIXME/XXX/HACK markers that live in *comments* only.

    A work-marker is a comment convention (``# TODO: ...``). Counting the bare
    regex across the whole file also matches the words inside string literals
    and report labels — e.g. redsl, whose domain vocabulary is literally
    ``"TODO issues before/after"`` — producing false cleanup tickets on every
    scan. Tokenizing and inspecting only COMMENT tokens removes that noise.
    Files that fail to tokenize (syntax errors, py2, partial edits) fall back to
    the whole-text regex so genuine markers are never silently dropped.
    """
    try:
        comments = [
            tok.string for tok in tokenize.generate_tokens(io.StringIO(text).readline) if tok.type == tokenize.COMMENT
        ]
    except (tokenize.TokenError, IndentationError, SyntaxError, ValueError):
        return len(MARKER_RE.findall(text))
    return sum(len(MARKER_RE.findall(c)) for c in comments)


def load_koruignore_patterns(project: Path) -> tuple[str, ...]:
    """Load optional scan ignore patterns from ``.koruignore``.

    The format is intentionally minimal: one glob pattern per line,
    blank lines and ``#`` comments are ignored.
    """
    ignore_file = project / ".koruignore"
    if not ignore_file.is_file():
        return ()
    try:
        lines = ignore_file.read_text(encoding="utf-8", errors="ignore").splitlines()
    except OSError:
        return ()

    patterns: list[str] = []
    for raw in lines:
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("./"):
            line = line[2:]
        elif line.startswith("/"):
            line = line[1:]
        patterns.append(line)
    return tuple(patterns)


def is_koruignored(rel_path: Path, patterns: Sequence[str]) -> bool:
    """Return ``True`` when ``rel_path`` matches a ``.koruignore`` pattern."""
    if not patterns:
        return False

    rel = rel_path.as_posix()
    basename = rel_path.name
    for pattern in patterns:
        if not pattern:
            continue

        if pattern.endswith("/"):
            prefix = pattern.rstrip("/")
            if rel == prefix or rel.startswith(f"{prefix}/"):
                return True
            continue

        if fnmatch.fnmatch(rel, pattern):
            return True
        # Bare filename patterns should match in any directory.
        if "/" not in pattern and fnmatch.fnmatch(basename, pattern):
            return True

    return False


def count_todo_markers_in_project(
    project: Path,
    *,
    min_per_file: int = 3,
    max_files_walked: int = 2_000,
    excludes: frozenset[str] = DEFAULT_SCAN_EXCLUDES,
) -> Counter[str]:
    """Pure scan engine: walk project files and count markers meeting min threshold."""
    counts: Counter[str] = Counter()
    koruignore_patterns = load_koruignore_patterns(project)
    walked = 0
    for path in project.rglob("*.py"):
        walked += 1
        if walked > max_files_walked:
            break
        if any(part in excludes for part in path.parts):
            continue
        rel_path = path.relative_to(project)
        if is_koruignored(rel_path, koruignore_patterns):
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        n = count_todo_markers(text)
        if n >= min_per_file:
            counts[str(rel_path)] = n
    return counts


def scan_todo_markers(
    project: Path,
    *,
    min_per_file: int = 3,
    max_files_walked: int = 2_000,
) -> list[Suggestion]:
    """Count TODO/FIXME/XXX/HACK per Python file; suggest cleanup tickets.

    ``min_per_file`` filters out trivial cases — most repos accumulate a
    handful of historical TODOs that are not worth surfacing.
    """
    counts = count_todo_markers_in_project(
        project,
        min_per_file=min_per_file,
        max_files_walked=max_files_walked,
    )
    return [
        Suggestion(
            signal="todo_markers",
            title=f"Resolve {n} TODO/FIXME markers in {rel_path}",
            description=(
                f"Static scan found **{n}** TODO/FIXME/XXX/HACK markers "
                f"in `{rel_path}`. Either address them or convert each into "
                "an explicit planfile ticket so backlog stays honest."
            ),
            priority="low",
            labels=("cleanup", "scan"),
            files=(rel_path,),
        )
        for rel_path, n in counts.most_common(10)
    ]
