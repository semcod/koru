# Ticket 006: Align Goal with Koru's literal version carriers

- **ID**: ticket-006
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-08-10
- **Work classification**: `SERVICE / governance`

## Goal and scope

Remove only `src/koru/__init__.py:__version__` from Goal's configured version
files. That module resolves installed package metadata dynamically and has no
writable literal declaration; Goal 2.1.292 correctly refuses to treat it as a
release carrier. Preserve every custom comment and all other Goal settings,
assign the currently unowned release carriers to the integration workstream,
and own Goal's governance-scoped README metadata for the paired publication.

## Acceptance criteria

- [x] AC-01: The user authorized autonomous Goal refactoring, testing and
  publication without a repeated confirmation for each bounded change.
- [ ] AC-02: `goal.yaml` lists only the literal VERSION, Python metadata and
  package.json carriers and otherwise remains byte-for-byte unchanged.
- [ ] AC-03: Goal recognizes the existing synchronized 0.1.459 prebump without
  an unreadable-carrier error or a second bump.
- [ ] AC-04: Repository governance, hosted smoke and exact-head validation pass.
- [ ] AC-05: Goal-generated README, changelog and package-lock metadata remains
  synchronized with the existing 0.1.459 carriers.
- [ ] AC-06: Immutable governance metadata assigns VERSION, CHANGELOG and the
  npm lockfile to integration and records the exact customized manifest hash.

## Risk boundary

This governance slice changes one configured list item, release-carrier
ownership and governance-scoped README metadata. It does not change runtime
code, package behavior, the selected version, registry settings, custom
release comments or publishing policy. Release/dependency manifests are owned
by paired integration ticket-004.

## Session authorization

The user explicitly requested autonomous Goal-based refactoring, testing and
publication on 2026-08-10. No fresh confirmation is required for this exact
one-line configuration repair.

## Participants

- Human participant: unresolved; no user-* file was created.
- Agent participant: [ai-codex.md](ai-codex.md)
