# Ticket 115: Separate todo2code ticket promotion policy

- **ID**: ticket-115
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: PUBLICATION
- **Created**: 2026-09-08

SESSION_EXECUTION_AUTHORIZATION: User requested continued refactoring, GitHub publication, deployment and testing.

AC-01: Reduce todo2code promotion orchestration complexity by extracting the
single-ticket policy while preserving explicit executor and contract gates,
path filtering, input defaults and atomic sprint-file updates.

## Acceptance criteria

- [ ] AC-01: Extract single-ticket promotion policy and preserve existing tests.

Validation: 5 focused tests, Koru-driven regression tests, Ruff, managed
governance, Docker Compose and compileall passed. A second extraction splits
eligibility from executor configuration so the analyzed promotion helpers stay
below the complexity threshold.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
