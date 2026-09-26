"""Non-negotiable security exclusions for project context assembly.

These tables and the :func:`_is_excluded` predicate decide which repository
paths may never appear in context output handed to an LLM executor:
secrets and credentials, VCS internals, generated files, dependency trees
and caches. The policy is deliberately not configurable — opt-in for any
sensitive path is not supported so context assembly can never leak secrets.

Split from ``koru.queue.context`` (PLF-039); the facade re-exports
``_is_excluded`` so existing ``koru.queue.context`` imports stay stable.
"""

from __future__ import annotations

import fnmatch
from pathlib import Path

_ALWAYS_EXCLUDED_NAMES: frozenset[str] = frozenset(
    {
        # Secrets / credentials
        ".env",
        "secrets",
        "credentials",
        # VCS & worktrees
        ".git",
        ".worktrees",
        # Generated / binary / large dependency trees / internal caches
        "node_modules",
        "vendor",
        "__pycache__",
        ".venv",
        "venv",
        "dist",
        "build",
        ".eggs",
        ".code2llm_cache",
        ".dirac-symbol-index",
        ".koru",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
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
    # Databases / dumps / caches
    ".sqlite",
    ".db",
    ".sql",
    ".pkl",
    ".pickle",
    ".parquet",
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
    ".worktrees/**",
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
    ".code2llm_cache/**",
    ".dirac-symbol-index/**",
    ".koru/**",
    ".pytest_cache/**",
    ".mypy_cache/**",
    ".ruff_cache/**",
    "*.pkl",
    "*.pickle",
    "*.parquet",
    ".coverage",
    "coverage.xml",
    "*.log",
)


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
