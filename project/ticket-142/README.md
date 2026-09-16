# Ticket 142: Document adopted Wellmanifest standards in AGENTS instructions

- **ID**: ticket-142
- **Owner**: codex
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-15

## Goal and scope

Adopt the latest verified `wellmanifest/new-project` release through Goal so
the managed host instructions and governance runtime are refreshed as one
immutable package. This resolves the `AGENTS.md` managed-file drift boundary;
the adoption process, not a hand-edited lock, remains authoritative. The
target-specific standard map stays derived from
`.governance/standard-adoption.json`.

SESSION_EXECUTION_AUTHORIZATION: the user explicitly requested execution,
push and merge in this conversation.

## Acceptance criteria

- [ ] AC-01: The latest verified standard package is adopted through the
      managed updater and its immutable lock is regenerated.
- [ ] AC-02: Refreshed host instructions identify the machine-readable
      adoption authority without duplicating policy prose.
- [ ] AC-03: Managed governance, documentation checks and protected
      exact-head publication pass.

## Blocker

Ticket-065 is still `IN_PROGRESS` in its canonical worktree and has an open
PR #249. Its accepted write scope includes `.governance/manifest.json`, which
overlaps the atomic standard-adoption update required here. Resume ticket 142
after ticket-065 reaches a protected terminal receipt, or after its owner
provides an accepted handoff/reconciliation.

**Resolved 2026-09-16**: ticket-065 reached its terminal receipt — PR #249
merged as of 07:15Z, branch deleted, workspace released. The recorded
SESSION_EXECUTION_AUTHORIZATION (execution, push, merge) is reaffirmed by the
owner's "tak" in the resuming session. Resuming under D-142-0001's
future route: refresh the exact head against main, re-run all gates, and keep
the protected Validator as the only merge authority.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
