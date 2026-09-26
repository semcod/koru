# Antigravity plan

## Problem

Koru's autonomous loop post-run verification (`queue.post_run_verify` in `koru.yaml`) fails on two commands:
1. `.venv/bin/python -m ruff check src tests` fails with 27 errors (unused imports, long lines in tests).
2. `.venv/bin/python -m pytest tests/ -q -x` fails on `test_ensure_autonomy_strategy_creates_koru_yaml` in `tests/test_autonomy_strategy.py` because it asserts `accordion_detail_to_general` instead of the new default strategy `in_flight_first`.

Because `post_run_verify` has `on_failure: reopen`, every ticket completed by the autonomous daemon is immediately reopened with `waiting_input`, deadlocking the autonomous cycle.

## Approach

1. Update `tests/test_autonomy_strategy.py` to expect `in_flight_first`.
2. Fix the 27 ruff lint errors in the scoped test and integration files.
3. Verify that `ruff check src tests` passes cleanly with 0 errors.
4. Verify that `pytest tests/test_autonomy_strategy.py` passes cleanly.
5. Verify governance gate passes with 0 errors.
