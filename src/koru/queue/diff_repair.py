"""Turn an agent's reply into a diff git will accept.

Models produce unified diffs with reliable defects: fenced in prose, missing
the ``---``/``+++`` headers, hunk ranges off by one. Those are all derivable
from the diff body, so they are repaired here rather than costing a retry.
What is *not* repaired is anything ambiguous — a hunk line with no marker
could be context, an addition or a deletion, and guessing would risk writing
the wrong change into someone's code.

Pure text handling: no filesystem, no git, no network.
"""

from __future__ import annotations

import re

_FENCE_RE = re.compile(
    r"```(?:diff|patch)?\s*\n(?P<body>.*?)(?:\n```|\Z)",
    re.DOTALL,
)


_DIFF_START_RE = re.compile(r"^(diff --git |--- )", re.MULTILINE)


_HUNK_RE = re.compile(
    r"^@@ -(?P<old_start>\d+)(?:,(?P<old_len>\d+))? \+(?P<new_start>\d+)(?:,(?P<new_len>\d+))? @@(?P<tail>.*)$",
)


_GIT_HEADER_RE = re.compile(r"^diff --git a/(?P<old>.+?) b/(?P<new>.+?)\s*$")


_SYMLINK_MODE_RE = re.compile(r"^(?:new file mode|new mode) 120000\s*$", re.MULTILINE)


def extract_unified_diff(text: str) -> str | None:
    """Pull a unified diff out of an agent's stdout.

    Agents habitually wrap diffs in code fences and add commentary, so accept
    both fenced and bare output. Returns None when the reply contains no diff,
    which includes the explicit ``NO-PATCH:`` refusal.
    """
    if not text:
        return None
    for match in _FENCE_RE.finditer(text):
        body = match.group("body")
        if _DIFF_START_RE.search(body):
            return _normalize_diff(body)
    if _DIFF_START_RE.search(text):
        start = _DIFF_START_RE.search(text)
        assert start is not None
        return _normalize_diff(text[start.start():])
    return None


def _normalize_diff(body: str) -> str:
    """Trim trailing fences/prose and guarantee the single trailing newline
    ``git apply`` expects."""
    lines = body.splitlines()
    while lines and lines[-1].strip() in {"", "```"}:
        lines.pop()
    return "\n".join(_repair_hunk_counts(_repair_missing_file_headers(lines))) + "\n"


def _repair_hunk_counts(lines: list[str]) -> list[str]:
    """Recompute ``@@`` line counts from the hunk body.

    Models miscount hunk lengths routinely — one line off makes ``git apply``
    reject the whole patch as "corrupt patch at line N". The body is the
    authoritative content and the counts are derived from it, so recomputing
    them is a safe normalisation rather than a guess.
    """
    repaired = list(lines)
    for index, line in enumerate(repaired):
        match = _HUNK_RE.match(line)
        if not match:
            continue
        old_count = 0
        new_count = 0
        for body_line in repaired[index + 1:]:
            if body_line.startswith(("@@", "diff --git", "--- ", "+++ ")):
                break
            if body_line.startswith("\\"):  # "\ No newline at end of file"
                continue
            if body_line.startswith("+"):
                new_count += 1
            elif body_line.startswith("-"):
                old_count += 1
            else:  # context line (a bare empty line counts as context too)
                old_count += 1
                new_count += 1
        repaired[index] = (
            f"@@ -{match.group('old_start')},{old_count} "
            f"+{match.group('new_start')},{new_count} @@{match.group('tail')}"
        )
    return repaired


def _repair_missing_file_headers(lines: list[str]) -> list[str]:
    """Insert ``---``/``+++`` lines when an agent omits them.

    Models routinely emit a ``diff --git`` header followed straight by a
    ``@@`` hunk, which ``git apply`` rejects as "patch fragment without
    header". The paths are already in the ``diff --git`` line, so the headers
    can be reconstructed deterministically rather than by re-prompting.
    """
    repaired: list[str] = []
    for index, line in enumerate(lines):
        repaired.append(line)
        match = _GIT_HEADER_RE.match(line)
        if not match:
            continue
        following = next(
            (candidate for candidate in lines[index + 1:] if candidate.strip()),
            "",
        )
        if following.startswith("@@"):
            repaired.append(f"--- a/{match.group('old')}")
            repaired.append(f"+++ b/{match.group('new')}")
    return repaired


def symlink_creations(diff: str) -> bool:
    """Whether a diff creates a symlink or converts a file into one.

    ``git apply`` rejects ``../`` paths but happily creates a link pointing
    anywhere on the filesystem, which hands an agent-authored patch a way out
    of the workspace it was scoped to. Legitimate uses exist, so this is a
    policy question rather than a hard error — see ``symlinks_allowed``.
    """
    return bool(_SYMLINK_MODE_RE.search(diff))


