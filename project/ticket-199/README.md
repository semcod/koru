# Ticket 199: Decompose god function apply_patch_with_retry

- **ID**: ticket-199
- **Owner**: antigravity
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-25

## Goal and scope

Address code smell: God Function: `apply_patch_with_retry` in `src/koru/queue/patch_retry.py:96`
(PLF-013 / issue #399).

Extract focused helper functions for retry execution, run finishing, verification
record building, and promotion record assembly. Preserve exact patch transaction,
drift detection, envelope wrapping, and evidence recording semantics.

## Acceptance criteria

- [x] AC-01: Scope is approved by a human owner.
- [x] AC-02: `apply_patch_with_retry` and `_finish_run` decomposed with all helpers <= 11.
- [x] AC-03: Existing unit and regression tests pass without changes.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
