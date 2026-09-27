# Ticket 316: Preserve project history when replaying scan force

- **ID**: ticket-316
- **Owner**: agent:codex
- **Status**: IN_PROGRESS
- **Workflow state**: PUBLICATION
- **Created**: 2026-09-27

## Goal and scope

First slice of PLF-063 / semcod/koru#524: scan force currently deletes project/
and runs the autonomous loop. Replace it with one scanner invocation and keep
legacy DSL compatible. Idle narration is a dependent slice, preserved in a
bounded recovery patch and still tracked by PLF-063; it is not part of this PR.

SESSION_EXECUTION_AUTHORIZATION: user requested continued Koru repairs and
pilots on 2026-09-27. Ticket-313 stays blocked on missing independent approval;
this ticket does not close it or activate its held runtime. Allocation used
the reviewed HOME allocator 5f21f21 and preserved foreign primary changes.
The initial 12-file change exceeded class M's 9-file budget, so it was split;
this S slice changes four implementation files and does not widen the budget.

## Acceptance criteria

- [x] AC-01: Scan replay preserves project and Planfile history and propagates failure.
- [x] AC-02: Legacy DSL/labels remain usable with truthful scan metadata.
- [ ] AC-03: Relevant regressions and governance pass; independent Validator owns publication.

Validation: 73 focused tests passed; after pinning replay to the current Python
interpreter, all 11 replay tests passed again. Governance and Ruff passed.
Independent exact-head publication remains pending.
