# Ticket 227: decompose god function validate-vql-chat-target

- **ID**: ticket-227
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-26
- **Planfile ticket**: PLF-053 (code2llm god-function smell, severity 0.798)

## Goal and scope

Remove the code2llm `God Function: validate_vql_chat_target` smell in
`src/koru/integrations/photo_vql_validation.py:456` (CC=13, fan-out=11,
mutations=23; thresholds fan-out > 10, mutations > 6, CC > 12) with the
smallest behavior-preserving decomposition, and run the local tests.

Session authorization: the planfile PLF-053 handoff explicitly requests
execution ("Make the smallest refactor that removes the smell and run local
tests") — recorded as `SESSION_EXECUTION_AUTHORIZATION` per AGENTS.md step 4.

## Approach

- `code2llm` double-counts tuple-unpack assignment targets, so the 7-name
  `_target_geometry` unpack alone yields 14 of the 23 mutations. Bind it once
  as a `TargetGeometry` NamedTuple; make `_target_bounds_size` return a
  `BoundsSize` NamedTuple for the same reason.
- Move `app_match` / `label_ok` / element-size derivations into
  `_collect_vql_validation_errors` / `_live_vql_validation_errors`, extract
  `_target_is_map` and the audit report literal into
  `_vql_chat_validation_report`.
- Public surface is untouched: `validate_vql_chat_target` keeps its signature
  and exact 12-key result dict; `__all__` unchanged; the `vdisplay_client`
  facade keeps late-binding patch targets working.

## Acceptance criteria

- [x] AC-01: code2llm reports no god function for `validate_vql_chat_target`
      and none of the touched/new helpers is flagged.
- [x] AC-02: existing photo VQL tests pass unchanged plus one new regression
      test asserting the exact full result dict.
- [x] AC-03: `bash project/governance-check.sh` passes with 0 errors.

## Notes

- `validate_chat_coords_for_ide` in the same file already exceeds fan-out and
  mutation thresholds on main; it is a separate lower-severity smell, out of
  scope here (recorded in intent `nonGoals`).
- No `project/duplication.toon.yaml` exists for the touched paths (checked
  2026-09-26), so no duplication-review entries apply.
- Staleness check per ticket evidence: `analysis.toon.yaml` sha256
  `470d85f7…` and `photo_vql_validation.py` sha256 `294deb02…` both match the
  PLF-053 evidence; metrics reproduced locally (CC=13 / fan-out=11 /
  mutations=23) before starting.
- Behavior equivalence was proven differentially: the HEAD implementation and
  the refactored one produce identical 12-key reports over 34 targeted
  comparisons (code-edit, capture mismatch, map fallback/calibration,
  background/small bounds, empty label, low confidence, x/y override,
  surface-window ids, vscode coords, terminal-noise labels, width/height
  bounds keys, fallback source, note-label fallback).
- Pre-existing suite artifact (not this ticket): running
  `tests/test_jetbrains_surface_chat_target.py` alone fails its two
  `jetbrains_chat_target_from_surface` tests because nothing imports
  `vdisplay_client` first, so koruide's noise vocabulary stays unregistered;
  the same two tests fail solo on clean main (verified by temporarily
  restoring the HEAD source). The AC-02 three-file command passes 108/108.

## Results

- AC-01: `code2llm.api.analyze('src/koru/integrations')` reports no god
  function for `validate_vql_chat_target` (now CC=3, fan-out=7, mutations=5;
  was CC=13 / fan-out=11 / mutations=23). No touched or new helper is
  flagged; `_live_vql_validation_errors` sits at mutations=6 (limit 6).
- AC-02: 108 passed, 2 skipped, 1 deselected
  (`tests/test_jetbrains_surface_chat_target.py`,
  `tests/test_photo_vql_drive.py`, `tests/test_photo_vql_orchestrator.py`),
  including the new full-report golden test.
- AC-03: `bash project/governance-check.sh` → GOV-PASS (0 errors, 0 warnings).

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant
prose and raw command logs are not required delivery output.
