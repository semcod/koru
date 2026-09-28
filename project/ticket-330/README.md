# ticket-330: Consume canonical allocator workspaces

- **ID**: ticket-330
- **Owner**: codex
- **Status**: IN_PROGRESS
- **Workflow state**: PUBLICATION

SESSION_EXECUTION_AUTHORIZATION: user asked to continue the Koru execution investigation and authorized repair of #565 / PLF-100 and protected publication. This disjoint first slice consumes allocation safely; it does not own the queue changes in ticket-329.

## Acceptance criteria

- [x] AC-01: Real adopted allocator produces exactly one registered relative canonical worktree; Koru consumes its actual output and validates ticket, branch, paths and base without recreating it or overwriting allocation records.
- [x] AC-02: Allocation alone never permits implementation. Persist allocation identity and controller-admission blocker; automatic retries never allocate another ticket for the interrupted run.
- [ ] AC-03: Focused regression and managed checks pass; exact-head independent publication.

Remaining #565 scope: protected controller acquisition/revalidation across execution and publication, queue workspace/promotion integration, audited cleanup and resume. No current Koru protected controller adapter exists in this path; fail closed until that boundary is integrated.

Validation: 99 focused ticket-command tests passed with the real adopted allocator/checker and Git; managed governance PASS; Ruff PASS; Docker engine 29.1.3 available. This slice stops at controller admission and does not claim completed issue implementation.
