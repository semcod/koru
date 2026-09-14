# Ticket 128: Add proactive fleet standard-update ticket emission

- **ID**: ticket-128
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: PUBLICATION
- **Created**: 2026-09-14

## Goal and scope

SESSION_EXECUTION_AUTHORIZATION: the user requested continuation of the
Wellmanifest freshness work and asked whether Koru can execute it faster.

Add a koru fleet standard-update scanner. It reads one clean, already-fetched
wellmanifest/new-project checkout as the standard source, compares every
adopted repository lock by version and immutable revision, and optionally
emits one deduplicated Planfile adoption notice per stale target.
The scanner must never edit, stage, commit, push, merge or delete an adopter.
Each emitted notice remains waiting_input; the target repository's own
governance adoption ticket and protected delivery process remain authoritative.

Read-only Git observations run in bounded parallel workers so the fleet can be
audited quickly. Planfile ticket creation stays sequential because it has a
single writer.

## Acceptance criteria

- [x] AC-01: Scope is approved by the user's explicit execution request.
- [x] AC-02: A clean standard source is required and its version/revision are
      compared against all discovered governance locks without network access
      or adopter mutation.
- [x] AC-03: The scanner supports bounded parallel observations and reports
      dirty targets and linked worktrees as evidence, without treating them as
      permission to overwrite anything.
- [x] AC-04: Explicit ticket emission is idempotent by repository and target
      revision, uses waiting_input, and grants no write or merge authority.
- [x] AC-05: CLI, focused tests, Ruff and governance checks pass.

## Validation evidence

- `22 passed` in `tests/test_standard_fleet.py tests/test_cli_fleet.py`.
- `4075 passed, 15 skipped, 164 deselected, 962 subtests passed` in the
  non-slow suite; the three failures are the same baseline failures on clean
  `main` (`test_ide_doctor...` and the two `test_pyproject_metadata...`).
- `./project/governance-check.sh --base origin/main --head HEAD --actor agent`:
  `GOV-PASS: passed (0 errors, 0 warnings)`.
- Ruff, Python compilation and `git diff --check` pass.
- Read-only real-fleet run: 33 governed repositories, 2 current and 31
  stale against clean `wellmanifest/new-project` `0.20.29 @
  a4178b9cf6fa12540ee7406d7f38391dd4fa1f30`.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
