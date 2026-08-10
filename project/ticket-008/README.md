# Ticket 008: Require Goal 2.1.293 across Koru development metadata

- **ID**: ticket-008
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: VALIDATION
- **Created**: 2026-08-10
- **Work classification**: `SERVICE / integration`

## Goal and scope

Raise Koru's Goal development-tool floor from 2.1.292 to the published
2.1.293 release in every existing canonical dependency slot and refresh the
uv lockfile. Keep Koru's application version unchanged unless Goal's
registry-aware version state proves that a new release is required.

## Acceptance criteria

- [x] AC-01: The user explicitly requested autonomous dependency updates,
  testing, publication and continuation without repeated confirmation.
- [x] AC-02: All Goal dependency slots in `pyproject.toml` and `app.doql.less`
  require at least 2.1.293.
- [x] AC-03: `uv.lock` resolves the public Goal 2.1.293 artifact and remains
  frozen/current.
- [x] AC-04: Dependency-focused tests and repository governance pass.
- [ ] AC-05: Goal makes a registry-aware Koru version decision and creates a
  pull request whose exact head passes hosted and validator gates before
  merge.

## Risk boundary

This ticket changes development-tool metadata and its lockfile only. It does
not change runtime dependencies, runtime source, public interfaces, Docker,
CI or generated analysis snapshots. Governance evidence and the canonical
ticket index are updated only for this ticket.

## Local validation evidence

- `uv lock --check` and `uv tree --locked --package goal`: PASS; Goal resolves
  to public version 2.1.293.
- Dependency synchronization tests: 12 passed, including 735 inventory
  subtests.
- Koru critical suite: 253 passed with two pre-existing deprecation warnings.
- `doql -f app.doql.less validate`: 0 errors and two pre-existing
  compatibility warnings.
- Production Docker image builds successfully; an offline (`--network none`)
  container reports `koru 0.1.460` and installed `goal 2.1.293`.
- Repository governance and `git diff --check`: PASS.
- Goal registry comparison preserves Koru 0.1.460 with a `no-release`
  decision; no artificial application-version bump is required.

## Session authorization

The user authorized autonomous execution and publication in this session on
2026-08-10. This bounded dependency-only intent therefore proceeds directly
to `EDIT`; no human-owned `user-*.md` file is synthesized.

## Participants

- Human participant: unresolved; no user-* file was created by this script.
- Agent participant: [ai-codex.md](ai-codex.md)
