# Ticket 002: Adopt immutable new-project 0.11.0

- **ID**: ticket-002
- **Owner**: unresolved:human
- **Status**: PLAN
- **Workflow state**: WAIT_FOR_APPROVAL
- **Created**: 2026-08-05
- **Workstream**: governance

## Goal and scope

Bootstrap Koru as a full adopter of the immutable new-project 0.11.0 release
at `cc9b04673bbd85cb4e35fb683d288ef34be1485f`, using Goal's local governance
adapter. Preserve Koru's existing root files, generated `project/README.md`,
Python/Docker runtime and completed ticket-001.

This ticket installs governance and the canonical classification DSL only.
Replacing Koru's `critical/high/normal/low` mutation strategy is a subsequent
application ticket.

## Acceptance criteria

- [ ] AC-01: The human approves the bootstrap scope and exact release SHA.
- [ ] AC-02: A repository-specific 0.11.0 manifest owns Koru's Python, Docker,
  application, integration and governance paths without taking over generated
  `project/README.md`.
- [ ] AC-03: Goal's check plan matches the reviewed managed package and its
  application creates no files outside intent scope.
- [ ] AC-04: The lock records published 0.11.0 provenance and manages both
  work-classification files.
- [ ] AC-05: Governance, focused Koru tests and Docker validation pass.

## Participants

- Human participant: unresolved; no `user-*` file was created.
- Agent participant: [ai-codex.md](ai-codex.md).

## Risks

- Initial adoption is an atomic governance bootstrap with 19 planned managed
  artifacts; runtime code, dependencies and generated analysis stay untouched.
- Koru's existing priority behavior remains unchanged until a later approved
  application ticket.
