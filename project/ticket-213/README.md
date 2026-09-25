# Ticket 213: Decompose god function build context

- **ID**: ticket-213
- **Owner**: claude
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-25

## Goal and scope

Address code smell: `God Function: build_context` in
`src/koru/context.py:462` (PLF-031, CC=9, fan-out=20, mutations=23).

Extract three cohesive phases: the planfile pre-flight into
`_planfile_is_initialised`, the fetch / compatibility-repair /
fixture-filter chain into `_collect_ticket_state` returning a
`_TicketState` NamedTuple, and the final brief assembly into
`_assemble_context`. Make `_fetch_ticket_data` return a `_TicketFetch`
NamedTuple (star-adapting `_parse_ticket_response`'s unchanged tuple) so
the decomposed body contains no tuple unpacking. Preserve the public
keyword-only `build_context` signature, output shape and side-effect
order.

## Acceptance criteria

- [x] AC-01: Scope is approved by a human owner (planfile PLF-031 queue handoff).
- [x] AC-02: `build_context` metrics fall under the god-function thresholds (CC <= 12, fan-out <= 10, mutations <= 6); every new helper stays under too.
- [x] AC-03: `pytest -q tests/test_context.py tests/test_koruapi.py tests/test_serve.py` passes unchanged.
- [x] AC-04: code2llm analysis of the changed file reports no function crossing a god-function threshold that did not already cross one before this change.
- [x] AC-05: `bash project/governance-check.sh` passes with 0 errors.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
