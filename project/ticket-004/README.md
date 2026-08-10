# Ticket 004: Harden the Goal-based Koru release

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

After 0.1.459 publication, verify the actual public wheel rather than only the
source checkout. That smoke exposed an undeclared runtime dependency:
`koru --version` imports `Draft202012Validator` through
`koru.proposal_envelope`, but `jsonschema` was present only in development
groups. Declare the existing requirement in canonical runtime metadata and
publish the Goal-selected corrective release 0.1.460.

## Acceptance criteria

- [x] AC-01: The user explicitly requested testing, publication and updating
  Goal in dependent projects, with autonomous continuation.
- [x] AC-02: `pyproject.toml` and its DSL source require `goal>=2.1.292` in
  every existing Goal dependency slot.
- [x] AC-03: `uv.lock` resolves Goal 2.1.292 from the public index and passes
  `uv lock --check`.
- [x] AC-04: Dependency-focused validation and repository governance pass.
- [x] AC-05: Goal recognizes the complete existing 0.1.459 prebump without an
  additional bump and the protected release PR passes hosted smoke and
  exact-head validation.
- [x] AC-06: Goal publishes Koru 0.1.459 only from merged `main`; public-index
  metadata/import resolve 0.1.459 and the public-wheel CLI smoke records the
  missing `jsonschema` dependency instead of hiding it.
- [x] AC-07: `jsonschema>=4.0,<5.0` is a canonical runtime requirement in both
  `app.doql.less` and `pyproject.toml`, and the uv lock remains current.
- [x] AC-08: A wheel built from the corrective release installs into an
  isolated environment and `koru --version` returns the selected version.
- [x] AC-09: Hosted smoke and exact-head validation pass before Goal publishes
  0.1.460 from protected merged `main`.

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
- Corrective wheel SHA-256:
  `4313b1856bb05c8d36f9129b5fd126e883d1893f0ee99f8477394a91470df707`.
- Isolated corrective wheel: `koru --version` -> `koru 0.1.460`; package
  metadata/module -> 0.1.460; installed `jsonschema` -> 4.26.0.
- DoQL validation: 0 errors, 2 pre-existing compatibility warnings.
- Goal critical Python gate: 253 passed, 2 deprecation warnings.
- All five Node plugin workspaces: compile and tests PASS after the canonical
  `npm install` lock strategy; npm audit reports 0 vulnerabilities.
- Corrective PR: `semcod/koru#22`; approved exact head:
  `a8dacd1a4a87140344c898ef9014ab2fe077f67c`; validator run:
  `31394251198`; merge commit:
  `a43963a29599cbbd731d8dcc072ad6a643bf67ba`.
- Goal 2.1.292 publish-only gate: 253 Python tests passed and all five Node
  workspaces passed before upload from merged `main`.
- Public release: `koru==0.1.460`; wheel SHA-256:
  `923b2298acadbe37c2a92904168102afdceabe4d88b899acd9891ba01ac14a8d`;
  sdist SHA-256:
  `dc63cb18fda189fbb4c1f78f65105ee1e548a3195efe940d1bccab7c9bb0c78b`.

## Risk boundary

The follow-up makes one already-imported library explicit in runtime metadata;
it changes neither Koru APIs nor queue/autonomy behavior. The dependency is
bounded below the next major version, and the repository policy permits only
this one runtime dependency in the delivery slice. Generated analysis
snapshots remain out of scope.

## Session authorization

The user authorized this concrete dependency update and autonomous execution
on 2026-08-10. No fresh confirmation is required for the bounded paths in the
accepted intent.

The same user request explicitly includes testing and publication. Goal
2.1.292 revealed an existing complete 0.1.459 prebump and unreleased package
source after v0.1.456; publishing that already-selected version was part of
this integration completion. Because the immutable 0.1.459 public wheel then
failed its isolated CLI smoke, the same authorization covers the minimal
metadata correction and corrective 0.1.460 publication.

## Participants

- Human participant: unresolved; no user-* file was created by this script.
- Agent participant: [ai-codex.md](ai-codex.md)
