# Ticket 283: Enable claude-code client in simple model routing for bounded ruff tasks

- **ID**: ticket-283
- **Owner**: antigravity
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-27

## Goal and scope

Allow the `claude-code` autopilot client to use the configured simple model (`zai/glm-5.3-flash`) for bounded single-file ruff lint fix tasks.

1. Extend `_is_lint_fix_request` in `src/koru/task_model_policy.py` to allow `claude-code` alongside `opencode`.
2. Update unit tests in `tests/test_task_model_policy.py` to verify that `claude-code` selects `zai/glm-5.3-flash` when given a bounded lint task, while unsupported clients remain on the default model.

## Acceptance criteria

- [ ] AC-01: `python3 -m pytest -q -p no:wellmanifest_governance tests/test_task_model_policy.py` passes cleanly.
- [ ] AC-02: `ruff check src/koru/task_model_policy.py tests/test_task_model_policy.py` reports zero errors.
- [ ] AC-03: `./project/governance-check.sh` reports 0 errors and 0 warnings.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
