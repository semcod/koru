# Ticket 186: Reduce cyclomatic complexity: MultiAgentOrchestrator.run (CC=31)

- **ID**: ticket-186
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-20

## Goal and scope

SESSION_EXECUTION_AUTHORIZATION: the queue owner instructed re-running the
STARTER-619 planfile ticket unmodified after freeing one application-workstream
WIP slot (done: ticket-185 published via PR #370 protected merge).

code2llm reports `src.koru.multi_agent.MultiAgentOrchestrator.run` at
`src/koru/multi_agent.py:304` with cyclomatic complexity 31 (limit 15).
Extract the run() stages (GitHub sync, queue collection, dry-run plan,
worker reaping, backlog promotion, worker spawn) into focused helper methods
with unchanged behavior, bringing the method under the limit 15.

## Acceptance criteria

- [x] AC-01: `MultiAgentOrchestrator.run` cyclomatic complexity is below 15
      (code2llm re-run on this checkout, output outside the repo tree).
- [x] AC-02: `tests/test_multi_agent.py` passes unmodified.
- [x] AC-03: `ruff check` and `ruff format --check` pass on
      `src/koru/multi_agent.py`.
- [x] AC-04: `./project/governance-check.sh --base origin/main` passes.

## Validation evidence

Recorded 2026-09-20 in `.worktrees/ticket-186--multi-agent-run-complexity`
(branch `ticket/186-multi-agent-run-complexity`, base `origin/main` = `52c5a3a2`):

- AC-01: `code2llm <worktree> -f all -o /tmp/opencode/code2llm-ticket186
  --no-chunk --exclude *.md --exclude plugins` — the report no longer lists
  any CC hotspot in `multi_agent` (module row `CC=9`; the only remaining CC
  finding is `_parse_layer_hotspot_suggestions CC=15` in an unrelated
  pre-existing module). Independent AST recount: `run` CC 32 → 9; every
  extracted helper ≤ 8 (`_sync_github_issues` 7, `_try_spawn_next_worker` 8,
  `_reap_finished_workers` 5, `_promote_backlog_task` 5,
  `_print_dry_run_plan` 3, `_collect_pending_tasks` 2).
- AC-02: `PYTHONPATH=src python -m pytest tests/test_multi_agent.py -q` —
  8 passed; plus `tests/test_cli_auto.py` — 10 passed total, unmodified.
- AC-03: `ruff check src/koru/multi_agent.py` — All checks passed;
  `ruff format --check` — clean (after one `ruff format` pass on the edit).
- AC-04: `bash project/governance-check.sh --base origin/main` —
  `GOV-PASS: passed (0 errors, 0 warnings)`.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
