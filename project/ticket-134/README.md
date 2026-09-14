# Ticket 134: Prepare pinned documentation gate and consumer canaries

- **ID**: ticket-134
- **Owner**: codex
- **Status**: IN_PROGRESS
- **Workflow state**: PUBLICATION
- **Created**: 2026-09-14

## Goal and scope

SESSION_EXECUTION_AUTHORIZATION: continue the documentation campaign and
consumer pilots. Prepare Koru adoption of published docs 0.5.0, a bounded
preflight/final adapter and negative canaries. Link: semcod/koru#169.
Publish through independent review when required checks are available.
Do not overwrite primary Planfile migration, ticket-133 or the independently
modified OneDev executor configuration. Source preparation is not CI enforcement.

## Acceptance criteria

- [x] AC-01: Exact published docs pin and digest; no candidate-selected weaker checker.
- [x] AC-02: Preflight and final checks fail closed with immutable verified source;
  final requires trusted base, no document/test command execution.
- [ ] AC-03: Real Koru corpus and negative canaries pass, plus managed and stack checks.
- [ ] AC-04: Record publication and remaining protected executor deployment separately.

## Tracking boundary

13 consumer canaries PASS with the real published docs runtime; actual Koru
preflight and final base check PASS for five documents/maps. Existing verifier
regressions: 110 passed, 16 deselected by the repository configuration.
Ruff, Docker Compose and working-tree governance PASS. Exact-head governance
and protected publication remain required; no protected docs deployment claimed.

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
