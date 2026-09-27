# Ticket 323: Hold unscoped duplication refactors before model execution

- **ID**: ticket-323
- **Owner**: agent:codex
- **Status**: IN_PROGRESS
- **Workflow state**: PUBLICATION
- **Created**: 2026-09-27

## Goal and scope

PLF-069 / semcod/koru#554. A c2004 duplication scan ticket (PLF-2624) is admitted as llm/interactive with only a jscpd report as its file scope. The queue classifies it as answer-only and requests done after text output without source changes. Hold this unscoped refactoring task before model calls or claiming work. Preserve explicit answer-only tasks and existing scoped edit verification.

SESSION_EXECUTION_AUTHORIZATION: user requested continued Koru repairs and pilots on2026-09-27. Isolated reproduction proves text-only false completion. Private c2004PLF-2657 runtime remains unactivated. Scope is two files in a dedicated leased worktree, disjoint from ticket322.

## Acceptance criteria

- [x] AC-01: An unscoped duplication scan ticket cannot invoke a model, claim work or complete, including when its model returns success.
- [x] AC-02: Report-only scope cannot pass as source refactoring; explicit analytical tasks and scoped edit contracts preserve existing behavior.
- [ ] AC-03: Queue regressions and governance pass; publish through the independent Validator.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.

Validation:110 queue tests+12subtests passed. After explicit closure binding for Ruff, both new tests+8subtests passed again. Governance, Ruff and whitespace checks pass. Independent exact-head publication pending.
