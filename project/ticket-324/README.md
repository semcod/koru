# Ticket 324: Preserve queue admission blocks in outer autopilot

- **ID**: ticket-324
- **Owner**: agent:codex
- **Status**: IN_PROGRESS
- **Workflow state**: PUBLICATION
- **Created**: 2026-09-27

## Goal and scope

PLF-070 / semcod/koru#556; dependency of c2004 PLF-2657. PR555 prevents unscoped duplication work in the queue, but the outer autopilot can still drive its waiting_input message. Its skip decision also permits infrastructure_error. Carry a machine-readable admission block through the aggregate queue result and deny outer drive before labels, promotion or stagnation can override it. Preserve ordinary interactive waiting prompts.

SESSION_EXECUTION_AUTHORIZATION: continued Koru repairs and pilot observation requested by the user on2026-09-27. Isolated installed-artifact decision reproduction returns should_skip=False for both failures. No model invoked. Do not activate the previous runtime candidate until end-to-end admission is verified. Scope is the five allocated source/test files; no hardware, provider-policy or protected-publication changes.

## Acceptance criteria

- [x] AC-01: The real queue denial survives aggregation and blocks outer autopilot regardless of llm-ready labels and stagnation.
- [x] AC-02: Queue infrastructure, claim and configuration errors cannot trigger fallback execution; ordinary interactive waiting remains supported.
- [ ] AC-03: Focused regressions and governance pass; publish through independent Validator before runtime activation.

## Tracking boundary

Bounded implementation intent; raw evidence is in ignored recovery storage.

Validation:151tests+12subtests pass, including real queue denial through outer skip decision, initial and high-stagnation infrastructure failures, and ordinary waiting. Governance, Ruff and whitespace checks pass. Runtime remains unactivated; independent publication pending.
