# Ticket 257: decompose dispatch_validator_merge in publication to reduce cyclomatic complexity

- **ID**: ticket-257
- **Owner**: antigravity
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-26

## Goal and scope

Reduce cyclomatic complexity in `src/koru/ci/publication.py`:
1. `dispatch_validator_merge` (CC=22 -> <=5): Decompose into PR number resolver (`_resolve_pr_number`), mergeability validator (`_verify_pr_mergeable`), and validator command builder (`_build_validator_cmd`).
2. Ensure 100% backward compatibility of all function arguments, options, return dictionary format, and errors raised.
3. Verify that all 12 tests in `tests/test_ci_pipeline.py` pass without modification.

## Acceptance criteria

- [x] AC-01: Decompose `dispatch_validator_merge` in `src/koru/ci/publication.py` so CC <= 5.
- [x] AC-02: All existing tests in `tests/test_ci_pipeline.py` pass without modification.
- [x] AC-03: `ruff check` and `ruff format` report 0 findings.
- [x] AC-04: `./project/governance-check.sh` passes with 0 errors and 0 warnings.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
