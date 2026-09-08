# Ticket 116: Separate todo2code discovery orchestration

- **ID**: ticket-116
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-08

SESSION_EXECUTION_AUTHORIZATION: User requested continued refactoring, GitHub publication, deployment and testing.

AC-01: Extract repeated plan-set consumption from todo2code discovery while
preserving stale-artifact reuse, usefulness filtering, limits and planfile
application.

## Acceptance criteria

- [ ] AC-01: Plan processing is shared without changing outcomes.

Validation: 15 focused tests, Koru-driven regressions, Ruff, managed
governance, Docker Compose and compileall passed.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
