# Ticket 318: Report idle eligibility truthfully and remove destructive scan guidance

- **ID**: ticket-318
- **Owner**: agent:codex
- **Status**: IN_PROGRESS
- **Workflow state**: PUBLICATION
- **Created**: 2026-09-27

## Goal and scope

Remaining guidance slice of PLF-063 / semcod/koru#524, after ticket-316 / PR544.
The observed c2004 runtime reports no open work while its snapshot shows five
operator-held open tickets, and suggests deleting project history to scan.
Report eligibility in the configured queue, retain the real status snapshot,
and offer the merged safe scan action. No admission, scheduling or hold changes.

SESSION_EXECUTION_AUTHORIZATION: user requested continued Koru repairs, tests
and autonomous pilots on 2026-09-27. Dedicated ticket/worktree/lease allocated
from current main after disjoint-scope/WIP admission. Dependency code is merged
at ea7475ef with App approval for source 33af99b7; post-merge receipt reconciliation
is separately pending and grants no runtime deployment authority.

## Acceptance criteria

- [x] AC-01: Idle diagnostics remain truthful with open operator-held/dependency-held work.
- [x] AC-02: Scan guidance respects configuration and never recommends deleting project history or reopening terminal tickets.
- [ ] AC-03: Relevant tests and governance pass; publication uses the independent Validator.

Validation: 51 focused runner/scan/replay tests pass on the final changes.
The broader run also passed decision-trace and autonomous tests; its one
incorrect enabled-scan fixture assertion was corrected and the affected suite
rerun. Governance, Ruff and whitespace checks passed. Exact-head independent
publication remains pending.
