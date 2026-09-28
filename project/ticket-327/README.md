# Ticket 327: verified autonomous execution and bounded recovery

- **ID**: ticket-327
- **Owner**: agent:codex
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-28

## Goal and scope

SESSION_EXECUTION_AUTHORIZATION: user requested implementing/deploying and testing
a better solution after the PLF099 diagnosis. Explicit handoff of new primary
changes received. Project-specific old autonomous loop stopped with receipt;
primary changes preserved by peer stash, then primary reconciled to merged326.
Earlier stashes preserved. Allocate327 owns only its declared paths.

## Acceptance criteria

- [x] AC-01: Actual temporary-Git regressions cover dirty/staged/untracked/committed
  deltas; persistent failed/no-effect budget blocks repeat drives after restart.
- [x] AC-02: Requested and actual client/provider/model are distinct; failed
  verification cannot be called completed; PLF099 complexity <=15 with behavior tests.
- [x] AC-03: Focused tests, Ruff and managed gate pass; protected exact-head delivery.

## Remaining work

Merged326 does not yet run comparative API/CLI fixtures or integrate the queue;
retain a separate followup. This ticket does not waive those criteria.
