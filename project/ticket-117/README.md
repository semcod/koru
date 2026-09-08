# Ticket 117: Simplify todo2code discovery orchestration

- **ID**: ticket-117
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-08

SESSION_EXECUTION_AUTHORIZATION: User requested continued refactoring, GitHub publication, deployment and testing.

AC-01: Simplify todo2code discovery orchestration by extracting bounded
configuration and fresh-artifact handling while preserving command execution,
staleness rules, filtering and planfile outcomes.

## Acceptance criteria

- [ ] AC-01: Discovery behavior remains unchanged and orchestration complexity decreases.

Validation: 15 focused tests, Koru-driven regressions, Ruff, managed
governance, Docker Compose and compileall passed.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
