# Ticket 310: Use native Planfile readiness before claiming queued work

- **ID**: ticket-310
- **Owner**: agent:codex
- **Status**: IN_PROGRESS
- **Workflow state**: PUBLICATION
- **Created**: 2026-09-27

## Goal and scope

PLF-060 / semcod/koru#516: a real isolated queue pilot ran a high-priority
dependent before its unfinished prerequisite. The dependent failed and stayed
blocked after the prerequisite completed. Delegate runnable admission to the
configured Planfile CLI before claim/start, retaining Koru queue targeting,
priority and human deferral among tickets admitted by Planfile.

SESSION_EXECUTION_AUTHORIZATION: the user requested continued source fixes,
autonomy pilots, tests and protected publication on 2026-09-27. Allocation used
the reviewed HOME allocator at 5f21f21ea8f06c551b6ff3ba12930e399a6e6944
(wellmanifest/new-project#411), retaining adopter-owned admission and layout
checks. No managed adopter files or another writer's changes were modified.

## Acceptance criteria

- [x] AC-01: Native dependency, execution-state and autonomy-boundary admission
  runs before claim/start, also for explicitly targeted and legacy object tickets.
- [x] AC-02: Invalid/unavailable readiness evidence fails closed without execution.
- [x] AC-03: Real native Planfile + Koru + local-shell pilot runs A then B and
  preserves tasks with unresolved dependencies; relevant queue regressions pass.

## Boundaries

This slice does not change model permissions, hardware, Taskand, process guards
or shell-drive completion policy. AUTODONE remains off in c2004 until its
separate evidence defect is repaired. Protected Validator controls merge.

## Validation

- Queue regressions: 259 passed and 9 subtests; earlier admission suite included
  invalid reports, targeted legacy objects, waiting state and missing dependencies.
- Native admission cases with Planfile v0.1.123 source (the lock version):
  14 passed. The CLI report includes all sprints for archived prerequisites,
  while execution remains restricted to the current candidate list.
- Real candidate pilot: API health GET -> shell proof -> shell verification;
  all three completed in dependency order. A critical missing-dependency task
  remained open/unclaimed, and the next cycle was idle. This pilot used no
  external readiness wrapper and changed no production runtime or hardware.
- The real native dependency regression is in test_planfile_queue.py, included
  by the deployed protected OneDev profile.

The additional fixture adapter only supplies native-report responses to existing
executor/lifecycle unit fakes whose tickets are already declared runnable. Native
admission regressions and the real pilot do not use that adapter.

MCP server regressions: 19 passed. Import-linter 2.13: all three contracts kept
(731 files / 1927 dependencies). Modified-path Ruff and whitespace checks pass.
