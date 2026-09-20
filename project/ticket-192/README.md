# Ticket 192: Reduce cyclomatic complexity: merge_missing_ticket_records (CC=25)

- **ID**: ticket-192
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-20

## Goal and scope

SESSION_EXECUTION_AUTHORIZATION: the planfile queue owner handed STARTER-611
to this session with explicit completion instructions (checks, commit,
`planfile ticket done STARTER-611`).

`project/analysis.toon.yaml` reports `merge_missing_ticket_records` defined in
`src/koru/planfile_compat.py:106` with cyclomatic complexity 25 (limit 15).
Extract identifier/status normalization, reported-id collection, the coverage
test, diagnostic decoration, the recovery loop and report assembly into
focused module-level helpers with unchanged behaviour, bringing the function
under the limit 15.

## Acceptance criteria

- [x] AC-01: `merge_missing_ticket_records` cyclomatic complexity is below 15
      (code2llm re-run on this checkout, output outside the repo tree).
- [x] AC-02: `tests/test_planfile_compat.py` plus the existing consumer
      suites (`tests/test_queue_clean.py`, `tests/test_context.py`,
      `tests/test_planfile_queue.py`) pass.
- [x] AC-03: `ruff check` passes on `src/koru/planfile_compat.py` and
      `tests/test_planfile_compat.py`.
- [x] AC-04: `bash project/governance-check.sh --base origin/main` passes.

## Validation evidence

Recorded 2026-09-20 in `.worktrees/ticket-192--planfile-compat-complexity`
(branch `ticket/192-planfile-compat-complexity`, base `origin/main` = `17270faf`):

- AC-01: `code2llm <worktree> -f all -o /tmp/opencode/code2llm-ticket192
  --no-chunk --exclude *.md --exclude plugins` — the CC report no longer lists
  `merge_missing_ticket_records` (module row `planfile_compat CC=10`).
  Independent AST recount: `merge_missing_ticket_records` CC 25 → 3; every
  extracted helper ≤ 6 (`_recover_missing_records` 6, `_decorated_recovery` 5,
  `_ticket_identifier` 3, `_reported_ticket_ids` 3, `_already_covered` 3,
  `_compatibility_report` 3, `_normalized_status` 2). Behaviour differential
  old-vs-new over 2420 generated scenarios (5 sprint layouts × status matrix ×
  reported-payload shapes, including corrupt YAML) is byte-identical for the
  merged list and `report.to_dict()`.
- AC-02: `PYTHONPATH=src python -m pytest tests/test_planfile_compat.py
  tests/test_queue_clean.py tests/test_context.py tests/test_planfile_queue.py
  tests/test_cqrs_planfile_queue_context.py -q` — new suite (13 tests) passes;
  consumer suites pass except three pre-existing `TestPlanfileQueueLlm`
  transport failures that reproduce identically on the pristine accepted base
  (verified via `git stash -u` comparison) and are unrelated to this module.
- AC-03: `ruff check src/koru/planfile_compat.py tests/test_planfile_compat.py`
  — All checks passed. `ruff format --check` remaining finding is the
  pre-existing `unknown_status_count` span, unchanged verbatim from the
  accepted base.
- AC-04: `bash project/governance-check.sh --base origin/main` —
  `GOV-PASS: passed (0 errors, 0 warnings)`.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
