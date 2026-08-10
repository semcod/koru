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
- [x] AC-02: `pyproject.toml` and its DSL source require `goal>=2.1.292` in
  every existing Goal dependency slot.
- [x] AC-03: `uv.lock` resolves Goal 2.1.292 from the public index and passes
  `uv lock --check`.
- [x] AC-04: Dependency-focused validation and repository governance pass.
- [ ] AC-05: Goal recognizes the complete existing 0.1.459 prebump without an
  additional bump and the protected release PR passes hosted smoke and
  exact-head validation.
- [ ] AC-06: Goal publishes Koru 0.1.459 only from merged `main`, and a fresh
  public-index environment resolves that exact version.

## Delivery evidence

- PR: `semcod/koru#19`.
- Approved exact head: `340a4fe8ef7f443412133c28cb00d107c5e75633`.
- Validator run: `31388422059`; identity: `ifuri-validator-agent[bot]`.
- Merge commit: `9b5b3d6c60b302aff1748d6afae9ec9a4b1b47df`.

## Validation evidence

- `uv lock --check`: PASS; locked/imported Goal version: 2.1.292.
- `tests/test_dev_sync.py`: 4 passed.
- `tests/test_dependency_boundary_inventory.py`: 8 passed, 735 subtests.
- Repository governance: 0 errors, 0 warnings; hosted `smoke`: PASS.

## Risk boundary

This is a development-tool floor and lock refresh only. It does not add a new
runtime dependency, change Koru APIs, alter queue/autonomy behavior or modify
generated analysis snapshots.

## Session authorization

The user authorized this concrete dependency update and autonomous execution
on 2026-08-10. No fresh confirmation is required for the bounded paths in the
accepted intent.

The same user request explicitly includes testing and publication. Goal
2.1.292 revealed an existing complete 0.1.459 prebump and unreleased package
source after v0.1.456; publishing that already-selected version is therefore
part of this integration completion, not a second version increment.

## Participants

- Human participant: unresolved; no user-* file was created by this script.
- Agent participant: [ai-codex.md](ai-codex.md)
