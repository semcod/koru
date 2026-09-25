# Ticket 207: Reduce cyclomatic complexity in terminal prompt

- **ID**: ticket-207
- **Owner**: claude
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-25

## Goal and scope

Reduce cyclomatic complexity: `src.koruapi.opencode_terminals.terminal_prompt` (CC=29, limit 15) at
`src/koruapi/opencode_terminals.py:1010` (PLF-026).

Extract focused helpers for target resolution (`_resolve_terminal_target`), session creation with
failover (`_create_session_with_failover`, `_retry_session_failover`), and prompt execution with
failover (`_send_prompt_with_failover`, `_retry_prompt_failover`). Preserve identical error responses,
provider exhaustion marking, model failover retry logic, and result payload formatting.

## Acceptance criteria

- [x] AC-01: Scope is approved by a human owner (planfile PLF-026 queue handoff).
- [x] AC-02: `terminal_prompt` and all new helpers have CC <= 9 (Rank A or low B).
- [x] AC-03: `pytest -q tests/test_dashboard_terminals.py tests/test_opencode_serve_scan.py` passes unchanged.
- [x] AC-04: `code2llm` re-run reports no complexity finding for `terminal_prompt`.
- [x] AC-05: `bash project/governance-check.sh` passes with 0 errors.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
