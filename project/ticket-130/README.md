# Ticket 130: Consume Goal governance proposals through Planfile

- **ID**: ticket-130
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-14

## Goal and scope

Consume Goal's strict `planfile.ticket-proposal.v1` governance remediation
artifact through an explicit Koru CLI boundary. Validate the target-owned
proposal, create one deduplicated Planfile ticket, assign it to the automatic
LLM queue lane and preserve the proposal as local runtime evidence.

## Acceptance criteria

- [x] AC-01: Koru accepts only a valid strict `TicketProposalV1` artifact
  located inside the target project.
- [x] AC-02: Koru creates or reuses one Planfile ticket using the proposal's
  safe fields, with `executor.kind=llm`, automatic mode and one attempt.
- [x] AC-03: Invalid, out-of-root or execution-authority-bearing payloads are
  rejected without a ticket write.
- [x] AC-04: Focused tests, Ruff, the managed governance check, stack checks
  and Docker Compose validation pass.

## Authorization

`SESSION_EXECUTION_AUTHORIZATION`: the user explicitly requested autonomous
implementation and testing of Goal-to-Planfile-to-Koru remediation.

## Validation evidence

Feature and CLI suite: 76 passed, 53 subtests passed. The full Koru suite
reached 4087 passed, 9 skipped, 165 deselected and 6 failures; after the new
dispatcher contract was updated, the remaining five failures are unrelated
existing socket, metadata and provider cases. Ruff,
`./project/governance-check.sh`, Docker Compose configuration, compileall and
`git diff --check` pass. Cross-repository integration created a real Planfile
ticket with `executor.kind=llm`, automatic mode and a stable dedupe key.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
