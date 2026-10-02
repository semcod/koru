# Ticket 424: Resolve declared Planfile CI verification gate

- **ID**: ticket-424
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: PUBLICATION
- **Created**: 2026-10-02

## Goal and scope

Read the project-declared Planfile CI verification command as a final legacy fallback. SESSION_EXECUTION_AUTHORIZATION: user requested continuation, testing and merge on 2026-10-02. Preserve unrelated primary changes.

## Acceptance criteria

- [x] AC-01: A valid declared Planfile ci.command resolves when no earlier verification command exists.
- [x] AC-02: Existing precedence, named profiles and mandatory profile allowlists remain enforced.
- [x] AC-03: Invalid or empty Planfile commands never become runnable gates; regression and governance checks pass.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.

## Validation

69 focused tests and 10 subtests passed; Ruff and managed governance passed; Docker Compose configuration passed. Broader queue checks passed 185 tests and 22 subtests but three existing SubLLM transport tests disagree with this host configuration; protected OneDev checks and independent exact-head Validator must decide publication.
