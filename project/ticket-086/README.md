# Ticket 086: Isolate command picker unit tests from live SubLLM

- **ID**: ticket-086
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: PUBLICATION
- **Created**: 2026-09-05

## Goal and scope

Restore deterministic unit-test isolation after the SubLLM routing migration.

## Acceptance criteria

- [x] AC-01: Default unit-test picker calls use a controlled unavailable response; explicit mocked model tests still pass.
- [ ] AC-02: Required tests and governance pass; Goal and protected Validator publish the material fix.
