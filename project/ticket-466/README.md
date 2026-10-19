# Ticket 466: Opt-in strict_files: refuse promotion of patches outside declared ticket files (#726)

- **ID**: ticket-466
- **Owner**: agent:claude
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-10-19

## Goal and scope

Part 1 of semcod/koru#726. A run for subactor/platform ticket-455 promoted a
"verified patch" that created an undeclared, truncated `tests/` file because
the verify command passed vacuously.

`src/koru/queue/transaction/preflight.py`: when a ticket sets
`inputs.strict_files: true` and declares `files`, `screen_promotion_preconditions`
refuses promotion with `patch_targets_outside_declared_files` and names the
undeclared targets (`undeclared_targets(plan)`). Without the opt-in nothing
changes, so existing lanes that add files keep working.
`tests/test_strict_files.py` covers refusal, `./` normalisation and the
default.

Implemented by willman (`koru.develop_ticket`, zai/glm-5.3). Both attempts
were correct but Koru refused them: the repository's pytest `addopts` load
`wellmanifest_governance`, whose session gate fails inside Koru's nested
staging worktree (GOV-PACKAGING-003), so any pytest verify command fails there.
Patch taken from the staging worktree after review.

Not in scope (rest of #726): `verify_not_discriminating` when the baseline
already passes; parse checks for new files.

## Acceptance criteria

- [x] AC-01: `tests/test_strict_files.py` → 3 passed.
- [x] AC-02: `tests/test_queue_transaction_phases.py` still passes (47 passed together).

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
