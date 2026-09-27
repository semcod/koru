# Ticket 321: Tiered model selection with glm5.3-flash default for small tasks

- **ID**: ticket-321
- **Owner**: human:tom
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-27
- **Authorization**: SESSION_EXECUTION_AUTHORIZATION

## Goal and scope

1. Establish `glm5.3-flash` (or configured simple tier) as the standard default for bounded single-file tasks, linting and small refactors when `KORU_TILLM_SIMPLE_MODEL` is not explicitly set, avoiding expensive frontier calls for trivial tasks.
2. Refine small task heuristics in `src/koru/task_model_policy.py`: allow single-file tasks with `XS`/`S` complexity or smell-specific targeted refactors to route to the fast flash tier.
3. Add model tier preference support to `koru config` (e.g. `model na sonnet`, `prosty model na glm5.3-flash`, `simple model to flash`).
4. Display active models (`model`, `simple_model`) in `render_config_table`.

## Acceptance criteria

- [ ] AC-01: Bounded tasks route to `glm5.3-flash` by default when no explicit operator pin is present.
- [ ] AC-02: `koru config` displays and allows modifying default and simple LLM models via NL.
- [ ] AC-03: Full test suite passes in `tests/test_task_model_policy.py` and `tests/test_configurator*.py`.
- [ ] AC-04: `./project/governance-check.sh` reports `GOV-PASS: passed (0 errors, 0 warnings)`.
