# Ticket 336: Restore failed patches without false rollback receipts

- **ID**: ticket-336
- **Owner**: agent:codex
- **Status**: IN_PROGRESS
- **Workflow state**: PUBLICATION
- **Created**: 2026-09-28

## Goal and scope

SESSION_EXECUTION_AUTHORIZATION: continue testing and repairing Koru regressions in files and contents. User continuation 2026-09-28. Protected publication remains part of the accepted delivery. Real Git probe confirmed rollback falsely reports success while both modified a.txt and added new.txt remain after failed verification.

## Acceptance criteria

- [x] AC-01: Failed direct verification reverses additions, deletions and changes; preserves unrelated files and the index; conflicting edits and Git failures return a non-retryable failure without claiming rollback or untouched workspace. Verifier exceptions also trigger restoration.
- [ ] AC-02: Focused queue/transaction tests, Ruff and governance pass; publish only through protected independent review.

## Scope limit

This slice covers failed verification. Commit-failure rollback, arbitrary verifier side effects outside patch targets and governed workspace admission remain separate work. Production lane remains stopped.

## Validation

- 72 transaction/journal/recovery/public API tests passed, including 3 failure-injection subtests.
- 107 queue tests passed, 3 deselected, 12 subtests passed. Those three LLM transport tests fail identically on unmodified main d2e60bb4 (live central transport is not isolated); recorded in PLF-100 for a separate scope.
- Ruff across src/koru/queue and the changed test passes; managed governance passes.
- External evidence: ~/.local/state/subactor/koru-ticket336/.
- Independent protected review and merge remain pending. Production lane remains stopped; this source change is not a deployment.
