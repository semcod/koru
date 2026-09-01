# Ticket 030: Koru CI verify uses ci run and default gates fallback

- **ID**: ticket-030
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-01

## Goal and scope

Ensure Koru autonomous verify steps run policy tests before quality gates,
and that projects without `.koru/topology.yaml` do not inherit every gate.

## Acceptance criteria

- [x] AC-01: Task profile verify uses `koru ci run`; baseline uses `--skip-gates`.
- [x] AC-02: `resolve_gates` defaults to `regix` + `redup` when topology is absent.
- [x] AC-03: Doctor reports `pyqual.yaml` and `scripts/ci-test.sh` when present.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
