# Ticket 022: Stabilize Koru work/decide smoke

- **ID**: ticket-022
- **Owner**: agent:codex
- **Status**: PLAN
- **Workflow state**: WAIT_FOR_APPROVAL
- **Created**: 2026-09-01

## Goal and scope

Stabilize the already-present `koru work` and execution-plan integration after
the delivered `work/decide` implementation introduced two Ruff failures in
the source smoke gate. The repair is limited to removing one unused import and
restoring deterministic import order; it must not change CLI behavior or the
validator-agent authority boundary.

The broader implementation is already on `main`, but presence is not approval
or completion evidence for this bounded repair.

## Acceptance criteria

- [ ] AC-01: The amended exact-base, two-source-file scope is explicitly
  approved before implementation or test files change.
- [ ] AC-02: Ruff passes for both touched modules and for the complete
  `src/koru` smoke scope without suppressions.
- [ ] AC-03: Existing execution-plan and work-lifecycle regression tests remain
  green with no CLI behavior or public-interface change.
- [ ] AC-04: Governance, diff hygiene and Docker configuration checks pass on
  the delivery head.

## Planning note

The accepted planning base is `37cd8021034680b6bee7d7ef27c628fef12dddab`.
Resume only after explicit approval by transitioning to `IN_PROGRESS / EDIT`
in this dedicated branch/worktree. The unrelated Ruff failure in
`tests/test_autonomous.py` and the seven previously measured deterministic
test failures require separate scopes.

## Participants

- Human participant: unresolved; no user-* file was created.
- Agent participant: [ai-codex.md](ai-codex.md)
- Agent participant: [ai-cursor.md](ai-cursor.md)
