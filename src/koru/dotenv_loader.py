"""Minimal stdlib ``.env`` loader — no external dependency.

koru detects optional capabilities (``OPENROUTER_API_KEY``, etc.) via
``os.environ``. Many projects keep these in a ``.env`` file at the
project root, exported only by ``source .env`` or by a shell plugin.
When the user runs ``koru serve`` from a fresh shell, that file is not
yet loaded and koru reports false negatives (e.g. ``openrouter: no``
even though the key is in ``.env``).

This module reads ``<project>/.env`` (and ``<project>/.env.local`` if
present) and adds missing keys to ``os.environ``. Existing variables
take precedence — the goal is to make koru *see* what the user already
has, never to override an explicit env.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

# Order matters: ``.env`` is the public default, ``.env.local`` is a
# common pattern for developer-specific overrides.
_DEFAULT_FILES: tuple[str, ...] = (".env", ".env.local")

# ``KEY=value`` with optional ``export``, quoted values, inline ``#``
# comments. Mirrors python-dotenv's grammar closely enough for koru's
# detection needs without pulling in the dependency.
_LINE_RE = re.compile(
    r"""^
    \s*(?:export\s+)?              # optional `export `
    (?P<key>[A-Za-z_][A-Za-z0-9_]*) # KEY
    \s*=\s*
    (?P<value>
        "(?:[^"\\]|\\.)*"          # double-quoted
      | '(?:[^'\\]|\\.)*'          # single-quoted
      | [^#\n]*                     # bare value (stop at # or EOL)
    )
    \s*(?:\#.*)?                    # trailing comment
    $""",
    re.VERBOSE,
)


def _parse_value(raw: str) -> str:
    """Strip surrounding quotes and trailing whitespace from a raw value."""
    value = raw.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
        inner = value[1:-1]
        if value[0] == '"':
            # Process simple backslash escapes (\n, \t, \", \\).
            inner = (
                inner.replace(r"\n", "\n")
                .replace(r"\t", "\t")
                .replace(r"\r", "\r")
                .replace(r"\"", '"')
                .replace(r"\\", "\\")
            )
        return inner
    return value


def parse_dotenv(text: str) -> dict[str, str]:
    """Return the ``KEY=value`` pairs from a ``.env``-style text."""
    out: dict[str, str] = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        match = _LINE_RE.match(line)
        if not match:
            continue
        out[match.group("key")] = _parse_value(match.group("value"))
    return out


def load_dotenv(
    project: Path,
    *,
    files: tuple[str, ...] = _DEFAULT_FILES,
    override: bool = False,
) -> dict[str, str]:
    """Load ``.env`` files from ``project`` into ``os.environ``.

    Returns the dict of values that were actually applied (useful for
    logging / tests). Existing environment variables win unless
    ``override=True``.
    """
    project = project.resolve()
    applied: dict[str, str] = {}
    for name in files:
        path = project / name
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for key, value in parse_dotenv(text).items():
            if not override and key in os.environ:
                continue
            os.environ[key] = value
            applied[key] = value
    return applied
