# Ticket 278: Address code smell: Shotgun Surgery: errors locals in koru bootstrap validation

- **ID**: ticket-278
- **Owner**: claude
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-27

## Goal and scope

Clear the code2llm `Shotgun Surgery: errors` smell (planfile ticket PLF-053,
reported for `src/koru/bootstrap.py:436`) in `src/koru/bootstrap.py`.

Seven functions in the file mutate a list local named `errors`
(`_validate_id`, `_validate_executor`, `_validate_blocked_by`,
`_validate_task`, `_validate_cross_task_dependencies`,
`validate_flat_pipeline`, `import_flat_pipeline`; reproduced with the
installed code2llm `DFGExtractor` mutation grouping on the file AST: 17
mutation records). The detector groups mutations by (file, variable) and
fires at >= 5 scopes — the shared *name* is the smell; each function
actually contributes its own validation stage's findings to the same
accumulated report (id findings, executor kind/mode findings, blocked_by
entry findings, the per-task aggregation, cross-task dependency/cycle
findings, the whole-pipeline aggregation, and the validation gate in the
public `import_flat_pipeline` entry point).

Fix: stage-accurate names for each stage's error channel — `id_errors`
(`_validate_id`, missing/duplicate id findings), `executor_errors`
(`_validate_executor`, executor.kind/executor.mode findings),
`blocked_by_errors` (`_validate_blocked_by`, non-string blocked_by entry
findings), `task_violations` (`_validate_task`, the per-task accumulator
across all field validators), `dependency_errors`
(`_validate_cross_task_dependencies`, unknown blocked_by references and the
dependency cycle), `pipeline_errors` (`validate_flat_pipeline`, the
whole-pipeline aggregation) and `validation_errors` (`import_flat_pipeline`,
the validation gate before materialisation). The `errors` mutation group
drops from 7 scopes to 0. Pure rename of function-internal locals; no
signature, return shape or behavior change; no other file is touched.

Tests: `tests/test_bootstrap.py` (direct coverage of
`validate_flat_pipeline`/`import_flat_pipeline` and the field validators)
runs unchanged as the behavioral proof of the pure rename.

## Acceptance criteria

- [x] AC-01: code2llm smell re-scan no longer reports `shotgun_surgery` for
  the variable `errors` in `src/koru/bootstrap.py`, and introduces no new
  (file, variable) mutation group at or beyond the threshold. Verified with
  the installed code2llm `DFGExtractor` mutation grouping on the file AST
  (standalone extract; `ProjectAnalyzer.analyze` on copies/worktrees
  silently yields empty scopes): baseline content reports `Mutation of
  variable 'errors' spans 7 functions` from exactly the seven scopes listed
  above (17 mutation records); renamed content reports an `errors` group of
  0 scopes; file mutation record count unchanged (115, pure rename); every
  renamed local lands at 1 scope — far below the >= 5 threshold.
- [x] AC-02: `python3 -m pytest tests/test_bootstrap.py -q` passes unchanged
  in the ticket worktree; `ruff check src/koru/bootstrap.py` reports zero
  errors.
- [x] AC-03: `bash project/governance-check.sh --base <merge-base>` passes
  with 0 errors from the ticket worktree (GOV-PASS, 0 errors, 0 warnings).

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
