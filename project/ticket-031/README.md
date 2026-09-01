# Ticket 031: Repair post-merge CI verification gaps

- **ID**: ticket-031
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: PUBLICATION
- **Created**: 2026-09-01

## Goal and scope

Deliver the post-merge verification fixes that were discovered only after
ticket-030 had already frozen and merged. Keep the terminal ticket immutable:
align doctor facade regression tests with its new probes and make
`koru ci run --skip-gates` truly skip quality gates when no policy command is
configured.

## Acceptance criteria

- [x] AC-01: The active user requested autonomous continuation and closure of
  all remaining session tasks; session execution authorization applies.
- [x] AC-02: `koru ci run --skip-gates` returns a successful no-op when the
  project has no `ci.command`, without invoking quality gates.
- [x] AC-03: Doctor facade tests cover the new probe order plus absent,
  unavailable and ready quality-pipeline states.
- [x] AC-04: Focused pytest, changed-file Ruff, governance and Docker Compose
  checks pass before protected publication.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
