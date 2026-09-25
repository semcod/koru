# Ticket 204: Reduce cyclomatic complexity in sse log stream

- **ID**: ticket-204
- **Owner**: antigravity
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-25

## Goal and scope

Reduce cyclomatic complexity: `src.koruapi.dashboard_logs.sse_log_stream` (CC=25, limit 15) at
`src/koruapi/dashboard_logs.py:118` (PLF-023).

Extract focused helpers for initial offset checking and incremental log tailing/parsing.
Preserve exact SSE formatting, keepalive interval, rotation handling, and level filtering semantics.

## Acceptance criteria

- [x] AC-01: Scope is approved by a human owner (planfile PLF-023 queue handoff).
- [x] AC-02: `sse_log_stream` and all new helpers have CC <= 9 (Rank A or low B).
- [x] AC-03: Existing dashboard log streaming tests pass unchanged (`pytest -q tests/test_dashboard_logs.py`).
- [x] AC-04: Governance check passes with 0 errors (`bash project/governance-check.sh`).

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
