# Ticket 140: Keep Goal remediation runtime state outside the implementation diff

- **ID**: ticket-140
- **Owner**: codex
- **Status**: IN_PROGRESS
- **Workflow state**: PUBLICATION
- **Created**: 2026-09-15

## Goal and scope

Keep Goal remediation's Planfile and analysis outputs local runtime state. The
proposal intake must exclude both newly-created and legacy tracked runtime
paths from the implementation diff without deleting their checkout contents.

## Acceptance criteria

- [x] AC-01: Proposal intake excludes `.planfile/`, `.koru/` and
      `.planfile_analysis/` in the local Git exclude registry.
- [x] AC-02: Legacy tracked runtime paths receive local `skip-worktree`
      protection after intake, so generated state does not appear as source
      implementation changes.
- [x] AC-03: Regression coverage proves the runtime files remain on disk and
      `git status` stays clean after the simulated Planfile write.
- [x] AC-04: The managed governance and applicable stack checks pass on the
      frozen implementation head.

## Validation evidence

- `tests/test_goal_remediation.py` — 5 passed.
- Ruff, compileall, managed governance, Docker Compose configuration and
  `git diff --check` — passed.

## Authorization

`SESSION_EXECUTION_AUTHORIZATION`: the user explicitly requested the fix,
remote publication and protected merge on 2026-09-15. Keep this ticket
`IN_PROGRESS / PUBLICATION` through exact-head review; the protected delivery
controller owns terminal closure after merge.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
