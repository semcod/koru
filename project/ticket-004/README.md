# Ticket 004: Require Goal 2.1.292 version-carrier fix

- **ID**: ticket-004
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-08-10
- **Work classification**: `SERVICE / integration`

## Goal and scope

Raise Koru's Goal development-tool floor from 2.1.264 to 2.1.292 in the
canonical dependency declarations and refresh the lockfile. Version 2.1.292
includes the synchronized-version transition boundary fix and detects only
writable Python version declarations, including conventional version modules.

## Acceptance criteria

- [x] AC-01: The user explicitly requested testing, publication and updating
  Goal in dependent projects, with autonomous continuation.
- [ ] AC-02: `pyproject.toml` and its DSL source require `goal>=2.1.292` in
  every existing Goal dependency slot.
- [ ] AC-03: `uv.lock` resolves Goal 2.1.292 from the public index and passes
  `uv lock --check`.
- [ ] AC-04: Dependency-focused validation and repository governance pass.

## Risk boundary

This is a development-tool floor and lock refresh only. It does not add a new
runtime dependency, change Koru APIs, alter queue/autonomy behavior or modify
generated analysis snapshots.

## Session authorization

The user authorized this concrete dependency update and autonomous execution
on 2026-08-10. No fresh confirmation is required for the bounded paths in the
accepted intent.

## Participants

- Human participant: unresolved; no user-* file was created by this script.
- Agent participant: [ai-codex.md](ai-codex.md)
