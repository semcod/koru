# Ticket 089: Make autonomy cycle regression tests deterministic

- **ID**: ticket-089
- **Owner**: tom
- **Status**: IN_PROGRESS
- **Workflow state**: PUBLICATION

## Goal and scope

Implement A0 of the verified autonomy roadmap: remove installed Planfile prefix and live planning-provider dependencies from the regression suite.

## Acceptance criteria

- [x] AC-01: Lease expiry asserts exactly one block for both single-token and Python-module Planfile commands.
- [x] AC-02: All 11 cycle tests run with an explicit planning stub and reject unexpected provider calls.
- [ ] AC-03: Focused regression, Ruff, governance and Docker Compose checks pass; protected PR delivery completes.
