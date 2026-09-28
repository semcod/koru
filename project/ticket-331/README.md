# Ticket331: Bind verification to the executed task

- **ID**: ticket-331
- **Owner**: agent:codex
- **Status**: IN_PROGRESS
- **Workflow state**: PUBLICATION

SESSION_EXECUTION_AUTHORIZATION: user requested a better solution for PLF099,
implementation/deployment/tests and continued twice. Continuation of the
accepted remaining criteria after merged ticket327/PR566. Canonical allocator
created this disjoint worktree; ticket330 owns ticket-command files. Preserve
primary changes and previous stashes; do not write the primary checkout.

## Acceptance criteria

- [x] AC-01: Result, completion receipt and failed-attempt accounting belong to
  the ticket actually driven, including failures and a changed next queue target.
  Matching verified completion does not require unrelated chat score; failing
  tests veto it. Unmeasured line counts remain unknown.
- [x] AC-02: Real Git, mocked transport, concurrent admission and fresh-process
  restart regressions prove the3-attempt bound and preserve PLF099 behavior.
- [ ] AC-03: Focused tests, Ruff and managed gate pass; independent exact-head
  protected publication and verified runtime. Do not equate commit with deploy.

Validation: 244 focused tests passed, including current-task attribution, finalizer
error handling, paid-call admission, concurrent reservations and fresh-process
restart. Ruff and managed governance passed. AC-03 still awaits exact-head
protected review and separately observed deployment.
