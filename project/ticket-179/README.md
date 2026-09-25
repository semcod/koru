# Ticket 179: Route small lint tasks and show observed model history

- **ID**: ticket-179
- **Owner**: codex
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-19

## Goal and scope

SESSION_EXECUTION_AUTHORIZATION: user says popraw after the verified model-routing
and logging audit. Implements STARTER-732 and STARTER-734 in Koru only.
SubLLM ticket082 has an independent writer; do not modify that checkout.
Audit ticket178 remains in protected publication. This ticket supplies material code.

## Acceptance criteria

- [x] AC-01: Bounded lint metadata can select the configured cheaper model; explicit
  pins, unknown/complex scopes and execution authority remain intact. Requests and
  observed executions have honest separate provenance without prompts or credentials.
- [ ] AC-02: Read-only history projections preserve source and coverage limits; tests
  pass and independent delivery is invoked. Dashboard and parser repair are a dependent slice.

## Session boundary

Owner session codex-koru-model179-20260919; maxActiveMinutes:120.
No model retry, scope expansion or self-approval authority is added.

Budget split: UI/parser patch preserved in private recovery for a dependent allocated ticket;
this slice owns only routing and model-history projections (8 implementation files).

Validation: 208 existing/new regression tests and 37 focused tests passed; Ruff and diff checks pass.
Dependent UI/parser slice: ticket180 (STARTER-734). Real-provider canary tracked privately.

Planfile compatibility: canonical task facts live in source.context.model_routing
(llm_task_kind=lint_fix, ruff_codes list). Current Planfile drops unknown input fields;
legacy direct caller inputs remain accepted. Files and labels stay top-level.
