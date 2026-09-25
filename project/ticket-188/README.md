# Ticket 188: Split god module: src/koru/poa/planning.py

- **ID**: ticket-188
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-20

## Goal and scope

SESSION_EXECUTION_AUTHORIZATION: the queue owner instructed executing the
STARTER-736 planfile ticket (session handoff) after freeing one
application-workstream WIP slot (done: ticket-186 published via PR #371
protected merge, validator approval 5259531111).

`project/analysis.toon.yaml` flags `src/koru/poa/planning.py` as a god module
(511 lines, 4 classes, 15 methods). Split into focused submodules by
responsibility; keep behavior byte-identical.

## Plan

Pure code movement into the `koru.poa` package, dependency-ordered without
cycles:

- `errors.py` — `PlanningError`, `BindingNotFound`, `AmbiguousBinding`,
  `PolicyDenied` hierarchy.
- `validation.py` — shared primitive validators: SHA-256/ticket/policy/artifact/
  UTC regexes, `validate_ticket_and_hash`, `parse_utc` (formerly module-private
  `_validate_ticket_and_hash`/`_parse_utc`).
- `snapshots.py` — `build_source_snapshot`, `validate_source_registry_snapshot`
  and the three `_validate_snapshot_*` helpers.
- `policy_decisions.py` — `policy_input_hash`, `validate_policy_decision`,
  `_validate_decision_shape` (+ closed `POLICY_FIELDS` set, formerly
  `_POLICY_FIELDS`).
- `plan_compile.py` — `compile_inert_plan`, `verify_planning_result`,
  `_select_bindings`, `_validate_process_graph`, `_require_process_uri_kind`.
- `planning.py` — compatibility facade re-exporting the exact previous
  `__all__` (including the `canonical_json` re-export) for
  `koru.poa.planning`, `koru.poa.__init__` and `koru.poa.logs` consumers.

## Acceptance criteria

- [x] AC-01: `tests/test_poa_registry.py`, `tests/test_poa_contracts.py` and
      `tests/test_poa_logs.py` pass unmodified on this branch.
- [x] AC-02: facade parity — every former `koru.poa.planning.__all__` name is
      importable from `koru.poa.planning` with unchanged identity/behavior.
- [x] AC-03: `ruff check` and `ruff format --check` pass on `src/koru/poa/`.
- [x] AC-04: no module in `src/koru/poa/` exceeds the code2llm god-module
      thresholds; `./project/governance-check.sh --base origin/main` passes.

## Validation evidence

Branch `ticket/188-poa-planning-split`, base `origin/main` = `24d901bf`:

- AST equivalence vs `24d901bf:src/koru/poa/planning.py`: all 4 classes and 15
  functions moved verbatim; the only normalized deltas are the eight shared
  helper names losing their underscore prefix when promoted to
  `validation.py`/`policy_decisions.py` (`_parse_utc` → `parse_utc`,
  `_validate_ticket_and_hash` → `validate_ticket_and_hash`, `_SHA256_RE` →
  `SHA256_RE`, `_TICKET_RE`, `_POLICY_RE`, `_ARTIFACT_RE`, `_UTC_RE`,
  `_POLICY_FIELDS`). Pure movement; messages, decision order and hashes
  unchanged.
- `PYTHONPATH=src python -m pytest tests/test_poa_registry.py
  tests/test_poa_contracts.py tests/test_poa_logs.py -q`: 22 passed (governance
  sessionstart gate GOV-PASS inside the run). `tests/test_planning_llm.py`:
  37 passed.
- Facade parity script: `koru.poa.planning.__all__` identical (11 names),
  `koru.poa.__all__` identical (18 names), re-exports resolve to the new
  submodules, `koru.poa.logs.planning_events_for_result` import unaffected.
- `ruff check src/koru/poa/` + `ruff format --check src/koru/poa/`: clean.
- `code2llm <worktree> -f all -o /tmp/opencode/ticket188/code2llm --no-chunk
  --exclude '*.md' --exclude plugins`: HEALTH has no GOD entries;
  `src/koru/poa/planning.py` no longer flagged. Largest new module is
  `plan_compile.py` at 282 lines.
- `./project/governance-check.sh --base origin/main` (+ per-changed-file form):
  GOV-PASS, 0 errors, 0 warnings.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
