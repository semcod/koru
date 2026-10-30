# Ticket 477: Validate Koru model responses before route success

- **ID**: ticket-477
- **Owner**: agent:codex
- **Status**: IN_PROGRESS
- **Workflow state**: PUBLICATION
- **Created**: 2026-10-30

## Goal and scope

SESSION_EXECUTION_AUTHORIZATION: the operator requested continued response-quality
integration and independent merges. Use the public SubLLM task validator before
accepting structured Koru responses, allowing central policy to select another
model after rejection. Preserve policy model selection, plain-text chat rewrites,
custom backend signatures and both registered route aliases.

The complete published native allocator was invoked with explicit disjoint paths
against the adopter's work-start and Worktrees planner. Its owned canonical lease
binds this session; no managed primary files or pre-existing edits were changed.
The independent full-standard upgrade in ticket-476 is not a dependency of this
application slice and remains subject to its unresolved protected checks.

## Acceptance criteria

- [x] AC-01: Default structured calls declare JSON and pass a task validator to
  public SubLLM before its success accounting and model failover.
- [x] AC-02: Unsupported actions, invalid optional types and unusable DSL are
  rejected; accepted DSL passes the existing grammar and schema without execution.
- [ ] AC-03: Both aliases, custom backends and plain-text rewriting retain their
  interfaces; deterministic regressions and required protected checks pass.

## Non-goals

No provider policy changes, LLM judge, new runtime dependencies, command execution,
standard upgrades, global provider quarantine or universal semantic correctness claim.

Validation: 259 tests and 12 subtests passed across both NLP aliases and the
required queue/MCP baseline. Ruff passed. A test using public SubLLM completion
and a substituted provider transport confirmed that task-invalid GLM-5.3 output
retries GLM-5.3 Flash; usage and health paths are isolated in temporary test state.
Independent protected CI and exact-head publication remain required.
