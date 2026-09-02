# Ticket 053: Publish generated artifacts in CI

- **ID**: ticket-053
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: PUBLICATION
- **Created**: 2026-09-02

## Goal and scope

Replace the obsolete weekly SUMR pull-request automation with a read-only CI
workflow that regenerates and uploads analysis and coverage artifacts, and
recovers the hash-verified accepted media baseline as an artifact. Generated
outputs must never be committed or pushed.

The user's 2026-09-02 instruction to execute the plan under `docs/*` is
`SESSION_EXECUTION_AUTHORIZATION` for this bounded VOL-1 infrastructure slice.

## Acceptance criteria

- [x] AC-01: CI uploads analysis, coverage and media as separate retained artifacts.
- [x] AC-02: The workflow has read-only repository permissions and no commit/PR path.
- [x] AC-03: Generator versions and media integrity bind to the checked-in registry.
- [x] AC-04: Governance, workflow syntax, Docker Compose and diff gates pass.

## Tracking boundary

This directory contains the minimal reviewed intent; ticket prose is not the
material outcome.
