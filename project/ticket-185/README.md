# Ticket 185: Split large module: koru.autonomous into cohesive submodules

- **ID**: ticket-185
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: PUBLICATION
- **Created**: 2026-09-20

## Goal and scope

SESSION_EXECUTION_AUTHORIZATION: the queue owner instructed executing the
STARTER-604 planfile ticket autonomously (`Split large module: autonomous`,
code2llm layer-hotspot signal).

`project/analysis.toon.yaml` flags `autonomous` in LAYERS as a large/hot
module (1240 lines, 0 classes, 77 methods, CC=7). The module is already a
monkeypatch-compatibility facade over `koru.autonomy.operator.*`; extract its
two cohesive non-patch-point responsibilities — environment reporting
(doctor/status/self-heal) and CLI argv configuration — into focused submodules
of a new `koru.autonomous` package, keeping the facade semantics byte-for-byte
so every existing monkeypatch target on `koru.autonomous` keeps working.

## Acceptance criteria

- [x] AC-01: Every former `koru.autonomous` module attribute (including the
      `__all__` names, `_consume_web_flag` and every function referenced by
      tests as a monkeypatch target) remains importable from `koru.autonomous`.
- [x] AC-02: `tests/test_autonomous.py`, `tests/test_dashboard_logs.py`,
      `tests/test_cli.py::auto` surfaces and the autonomy operator suites pass
      unmodified (monkeypatch targets unchanged).
- [x] AC-03: Focused regression tests exist for the extracted
      `koru.autonomous.reporting` and `koru.autonomous.argv_config`
      submodules and pass.
- [x] AC-04: Ruff check and format pass on the new package.
- [x] AC-05: `./project/governance-check.sh --base origin/main` passes with
      zero errors.

## Validation evidence

Recorded 2026-09-20 in `.worktrees/ticket-185--autonomous-split`
(branch `ticket/185-autonomous-split`, base `origin/main` = `5ad452d0`):

- AC-01: `PYTHONPATH=src .venv/bin/python -c "import koru.autonomous as m;
  assert all(hasattr(m, n) for n in m.__all__); assert hasattr(m,
  '_consume_web_flag')"` — ok. Full `dir()` parity check against the
  pristine base module: only `json` (unused helper import, referenced by no
  test or source patch target) was dropped; `argv_config`/`reporting`
  submodules were added.
- AC-02: `PYTHONPATH=src .venv/bin/python -m pytest tests/test_autonomous.py
  tests/test_dashboard_logs.py -q` — 202 passed, 3 failed; all three
  (`test_skip_due_to_recent_chat_activity_*`,
  `test_skip_chat_activity_blocks_self_drive_even_without_ticket_ack`)
  reproduce identically on the pristine base sources via `git archive HEAD`
  (pre-existing, chat-activity heuristic, unrelated to the split).
  `tests/test_cli.py -k auto` — 19 passed + 3 subtests, 1 pre-existing
  failure (`TestAutopilotReexecToProjectVenv`, venv re-exec, fails on base).
  Operator suites (`test_autonomous_startup/runtime/loop_runner/operator/
  operator_reload/operator_unsupported_ide`, `test_doctor_koru_auto_probe`,
  `test_autonomous_status_consumers`, `test_autonomous_diagnostics`,
  `test_autonomous_up`, `test_autonomous_scenarios`,
  `test_autonomous_cycle_config`, `test_lane_plugin_matching`) — 131 passed,
  3 pre-existing failures (venv re-exec x2, lane plugin matching), all
  reproducing identically on the pristine base sources.
- AC-03: `PYTHONPATH=src .venv/bin/python -m pytest
  tests/test_autonomous_reporting.py tests/test_autonomous_argv_config.py -q`
  — 35 passed.
- AC-04: `ruff check src/koru/autonomous/ tests/test_autonomous_reporting.py
  tests/test_autonomous_argv_config.py` and `ruff format --check` — clean.
- AC-05: `bash project/governance-check.sh --base origin/main` —
  `GOV-PASS: passed (0 errors, 0 warnings)`.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
