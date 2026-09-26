# Ticket 226: Decompose god function scan_opencode_log_for_exhaustion

- **ID**: ticket-226
- **Owner**: claude
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-26

## Goal and scope

Address code smell: `God Function: scan_opencode_log_for_exhaustion` in
`src/koruapi/opencode_terminals.py:397` (PLF-052).

The scanner measures CC=8, fan-out=14, mutations=22 — it trips the code2llm
fan-out and mutation gates (most mutations come from the two tuple unpacks,
which the analyzer double-counts per target). Keep it a linear
resolve/read/scan loop: the bounded tail read (missing/unreadable file,
`max(0, size - max_bytes)` seek) moves to `_read_log_tail`, and the
per-match exhaustion check + provider marking + event dict build moves to
`_stream_error_event`, which reads the regex groups positionally
(`match.group(N)`) instead of unpacking `match.groups()`. The default log
path, empty result for missing/unreadable files, tail-only window,
exhaustion-only marking and the event dict shape are unchanged.

Session execution authorization: planfile PLF-052 queue handoff delivered the
implementation instruction (observed 2026-09-26).

## Acceptance criteria

- [x] AC-01: Scope is approved by a human owner (planfile PLF-052 queue handoff).
- [x] AC-02: `scan_opencode_log_for_exhaustion` and every touched or new helper
  measure fan-out <= 10, mutations <= 6 and CC <= 12 (code2llm god-function gates).
- [x] AC-03: `pytest -q tests/test_dashboard_terminals.py` passes (existing
  tests unchanged, new tests for missing file, tail-only window and
  non-exhaustion errors).
- [x] AC-04: No untouched function in the module crosses a god-function gate
  it did not already cross before this change.
- [x] AC-05: `bash project/governance-check.sh` passes with 0 errors.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
