# Ticket 447: Support force staging and add returncode check for verified patch paths in commit_worktree

- **ID**: ticket-447
- **Owner**: gemini
- **Status**: IN_PROGRESS
- **Workflow state**: PUBLICATION
- **Created**: 2026-10-11

SESSION_EXECUTION_AUTHORIZATION: user requests continuation, test and merge. Koru verified patch staging must handle paths matched by broad repository gitignore and check staging exit codes before committing.

## Goal and scope

In `src/koru/queue/workspace.py`, when committing verified patch paths on a run branch or main, use force staging (`git add -f -- <paths>`) for explicitly passed patch paths and check command returncode so that files ignored by broad target `.gitignore` rules (e.g. `.planfile/`) can be committed properly to the run branch, and failures in `git add` are cleanly reported rather than failing ambiguously during `git commit`.

## Acceptance criteria

- [x] AC-01: `commit_worktree` uses `git add -f -- <paths>` when explicit paths are supplied and checks returncode before invoking `git commit`.
- [x] AC-02: `commit_on_main` uses `git add -f -- <paths>` when explicit paths are supplied.
- [x] AC-03: Regression tests verify that verified patch paths ignored by `.gitignore` are staged and committed successfully to the run branch.
