# Ticket 190: Reduce cyclomatic complexity: _scan_serve_processes (CC=22)

- **ID**: ticket-190
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-20

## Goal and scope

SESSION_EXECUTION_AUTHORIZATION: the queue owner handed the STARTER-607
planfile ticket to this session for autonomous execution; the ticket input
below is executed unmodified. The WIP precondition recorded there is already
satisfied: the application workstream is 3/4 after ticket-189 merged
(semcod/koru#373), verified via `.governance/work_start_check.py
--workstream application --allocation-check` (route NEW_TICKET_CANDIDATE,
zero blockers) immediately before this allocation.

code2llm reports `src.koruapi.opencode_terminals._scan_serve_processes`
at `src/koruapi/opencode_terminals.py:165` with cyclomatic complexity 22
(limit 15). Extract the stages (cmdline reading, opencode-serve argv
matching, --port/--hostname parsing, int coercion) into focused
module-level helpers with unchanged behavior, bringing the function and
every helper under the limit 15. Add behavior-pinning tests for the
extracted helpers and the scan in a new
`tests/test_opencode_serve_scan.py` (existing suites mock
`_scan_serve_processes` directly, so the new tests pin the real logic).

## Acceptance criteria

- [x] AC-01: `_scan_serve_processes` cyclomatic complexity is below 15
      and every extracted helper is below 15 (independent AST recount).
- [x] AC-02: new `tests/test_opencode_serve_scan.py` passes and
      `tests/test_dashboard_terminals.py` passes unmodified.
- [x] AC-03: `ruff check` and `ruff format --check` pass on
      `src/koruapi/opencode_terminals.py`.
- [x] AC-04: `./project/governance-check.sh --base origin/main` passes.

## Validation evidence

Recorded 2026-09-20 in `.worktrees/ticket-190--opencode-serve-scan-complexity`
(branch `ticket/190-opencode-serve-scan-complexity`, base `origin/main` = `bea8ab25`):

- AC-01: independent AST recount (radon-equivalent: branches + boolops +
      comprehension filters + excepts): `_scan_serve_processes` 22 → 7;
      every extracted helper ≤ 8 (`_parse_serve_listen_args` 8,
      `_read_cmdline` 4, `_is_opencode_serve` 4, `_to_int` 2). A 288-case
      differential harness (24 argv shapes × 4 pid shapes × 3 /proc fixture
      mixes, including unreadable cmdlines, non-numeric entries, invalid
      port values, last-wins duplicates, port 0 and positional edge cases)
      compared the original origin/main function and the refactored one:
      identical results in every case, 0 mismatches.
- AC-02: `PYTHONPATH=src python -m pytest tests/test_opencode_serve_scan.py
      tests/test_dashboard_terminals.py -q` — 66 passed
      (24 new behavior-pinning tests; existing suite unmodified).
- AC-03: `ruff check src/koruapi/opencode_terminals.py` — All checks
      passed; `ruff format --check` — clean. The module was not previously
      ruff-clean; the three pre-existing findings (F401 unused `sys`
      import, two UP017 `datetime.timezone.utc`) were fixed and one
      `ruff format` pass applied — no behavior change (differential harness
      re-run clean after formatting).
- AC-04: `bash project/governance-check.sh --base origin/main` —
      `GOV-PASS: passed (0 errors, 0 warnings)`.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant
prose and raw command logs are not required delivery output.
