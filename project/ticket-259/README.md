# Ticket 259: Decompose propose_and_apply in execution to reduce cyclomatic complexity

- **ID**: ticket-259
- **Owner**: antigravity
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-26

## Goal and scope

Refactor `propose_and_apply` in `src/koru/ticket_command/execution.py` to reduce its Cyclomatic Complexity from 20 down to <=6.

1. Extract `_load_context_files` to load and validate scope for context files.
2. Extract `_build_proposal_prompt` to construct the unified instruction and JSON payload.
3. Extract `_extract_and_validate_diff` to validate the returned unified diff bounds and forbidden tokens.
4. Extract `_apply_diff_to_workspace` to run git apply checks and apply the diff.
5. Retain 100% backward compatibility on `propose_and_apply`.

## Acceptance criteria

- [ ] AC-01: All tests in `tests/test_ticket_command.py` pass cleanly.
- [ ] AC-02: Cyclomatic complexity of `propose_and_apply` drops from 20 to <=6.
- [ ] AC-03: Ruff reports zero lint/formatting errors.
- [ ] AC-04: `./project/governance-check.sh` reports 0 errors and 0 warnings.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
