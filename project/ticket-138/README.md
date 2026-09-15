# Ticket 138: Align Koru metadata contracts with declared dependencies

- **ID**: ticket-138
- **Owner**: codex
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-15
- **GitHub issue**: https://github.com/semcod/koru/issues/184

## Goal and scope

The metadata regression tests described an older Koru dependency contract and
compared environment-marked requirements as raw strings. This ticket updates
the tests to match the declared runtime dependencies and to compare aggregate
extras by package, extras and bounds while retaining strict drift detection.

## Acceptance criteria

- [x] AC-01: Runtime dependency assertions include the declared jsonschema and
  korullm bounds.
- [x] AC-02: The `all` extra assertion handles a redundant Python marker without
  accepting missing packages or changed bounds.
- [x] AC-03: Managed metadata tests, Ruff and governance pass.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
