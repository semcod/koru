# Ticket 305: Pure step parsers in korudsl library to clear shotgun surgery

- **ID**: ticket-305
- **Owner**: claude
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-27

## Session authority

SESSION_EXECUTION_AUTHORIZATION: the operator handed this lane over with an
explicit request to work planfile ticket PLF-040, implement the smallest
smell-removing refactor and run the local tests (recorded here per
AGENTS.md rule 4; no human-owned `user-*.md` file was created or edited).

## Goal and scope

Clear the code2llm `Shotgun Surgery: goal['steps']` smell (planfile ticket
PLF-040, reported for `src/korudsl/library.py:38`, dedupe key
`code2llm:smell:shotgun_surgery:src/korudsl/library.py:38:Shotgun
Surgery: goal['steps']`) in `src/korudsl/library.py`.

Five step-line handlers each mutate the goal's step list in place
(`_handle_set`, `_handle_wait`, `_handle_get`, `_handle_save`,
`_handle_if`; reproduced with the installed code2llm `DFGExtractor`
mutation grouping on the file AST: the `goal['steps']` group has 5
mutation scopes, 39 total mutation records in the file, representative
line 38 = `_handle_wait`). The detector groups mutations by
(file, variable) and fires at >= 5 scopes — adding a new step prefix
today means touching one handler plus the dispatch table while the step
list keeps being appended to from five different places.

Staleness verified before work: the discovery artifact's
`files[0].sha256` (`83155a62…`) matches the current file byte-for-byte,
and the two merged commits citing a PLF-040 id (ticket-263, ticket-295)
target different dedupe keys — planfile sprint rolls reuse ids — so this
dedupe key is genuinely outstanding.

Fix: pure selection. The five handlers become pure line → step-record
parsers (`_parse_set`, `_parse_wait`, `_parse_get`, `_parse_save`,
`_parse_if`) that no longer take `goal`; `_apply_prefixed_line` keeps the
only `goal["steps"].append(...)` in the file. The mixed
`_PREFIX_HANDLERS` table (which needed a `FUNC:` special case for the
3-argument function handler) is replaced by a `_STEP_PARSERS` table plus
explicit `FUNC:`/`ERROR `/`CORRECT ` dispatch, which is behavior-identical
(no prefix is a prefix of another).

Not changed: `_handle_error`/`_handle_correct` keep the mutating-objective
shape (the `goal['objectives']` group is 2 scopes, far below the
threshold); the emit path (`lines` group, 4 scopes) is untouched; no
public symbol changes (`korudsl.__init__` re-exports only the four public
functions, all unchanged); no other file touched.

## Acceptance criteria

- [x] AC-01: DFGExtractor mutation grouping on the file AST reports the
      `goal['steps']` group at 1 scope (`_apply_prefixed_line`) after the
      refactor (baseline 5 scopes, exactly the ticket's "spans 5
      functions"); no variable group newly reaches the >= 5 threshold
      (`lines` stays at 4, `goal['objectives']` at 2).
- [x] AC-02: `tests/test_korudsl.py` passes unchanged and
      `ruff check src/korudsl/library.py` is clean.
- [x] AC-03: `project/governance-check.sh --base <merge-base>` reports
      GOV-PASS from this worktree.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant
prose and raw command logs are not required delivery output.
