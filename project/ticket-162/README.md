# Ticket 162: queue-defers-human-executor-tickets

- **ID**: ticket-162
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-17

## Goal and scope

SESSION_EXECUTION_AUTHORIZATION: the user asked to fix the detected koru
autonomy problems ("naprawiaj"), including the queue stalling in
`waiting_input` behind human-executor tickets while machine-runnable work
remained open.

`parse_next_ticket` picks the highest-priority open ticket regardless of
executor kind. A `human` ticket (including tickets with no `executor.kind`,
which `_resolve_executor_kind` maps to human) returns `waiting_input`, a
loop-terminal status — so one unanswered human ticket parked the whole drain
behind it (observed: queue stuck on STARTER-578 while llm tickets waited).

Fix: in non-interactive mode, eligible tickets are partitioned by executor
kind — machine-runnable tickets are served first and a human ticket is
returned only when nothing else remains, preserving `waiting_input` as the
correct terminal state. Interactive mode and the operator-queue deferral are
unchanged.

## Acceptance criteria

- [x] AC-01: Scope is approved by the user's explicit execution request.
- [x] AC-02: Non-interactive selection serves llm/shell tickets ahead of a
      higher-priority human ticket (regression tests).
- [x] AC-03: A queue with only human tickets still yields the human ticket
      (`waiting_input`), and executor-less tickets count as human.
- [x] AC-04: Interactive mode selection order is unchanged.
- [x] AC-05: `./project/governance-check.sh` reports GOV-PASS for this
      ticket branch.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
