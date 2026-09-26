# Ticket 241: centralize code2llm artifact candidate paths in scan

- **ID**: ticket-241
- **Owner**: claude
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-26

## Goal and scope

Remove the code2llm `Shotgun Surgery: candidates` smell in
`src/koru/scan.py:451` (mutation of `candidates` spanning 6 functions) —
planfile ticket PLF-044.

The six functions that each hand-built a `candidates` tuple of artifact paths
and resolved the first existing file (`_find_analysis_file`,
`_code2llm_cc_locations`, `_code2llm_module_paths`,
`_merge_call_graph_locations`, `_planfile_dup_groups_are_extern_mirrors`,
`_should_skip_code2llm_dup_ticket`) now share one declaration: the probe
locations for the three code2llm artifacts live in module constants
(`_ANALYSIS_ARTIFACT_PATHS`, `_PLANFILE_TICKETS_ARTIFACT_PATHS`,
`_CALLS_ARTIFACT_PATHS`, most preferred first) and resolution goes through the
pre-existing `_first_existing_artifact` helper. `_load_yaml_mapping` takes
`(project, rel_paths)` instead of pre-built absolute candidates. Changing
where code2llm artifacts are probed is now one constant edit instead of six
hand-written tuples.

Behavior is preserved verbatim, including the analysis probe order where the
nested plain-text `project/analysis.toon` beats a repo-root
`analysis.toon.yaml` copy; a new regression test pins that order.

## Acceptance criteria

- [x] AC-01: Scope is approved by human owner (SESSION_EXECUTION_AUTHORIZATION).
- [x] AC-02: `tests/test_scan.py` passes including the new probe-order regression test; its 7 remaining failures are byte-identical pre-existing reds at base HEAD (verified in a detached HEAD worktree).
- [x] AC-03: The consumer slice (`tests/test_scan_phase.py`, `tests/test_todo2code_discovery.py`, `tests/test_autonomous.py`, `tests/test_fleet_admission.py`, `tests/test_scan_split.py`, `tests/test_scan_todo_rust.py`, `tests/test_scan_todo.py`, `tests/test_code2llm_discovery.py`, `tests/test_ticket_evidence.py`, `tests/test_execution_plan.py`, `tests/test_plan_usefulness_scoring.py`, `tests/test_refactor_planfile_handoff.py`) passes except 2 `test_autonomous.py` chat-activity reds that also fail at base HEAD.
- [x] AC-04: `ruff check` reports no findings on `src/koru/scan.py` and `tests/test_scan.py`; `ruff format --check` is clean on `src/koru/scan.py` (the `tests/test_scan.py` format drift is pre-existing at base HEAD and outside the added lines).
- [x] AC-05: `bash project/governance-check.sh` reports 0 errors.

## Tracking boundary

SESSION_EXECUTION_AUTHORIZATION: the PLF-044 planfile handoff (user message
2026-09-26) instructs to make the smallest refactor removing the
`Shotgun Surgery: candidates` smell in `src/koru/scan.py:451`, run local
tests, and dispose of planfile ticket PLF-044 (`done` when checks pass and the
work is complete).

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
