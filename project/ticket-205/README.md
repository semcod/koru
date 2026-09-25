# Ticket 205: Reduce cyclomatic complexity in delegate_ticket_from_dashboard

- **ID**: ticket-205
- **Owner**: claude
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-25

## Goal and scope

Reduce cyclomatic complexity: `src.koruapi.dashboard_tickets.delegate_ticket_from_dashboard` (CC=30, limit 15) at
`src/koruapi/dashboard_tickets.py:368` (PLF-024).

Extract focused per-field mutation helpers (executor target, delegation defaults, prompt
addition, operator notes, priority, queue, llm-ready label) plus a shared `_mapping_slot`
guard for the repeated setdefault/isinstance pattern. Preserve identical sprint-file
mutation, changes reporting, history entries, and result payload.

## Acceptance criteria

- [x] AC-01: Scope is approved by a human owner (planfile PLF-024 queue handoff).
- [x] AC-02: `delegate_ticket_from_dashboard` and all new helpers have CC <= 9 (Rank A or low B).
- [x] AC-03: `pytest -q tests/test_dashboard_ticket_handlers.py tests/test_serve.py` passes unchanged.
- [x] AC-04: `code2llm` re-run reports no complexity finding for `delegate_ticket_from_dashboard`.
- [x] AC-05: `bash project/governance-check.sh` passes with 0 errors.

## Delivery note

Wave 1 (PR #415, merged as 872925eb) cut CC 30 -> 4 but kept a 9-helper
accumulator layout that reintroduces code2llm god-function (fan-out=15,
mutations=12) and shotgun-surgery ('changes' spans 8) findings. Wave 2 replaces
it with `_field_update`-based helpers returning change lists, a
`_SprintTicketHit` NamedTuple and extracted `_delegation_change_sets` /
`_delegation_result`, leaving only the five pre-existing dashboard_tickets
smells in code2llm output. AC-04 was verified against wave 2 only.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
