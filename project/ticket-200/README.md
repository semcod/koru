# Ticket 200: Reduce cyclomatic complexity in scan admission

- **ID**: ticket-200
- **Owner**: antigravity
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-25

## Goal and scope

Reduce cyclomatic complexity: `src.koru.fleet_admission.scan_admission` (CC=29) at
`src/koru/fleet_admission.py:27` (PLF-019).

Extract smaller helper functions for loading config, validating repository policy,
running gate CLI, and parsing decisions. Preserve exact admission behavior,
environment checking, timeout, and denial fallback semantics.

## Acceptance criteria

- [x] AC-01: Scope is approved by a human owner.
- [x] AC-02: `scan_admission` and all helpers have CC <= 8 (Rank A or low B).
- [x] AC-03: All existing fleet admission tests pass unchanged (`pytest -q tests/test_fleet_admission.py`).
- [x] AC-04: Governance check passes with 0 errors (`bash project/governance-check.sh`).

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
