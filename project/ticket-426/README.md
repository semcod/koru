# Ticket 426: Isolate queue LLM transport tests

- **ID**: ticket-426
- **Owner**: codex-koru-llm-tests
- **Status**: IN_PROGRESS
- **Workflow state**: PUBLICATION
- **Created**: 2026-10-02

## Goal and scope

SESSION_EXECUTION_AUTHORIZATION: the user requested continuing repairs, tests and independent publication. Queue transport tests must use controlled SDK boundaries rather than operator configuration.

## Acceptance criteria

- [x] AC-01: Missing central runtime is tested deterministically, including refusal to fall back to a vendor CLI or provider override.
- [x] AC-02: A configured central route forwards the exact request and preserves model, output and usage without a live model call.
- [ ] AC-03: Publish through OneDev and independent Validator review.

Cross-project findings have their canonical owner in [the fleet analysis](https://github.com/subactor/docs/blob/main/architecture/analysis/local-ci-adoption.md).

## Validation

Queue and transport checks: 122 passed, 12 subtests passed. Governance and Ruff pass. The broader local MCP test expects legacy `redup check`, but the installed Redup advertises `scan`; the same failure reproduces on unchanged main and is outside this ticket. Required OneDev verification remains independent.
