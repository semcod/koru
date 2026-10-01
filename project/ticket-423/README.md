# Ticket 423: Fix ticket log identity routing

- **ID**: ticket-423
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: PUBLICATION
- **Created**: 2026-10-01

## Goal and scope

Fix ticket log identity routing in Koru. SESSION_EXECUTION_AUTHORIZATION: user requested implementation and merge on 2026-10-01. Preserve unrelated primary checkout changes.

## Acceptance criteria

- [x] AC-01: Planfile identifiers never resolve by numeric suffix to unrelated Wellmanifest tickets.
- [x] AC-02: Unbound or unmapped activity never falls back to the most recently modified ticket.
- [x] AC-03: Explicit ticket routing works and ambiguous targets are rejected; regression and governance checks pass.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.

## Validation

33 focused tests passed; Ruff and governance passed; Docker engine and Compose configuration verified. Publication and merge requested by user; pending independent exact-head validation.
