# Ticket 005: Assign development toolchain ownership

- **ID**: ticket-005
- **Owner**: unresolved:human
- **Status**: DONE
- **Workflow state**: DONE
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
- [x] AC-02: Integration owns `app.doql.less` and `uv.lock` in both ownership
  and integration-routing declarations.
- [x] AC-03: The immutable manifest lock records the exact customized manifest
  digest and the governance gate passes without warnings.
- [x] AC-04: No runtime, dependency value, public API, CI or Docker behavior is
  changed by this governance-only slice.

## Delivery evidence

- PR: `semcod/koru#18`.
- Approved exact head: `9ebe4f5dd72740008e5ced1824ece60a428f21e0`.
- Validator run: `31387825764`; identity: `ifuri-validator-agent[bot]`.
- Merge commit: `ec58ffe7ebc917b4aa5acfc3eb6060734671e608`.

## Validation evidence

- Customized manifest SHA-256:
  `911bb4de37bc02c01a4f5337e3318ff0620419e02b83213c4129841c8c78a14c`.
- Repository governance: 0 errors, 0 warnings; `git diff --check`: PASS.
- Hosted `smoke` and exact-head validation: PASS.

## Risk boundary

This ticket changes ownership metadata only. The dependent Goal update remains
isolated in ticket-004 and must be rebased onto this merged governance change.

## Participants

- Human participant: unresolved; no user-* file was created.
- Agent participant: [ai-codex.md](ai-codex.md)
