# Ticket 120: Separate todo2code ticket hydration policy

- **ID**: ticket-120
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-08

SESSION_EXECUTION_AUTHORIZATION: User requested continued refactoring, GitHub publication, deployment and testing.

AC-01: Extract bounded todo2code verification command construction from ticket
hydration while preserving contract gating, diagnostic validation, source path
binding, labels and input defaults.

## Acceptance criteria

- [ ] AC-01: Hydration behavior remains unchanged and complexity decreases.

Validation: 7 focused tests, Koru-driven regressions, Ruff, managed
governance, Docker Compose and compileall passed.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
