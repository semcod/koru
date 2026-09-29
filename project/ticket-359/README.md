# Ticket 359: add plugins scope to application workstream

- **ID**: ticket-359
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-29

## Goal and scope

SESSION_EXECUTION_AUTHORIZATION: user asked to continue Koru autopilot
repair ("kontynuuj"). Durable fix for the windsurf autopilot plugin host
gate (accept Devin Desktop) requires owning `plugins/**`, which no
workstream currently covers. Add `plugins/**` to the `application`
workstream's `ownedPaths` so plugin source fixes can be allocated.

## Acceptance criteria

- [ ] AC-01: Scope validator accepts plugins/** paths for application tickets.
- [ ] AC-02: governance-check.sh passes.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
