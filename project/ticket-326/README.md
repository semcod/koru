# Ticket 326: daily benchmark routing

- **ID**: ticket-326
- **Owner**: agent:codex
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-28

## Goal and scope

SESSION_EXECUTION_AUTHORIZATION: user explicitly requested detailed tool-class
router refactor and one daily benchmark for simple, complex and other tasks.
User handed off primary changes and subsequent configurator delta; preserved in
stashes af33024b21ec88e4d3de2d07523f03cd6de9dad8 and
4237e4edf8ff58a2e032e651d43fca1486eb1fdb. This canonical worktree owns only the
allocated scope. Prior Twinerd publication and Koru560/344 requests remain queued.

## Acceptance criteria

- [x] AC-01: Explicit selection wins; capability-aware independently validated
  fresh ranking distinguishes task difficulty/kind and client/model/transport.
- [x] AC-02: A transactional daily claim prevents duplicate campaigns under
  concurrent timer/CLI, restart and local timezone/DST boundaries.
- [x] AC-03: Same isolated fixtures, independent validators, truthful probe
  statuses, CLI explanation/history and configurable daily user timer.

## Tracking boundary

Intent joins first material code commit; no carrier-only history.
