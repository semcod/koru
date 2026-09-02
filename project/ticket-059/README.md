# Ticket 059: Replace nlp2coru with canonical nlp2koru aliases

- **ID**: ticket-059
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: PUBLICATION
- **Created**: 2026-09-02

## Goal and scope

Consolidate the remaining natural-language adapter pair in canonical
`nlp2koru`. The canonical package owns both current and compatibility APIs;
all ten `nlp2coru` source modules become one-release warning/re-export facades
without a second heuristic, model, provider boundary, dispatcher or CLI.

## Acceptance criteria

- [x] AC-01: The user's instruction to execute and continue the plan in
  `docs/*` is recorded as `SESSION_EXECUTION_AUTHORIZATION`.
- [x] AC-02: `nlp2koru` owns the combined deterministic mapping, model types,
  LLM compatibility helpers, chat rewrite, dispatch and CLI behavior.
- [x] AC-03: Every tracked `nlp2coru` source module contains only a warning,
  imports and direct aliases/re-exports from `nlp2koru`.
- [x] AC-04: Both package suites pass against the canonical implementation;
  legacy symbols are identical to their canonical compatibility exports and
  both console entry points resolve to the same `main` function.
- [x] AC-05: Changed-file Ruff, compile, governance, Docker Compose and diff
  checks pass before protected exact-head publication.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
