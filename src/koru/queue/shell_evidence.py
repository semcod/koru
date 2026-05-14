"""Format planfile ticket notes that capture shell executor output.

Each successful shell queue run can append a ``KORU-SHELL-RUN`` note via
``planfile ticket update <id> --note`` or ``-n`` (see
``planfile_ticket_note.append_shell_evidence_note``) so ``planfile ticket
show`` surfaces stdout/stderr. When the installed planfile CLI omits both
flags, the same payload is written under ``.planfile/.koru/runs/``.

Notes carry a fresh ``run_id`` (UUID fragment) so operators or tooling
can correlate duplicates if a step is retried.
"""

from __future__ import annotations

import json

SHELL_RUN_NOTE_TAG = "KORU-SHELL-RUN"
"""Marker prefix on the first line of every shell-evidence note."""


def _tail_stream(text: str, limit: int) -> tuple[str, bool]:
    """Return the tail of *text*, normalising newlines."""
    raw = text or ""
    norm = raw.replace("\r\n", "\n")
    if len(norm) <= limit:
        return norm, False
    return norm[-limit:], True


def format_shell_run_note(
    *,
    run_id: str,
    exit_code: int,
    stdout: str,
    stderr: str,
    max_stream_chars: int = 4000,
    max_total_chars: int = 12000,
) -> str:
    """Build a single planfile ``--note`` string for a finished shell step.

    The first line is ``KORU-SHELL-RUN`` plus compact JSON metadata
    (``run_id``, ``exit_code``, ``truncated``, original byte lengths).
    Remaining lines hold stdout/stderr sections; each stream is
    independently tail-truncated to *max_stream_chars* when oversized.
    The final string is hard-capped at *max_total_chars* for safety.
    """
    out_raw = stdout or ""
    err_raw = stderr or ""
    out_body, t_out = _tail_stream(out_raw, max_stream_chars)
    err_body, t_err = _tail_stream(err_raw, max_stream_chars)
    meta = {
        "run_id": run_id,
        "exit_code": exit_code,
        "truncated": t_out or t_err,
        "stdout_chars": len(out_raw),
        "stderr_chars": len(err_raw),
    }
    header = f"{SHELL_RUN_NOTE_TAG} {json.dumps(meta, sort_keys=True)}"
    body = (
        f"--- stdout ---\n{out_body if out_body else '(empty)'}\n\n"
        f"--- stderr ---\n{err_body if err_body else '(empty)'}"
    )
    text = f"{header}\n{body}"
    if len(text) <= max_total_chars:
        return text
    overhead = len(header) + 80
    budget = max(200, max_total_chars - overhead)
    clipped = text[:budget] + "\n… [koru: note hard truncated to max_total_chars]\n"
    return clipped[:max_total_chars]


__all__ = ["SHELL_RUN_NOTE_TAG", "format_shell_run_note"]
