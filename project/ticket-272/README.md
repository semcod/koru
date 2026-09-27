# Ticket 272: Address code smell: shotgun surgery data locals in planning llm parsing

- **ID**: ticket-272
- **Owner**: claude
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-27

## Goal and scope

Clear the code2llm `Shotgun Surgery: data` smell (planfile ticket PLF-047,
reported for `src/koru/autonomy/planning_llm_parsing.py:95`) in
`src/koru/autonomy/planning_llm_parsing.py`.

Seven functions in the file mutate a local named `data`
(`parse_json_object`, `parse_evaluation`, `parse_improved_prompt`,
`parse_action_advice`, `parse_reflection`, `parse_strategy_tuning`,
`parse_ticket_priority`). The detector groups mutations by (file, variable)
and fires at >= 5 scopes — the shared *name* is the smell; each function
actually holds an independent decoded LLM JSON payload (the raw decoded JSON
value before the dict check, an evaluation, an improved-prompt response, an
action advice, a reflection, a strategy tuning, or a ticket-priority
response).

Fix: stage-accurate local names — `decoded` (raw `json.loads` value of any
type), `evaluation`, `prompt_payload`, `advice`, `reflection`, `tuning`,
`priority_payload`. The `data` mutation group drops from 7 scopes to 0. Pure
rename of function-internal locals; no signature, return shape or behavior
change; the unrelated private `_parse_json_object` in
`src/koru/integrations/photo_vql_llm_detect.py` keeps its own locals. No
other file is touched.

Tests: the module's only in-repo importer is the
`koru.autonomy.planning_llm` facade, exercised end-to-end (all six parse
functions) by `tests/test_planning_llm.py`, which runs unchanged as the
behavioral proof of the pure rename.

## Acceptance criteria

- [x] AC-01: code2llm smell re-scan no longer reports `shotgun_surgery` for
  the variable `data` in `src/koru/autonomy/planning_llm_parsing.py`, and
  introduces no new smell for that file. Verified with the installed code2llm
  `DFGExtractor` mutation grouping on the file AST (standalone extract;
  `ProjectAnalyzer.analyze` on copies/worktrees silently yields empty
  scopes): baseline content reports `Mutation of variable 'data' spans
  7 functions` from exactly the seven scopes listed above; renamed content
  reports a `data` group of 0 scopes; file mutation count unchanged (18,
  pure rename); every renamed local lands at exactly 1 scope, far below the
  >= 5 threshold.
- [x] AC-02: `python3 -m pytest tests/test_planning_llm.py -q` passes
  unchanged in the ticket worktree; `ruff check
  src/koru/autonomy/planning_llm_parsing.py` reports zero errors.
- [x] AC-03: `bash project/governance-check.sh --base <merge-base>` passes
  with 0 errors from the ticket worktree (GOV-PASS, 0 errors, 0 warnings).

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
