# Ticket 139: Keep local publication script compatible with worktree planner CLI

- **ID**: ticket-139
- **Owner**: codex
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-15
- **GitHub issue**: https://github.com/semcod/koru/issues/186

## Goal and scope

The protected local publication script still passed the removed
`--workspace-root` option to the Wellmanifest v5 worktree planner. Update the
invocation to use the explicit primary-checkout argument required by the
current planner, preserving the deterministic `/workspace` layout assertion.

## Acceptance criteria

- [x] AC-01: The script passes the current planner CLI and retains v5 layout
  and `.subactor/leases` validation.
- [x] AC-02: Shell syntax, help output and governance pass after the change.
- [ ] AC-03: A frozen-head publication reaches the local OneDev phase.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
