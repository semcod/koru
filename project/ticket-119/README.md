# Ticket 119: Separate Goal workspace repository selection

- **ID**: ticket-119
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-08

SESSION_EXECUTION_AUTHORIZATION: User requested continued refactoring, GitHub publication, deployment and testing.

AC-01: Extract bounded repository enumeration and dirty-repository selection
from Goal workspace resolution while preserving fail-closed ambiguity and
unreadable-status errors.

## Acceptance criteria

- [ ] AC-01: Goal target resolution remains behaviorally identical.

Validation: 10 focused tests, Koru-driven regressions, Ruff, managed
governance, Docker Compose and compileall passed.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
