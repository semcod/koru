# Ticket 201: Reduce cyclomatic complexity in hydrate_todo2code_ticket

- **ID**: ticket-201
- **Owner**: claude
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-25

## Goal and scope

Reduce cyclomatic complexity: `src.koru.queue.ticket_templates.hydrate_todo2code_ticket`
(CC=25, limit 15) at `src/koru/queue/ticket_templates.py:268` (PLF-020).

Extract focused helpers for the todo2code match guard, default inputs, contract
resolution, executor-authority demotion, diagnostic-id validation, verify-command
fill, and label normalization. Preserve exact hydration behavior, including the
governance demotion of uncontracted legacy llm/automatic executors.

## Acceptance criteria

- [x] AC-01: Scope is approved by a human owner (planfile PLF-020 queue handoff).
- [x] AC-02: `hydrate_todo2code_ticket` and all new helpers have CC <= 8.
- [x] AC-03: Existing todo2code/queue tests pass unchanged (`pytest -q tests/test_todo2code_autonomous_gate.py tests/test_subactor_repair_ticket_template.py`).
- [x] AC-04: code2llm no longer reports `hydrate_todo2code_ticket` above the CC limit.
- [x] AC-05: Governance check passes with 0 errors (`bash project/governance-check.sh`).

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
