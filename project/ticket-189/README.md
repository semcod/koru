# Ticket 189: Reduce cyclomatic complexity: _question_answers_via_llm (CC=26)

- **ID**: ticket-189
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-20

## Goal and scope

SESSION_EXECUTION_AUTHORIZATION: the queue owner handed the STARTER-606
planfile ticket (semcod/koru#353) to this session for autonomous execution;
the ticket input below is executed unmodified.

code2llm reports `src.koruapi.opencode_supervisor._question_answers_via_llm`
at `src/koruapi/opencode_supervisor.py:53` with cyclomatic complexity 26
(limit 15). Extract the stages (SubLLM import resolution, question spec
building, subllm transport, JSON salvage parsing, answer normalization) into
focused module-level helpers with unchanged behavior, bringing the function
under the limit 15.

## Acceptance criteria

- [x] AC-01: `_question_answers_via_llm` cyclomatic complexity is below 15
      (code2llm re-run on this checkout, output outside the repo tree).
- [x] AC-02: `tests/test_dashboard_terminals.py` passes unmodified.
- [x] AC-03: `ruff check` and `ruff format --check` pass on
      `src/koruapi/opencode_supervisor.py`.
- [x] AC-04: `./project/governance-check.sh --base origin/main` passes.

## Validation evidence

Recorded 2026-09-20 in `.worktrees/ticket-189--opencode-supervisor-question-llm`
(branch `ticket/189-opencode-supervisor-question-llm`, base `origin/main` = `0f60955f`):

- AC-01: `code2llm . -f all -o /tmp/opencode/code2llm-ticket189b --no-chunk
  --exclude '*.md' --exclude plugins` — the CC findings no longer mention
  `_question_answers_via_llm` (0 occurrences; the module row keeps only the
  out-of-scope pre-existing `supervise_once CC=37` hotspot). Independent AST
  recount: `_question_answers_via_llm` 26 → 9; every extracted helper ≤ 9
  (`_normalize_answer_set` 9, `_parse_answer_payload` 7, `_question_spec` 6,
  `_subllm_answer_stdout` 4, `_load_subllm` 3). A 17-case differential harness
  (valid/invented-label/prose-wrapped/`null`/shape-mismatch/transport-crash/
  no-module inputs) compared the original and refactored implementations:
  identical return values and log sequences in every case.
- AC-02: `PYTHONPATH=src python -m pytest tests/test_dashboard_terminals.py
  tests/test_koruapi_transports.py tests/test_testql_bridge.py -q` —
  50 passed, unmodified.
- AC-03: `ruff check src/koruapi/opencode_supervisor.py` — All checks passed;
  `ruff format --check` — clean. The module was not previously ruff-clean;
  the two pre-existing findings (UP035 `Callable` import, one E501 f-string
  in `supervise_once`) were fixed and one `ruff format` pass applied — no
  behavior change (identical concatenated strings).
- AC-04: `bash project/governance-check.sh --base origin/main` —
  `GOV-PASS: passed (0 errors, 0 warnings)`.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
