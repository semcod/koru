# Ticket 198: Reduce cyclomatic complexity in parse_next_ticket

- **ID**: ticket-198
- **Owner**: antigravity
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-25

## Goal and scope

Reduce the cyclomatic complexity of `src.koru.queue.ticket.parse_next_ticket`
from CC=26 to <= 15 (STARTER-741 / issue #381).

Extract focused helper functions for payload loading, single ticket matching,
runnable ticket filtering, priority sorting, and candidate selection. Preserve
exact semantics, priority order, and deferred human ticket handling.

## Acceptance criteria

- [x] AC-01: Scope is approved by a human owner.
- [x] AC-02: `parse_next_ticket` cyclomatic complexity drops from 26 to <= 15 with all helpers <= 15.
- [x] AC-03: Existing unit and regression tests pass without changes.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
