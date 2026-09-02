# Ticket 054: Validate generated-state cleanup

- **ID**: ticket-054
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: PUBLICATION
- **Created**: 2026-09-02

## Goal and scope

Make the volume-plan contract understand completed `untrack_generated` stages.
Instead of requiring generated source paths to exist, it must verify that every
path declared by the artifact registry is absent from the Git index.

The user's 2026-09-02 instruction to execute the plan under `docs/*` is
`SESSION_EXECUTION_AUTHORIZATION` for this bounded VOL-1 validation slice.

## Acceptance criteria

- [x] AC-01: Completed generated-state stages do not require deleted outputs to exist.
- [x] AC-02: Exact and wildcard registry paths are checked against the Git index.
- [x] AC-03: The test fails when a registry output is tracked and passes on current cleanup.
- [x] AC-04: Governance, focused tests, Docker Compose and diff gates pass.

## Tracking boundary

This directory contains the minimal reviewed intent; ticket prose is not the
material outcome.
