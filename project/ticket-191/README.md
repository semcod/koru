# Ticket 191: Reduce cyclomatic complexity: get_agent_availability (CC=15)

- **ID**: ticket-191
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-20

## Goal and scope

SESSION_EXECUTION_AUTHORIZATION: the planfile queue owner handed STARTER-609
to this session with explicit completion instructions (checks, commit,
`planfile ticket done STARTER-609`).

`project/analysis.toon.yaml` reports `get_agent_availability` defined in
`src/koru/agent_availability.py:137` with cyclomatic complexity 15 (limit 15).
Extract the environment-override lookup, the registry-entry parsing and the
temporary-block expiry reset into focused module-level helpers with unchanged
behaviour, bringing the function under the limit 15.

## Acceptance criteria

- [x] AC-01: `get_agent_availability` cyclomatic complexity is below 15
      (code2llm re-run on this checkout, output outside the repo tree).
- [x] AC-02: `tests/test_agent_availability.py` passes unmodified.
- [x] AC-03: `ruff check` passes on `src/koru/agent_availability.py`.
- [x] AC-04: `./project/governance-check.sh --base origin/main` passes.

## Validation evidence

Recorded 2026-09-20 in `.worktrees/ticket-191--agent-availability-complexity`
(branch `ticket/191-agent-availability-complexity`, base `origin/main` = `f171fe09`):

- AC-01: `code2llm <worktree> -f all -o /tmp/opencode/code2llm-ticket191
  --no-chunk --exclude *.md --exclude plugins` — the CC report no longer lists
  `get_agent_availability` (module row `agent_availability CC=7`). Independent
  AST recount: `get_agent_availability` CC 15 → 5; every extracted helper ≤ 7
  (`_availability_from_registry_entry` 7, `_with_expired_block_reset` 4,
  `_environment_override` 3). Behaviour differential over 18 scenarios
  (empty id, env precedence both-ways, registry miss/hit, invalid entries,
  expiry boundary at equality, corrupt registry) is byte-identical to the
  accepted base.
- AC-02: `PYTHONPATH=src python -m pytest tests/test_agent_availability.py -q`
  — 7 passed, unmodified.
- AC-03: `ruff check src/koru/agent_availability.py` — All checks passed.
  `ruff format --check` findings on pre-existing untouched spans are unchanged
  from the accepted base (verified via `git stash` comparison); the refactor
  keeps the module's existing formatting idiom verbatim.
- AC-04: `bash project/governance-check.sh --base origin/main` —
  `GOV-PASS: passed (0 errors, 0 warnings)`.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
