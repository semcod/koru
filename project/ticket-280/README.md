# Ticket 280: Address code smell: Shotgun Surgery: executor locals in koru queue ticket parsing

- **ID**: ticket-280
- **Owner**: claude
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-27

## Goal and scope

Clear the code2llm `Shotgun Surgery: executor` smell (planfile ticket PLF-055,
reported for `src/koru/queue/ticket.py:263`) in `src/koru/queue/ticket.py`.

Five functions in the file declare a local named `executor` holding the
ticket's executor block (`_is_human_executor`, `_should_skip_deferred_human`,
`ticket_command`, `ticket_api_request`, `ticket_taskand_request`; reproduced
with the installed code2llm `DFGExtractor` mutation grouping on the file AST:
69 mutation records). The detector groups mutations by (file, variable) and
fires at >= 5 scopes — the shared *name* is the smell; each function actually
consumes a different piece of the executor declaration (the raw block guarded
for human-kind classification, the kind string gated by the operator-defer
policy, and the handler each of the three request builders falls back to:
command, endpoint, process URI).

Fix: stage-accurate selections — `declared_executor` (`_is_human_executor`,
raw declaration, isinstance-guarded), `executor_kind`
(`_should_skip_deferred_human`, the defer-gate kind string) and `handler`
(`ticket_command`/`ticket_api_request`/`ticket_taskand_request`, the
executor-declared handler fallback). The `executor` mutation group drops from
5 scopes to 0. Pure rename of function-internal locals plus selection of
exactly the piece each stage consumes; no signature, return shape or behavior
change; no other file is touched.

Tests: the suites covering these paths
(`tests/test_queue_ticket_selection.py`, `tests/test_ticket_command*.py`,
`tests/test_planfile_queue.py`) run unchanged as the behavioral proof of the
pure rename.

## Acceptance criteria

- [x] AC-01: code2llm smell re-scan no longer reports `shotgun_surgery` for
  the variable `executor` in `src/koru/queue/ticket.py`, and introduces no new
  (file, variable) mutation group at or beyond the threshold. Verified with
  the installed code2llm `DFGExtractor` mutation grouping on the file AST
  (standalone extract; `ProjectAnalyzer.analyze` on copies/worktrees
  silently yields empty scopes): baseline content reports `Mutation of
  variable 'executor' spans 5 functions` from exactly the five scopes listed
  above; renamed content reports an `executor` group of 0 scopes; file
  mutation record count unchanged (69, pure rename); the new locals land at
  1/1/3 scopes and the untouched `inputs` group stays at 4 — all below the
  >= 5 threshold.
- [x] AC-02: the targeted pytest suites pass unchanged in the ticket
  worktree; `ruff check src/koru/queue/ticket.py` reports zero errors.
- [x] AC-03: `bash project/governance-check.sh --base <merge-base>` passes
  with 0 errors from the ticket worktree (GOV-PASS, 0 errors, 0 warnings).

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
