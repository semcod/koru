# Ticket 475: Honor hooks during queue promotion

- **ID**: ticket-475
- **Owner**: agent:codex
- **Status**: IN_PROGRESS
- **Workflow state**: PUBLICATION

SESSION_EXECUTION_AUTHORIZATION: the user requested continued repair of Willman and dependencies on 2026-10-20, following the observed Koru promotion anomaly. The managed allocator created this disjoint canonical worktree. Foreign worktrees and source remain preserved.

Queue promotion currently inserts `--no-verify` when a caller supplies the governed-worktree environment flag and a matching branch name. A rejecting hook can therefore be skipped while Koru reports a successful commit. Use ordinary `git commit` for every promotion, preserving hook failure and the proposed files.

- [x] AC-01: A real rejecting pre-commit hook runs for governed and ordinary promotion branches, the call fails, HEAD stays unchanged, and proposed bytes survive.
- [x] AC-02: A real accepting hook runs, only declared paths are committed, and other changes remain intact.
- [x] AC-03: Focused queue tests and managed governance pass with the normal plugin enabled.

Issue: https://github.com/semcod/koru/issues/737. This bounded slice fixes commit-hook bypass; authoritative writer admission is still outstanding in that issue. No result here grants review or merge authority.

Validation: the 10-case real-Git regression reproduced four failures on the original implementation. After the repair, the focused promotion, retention, recovery and transaction suite passes: 81 tests and 3 subtests, with the normal governance plugin enabled. Ruff and whitespace checks pass. Independent exact-head review, merge and deployment remain pending.
