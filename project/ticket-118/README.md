# Ticket 118: Separate todo2code scan suggestion mapping

- **ID**: ticket-118
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-08

SESSION_EXECUTION_AUTHORIZATION: User requested continued refactoring, GitHub publication, deployment and testing.

AC-01: Extract conversion of one useful todo2code plan into a suggestion while
preserving usefulness checks, path bounds, truncation, priority normalization,
dedupe evidence and labels.

## Acceptance criteria

- [ ] AC-01: Scan output remains identical and the orchestration is simpler.

Validation: 15 focused tests, Koru-driven regressions, Ruff, managed
governance, Docker Compose and compileall passed.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
