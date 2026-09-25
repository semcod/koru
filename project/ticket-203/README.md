# Ticket 203: Reduce cyclomatic complexity in ticket command service

- **ID**: ticket-203
- **Owner**: antigravity
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-25

## Goal and scope

Reduce cyclomatic complexity: `src.koru.ticket_command.service.run_ticket` (CC=35, limit 15) at
`src/koru/ticket_command/service.py:119` (PLF-022).

Extract focused helper functions for state folder initialization, prior state checking,
ticket state preparation, execution step, commit step, and publication/reporting steps.
Preserve exact execution lifecycle, locking, state caching, and error handling semantics.

## Acceptance criteria

- [x] AC-01: Scope is approved by a human owner (planfile PLF-022 queue handoff).
- [x] AC-02: `run_ticket` and all new helpers have CC <= 8 (Rank A or low B).
- [x] AC-03: Existing ticket command tests pass unchanged (`pytest -q tests/test_ticket_command.py tests/test_ticket_command_delivery.py tests/test_ticket_command_reporting.py`).
- [x] AC-04: Governance check passes with 0 errors (`bash project/governance-check.sh`).

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
