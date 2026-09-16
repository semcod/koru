# Ticket 144: Promote monag backlog whenever the autonomous queue is idle

- **ID**: ticket-144
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-15

## Goal and scope

SESSION_EXECUTION_AUTHORIZATION: the user said "kontynuuj, zbadaj autonomie"
after approving and merging ticket-143.

Ticket-143 placed monag backlog promotion inside the idle discovery fallback
chain. That chain only runs when `scan_after_idle_queue` is enabled, which is
`false` by default (`SCAN_AFTER_IDLE_QUEUE`) and only turned on by an autonomy
strategy. The live `maskservice/c2004` loop never reached it in 30 hours while
its queue stayed idle and its `backlog` sprint held 10 open `ready` tickets.
Promotion must run for every idle queue; when it promoted work, idle scan and
paid discovery are skipped for that cycle.

## Acceptance criteria

- [x] AC-01: The user's explicit request approves the bounded scope.
- [x] AC-02: An idle queue runs promotion regardless of
      `scan_after_idle_queue`; a non-idle queue never does; promoted tickets
      skip the idle scan; the discovery chain no longer calls monag.
- [x] AC-03: Focused tests, Ruff and governance validation pass.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
