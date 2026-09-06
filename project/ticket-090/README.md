# Ticket 090: Bound post-run verification

- **ID**: ticket-090
- **Owner**: tom
- **Status**: IN_PROGRESS
- **Workflow state**: PUBLICATION

## Goal and scope

Implement the command-validation portion of A1. The timeout interface follows in a dependent ticket after GOV-BUDGET-001 required splitting the combined change.

## Acceptance criteria

- [x] AC-01: Empty/blank/invalid commands never report verified or mutate lifecycle; valid commands run in order.
- [x] AC-02: Valid commands run in order, stop after first failure, and preserve injected runners and sanitized environment.
- [ ] AC-03: Focused tests, lint, governance and Docker checks pass and protected publication merges the change.
