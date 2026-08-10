# Ticket 005: Assign development toolchain ownership

- **ID**: ticket-005
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-08-10
- **Work classification**: `SERVICE / governance`

## Goal and scope

Assign Koru's canonical development DSL (`app.doql.less`) and deterministic
Python lockfile (`uv.lock`) to the existing integration workstream. Both files
are synchronized with `pyproject.toml`, but the adopted repository manifest
currently leaves them unowned and therefore blocks legitimate dependency
updates.

## Acceptance criteria

- [x] AC-01: The user authorized autonomous dependency updates without a fresh
  confirmation for each bounded repository change.
- [ ] AC-02: Integration owns `app.doql.less` and `uv.lock` in both ownership
  and integration-routing declarations.
- [ ] AC-03: The immutable manifest lock records the exact customized manifest
  digest and the governance gate passes without warnings.
- [ ] AC-04: No runtime, dependency value, public API, CI or Docker behavior is
  changed by this governance-only slice.

## Risk boundary

This ticket changes ownership metadata only. The dependent Goal update remains
isolated in ticket-004 and must be rebased onto this merged governance change.

## Participants

- Human participant: unresolved; no user-* file was created.
- Agent participant: [ai-codex.md](ai-codex.md)
