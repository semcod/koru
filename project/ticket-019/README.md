# Ticket 019: Restore green Ruff CI

- **ID**: ticket-019
- **GitHub issue**: #38
- **Owner**: agent:codex under SESSION_EXECUTION_AUTHORIZATION
- **Status**: DONE
- **Workflow state**: DONE
- **Created**: 2026-08-28

## Goal and scope

Remove the safe import-order violations that block both main CI matrix jobs.

## Acceptance criteria

- [x] AC-01: `ruff check src tests` passes.
- [x] AC-02: Protected checks passed for exact PR head
  `381e68086ab4926285fcd14491b5691eccf18f8b` before merge.

## Delivery evidence

- PR #39 was merged at 2026-08-28T14:50:50Z as
  `db65f25999112b87be3e967f06b267d7fa7fc1dc`.
- `smoke=SUCCESS` and `onedev/local-verify=SUCCESS` were observed on the exact
  implementation head.
- Later lint findings on `main` are outside the ticket-019 diff and are not
  retroactively attributed to this completed import-order repair.

## Participants

- Human participant: active-session authorization; no user-* file was created.
- Agent participant: [ai-codex.md](ai-codex.md)
