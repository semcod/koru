# Ticket 292: Support structured small task complexity in model policy routing

- **ID**: ticket-292
- **Owner**: antigravity
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-27

## Goal and scope

Enable the model routing policy in `src/koru/task_model_policy.py` to route structured small tasks (e.g. `complexity: "XS"`, `complexity: "S"`, or simple task kinds) with bounded scope (single target file, no complex labels) to the configured simple model (`KORU_TILLM_SIMPLE_MODEL`, e.g. `zai/glm-5.3-flash`).

1. Extend `src/koru/queue/ticket.py` (`ticket_llm_request`) to forward `complexity` and `task_size` in `request["task"]` and `request["task"]["inputs"]`.
2. Extend `src/koru/task_model_policy.py` to recognize bounded small tasks via `_is_small_task_candidate` and `_is_bounded_small_scope`, returning reason `bounded_small_task`.
3. Ensure complex tasks (`refactor`, `code2llm`, `security`, `governance`, `dependencies`, multi-file) strictly remain on the default model.
4. Maintain cyclomatic complexity CC <= 6 for all functions in `task_model_policy.py`.
5. Add comprehensive unit tests in `tests/test_task_model_policy.py`.

## Acceptance criteria

- [x] AC-01: `python3 -m pytest -q -p no:wellmanifest_governance tests/test_task_model_policy.py` passes cleanly (38 passed).
- [x] AC-02: `ruff check src/koru/task_model_policy.py src/koru/queue/ticket.py tests/test_task_model_policy.py` reports zero errors.
- [x] AC-03: `radon cc src/koru/task_model_policy.py -s` verifies CC <= 6 for all helper functions.
- [x] AC-04: `./project/governance-check.sh` reports 0 errors and 0 warnings.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
