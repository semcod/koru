# Ticket 075: Route standard-update remediation

- **ID**: ticket-075
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: PUBLICATION
- **Created**: 2026-09-02

## Goal and scope

Route the target-published `GOV-STANDARD-UPDATE-001` diagnostic through Koru's
existing one-agent, one-retry supervisor. The handoff must preserve the
interrupted implementation ticket and prepare the adoption in a distinct
governance ticket/worktree without weakening the fail-closed commit boundary.

## Acceptance criteria

- [x] AC-01: `GOV-STANDARD-UPDATE-001` is allowlisted only when resolved from
  the target-owned diagnostic catalog.
- [x] AC-02: The remediation handoff requires a separate governance adoption
  ticket and keeps the interrupted commit blocked until integration.
- [x] AC-03: Focused tests, Ruff, governance and repository stack gates pass.

## Authorization

`SESSION_EXECUTION_AUTHORIZATION`: the user explicitly requested continued
implementation, testing and deployment of automatic Wellmanifest updates and
repairs to Koru and Goal.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
