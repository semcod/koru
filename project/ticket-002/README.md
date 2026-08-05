# Ticket 002: Adopt immutable new-project 0.11.0

- **ID**: ticket-002
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: VALIDATION
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

- [x] AC-01: The human approves the bootstrap scope, exact release SHA and
  narrow migration amendment.
- [x] AC-02: A repository-specific 0.11.0 manifest owns Koru's Python, Docker,
  application, integration and governance paths without taking over generated
  `project/README.md`.
- [x] AC-03: Goal's check plan matches the reviewed managed package and its
  application creates no files outside intent scope.
- [x] AC-04: The lock records published 0.11.0 provenance and manages both
  work-classification files.
- [x] AC-05: Governance, focused Koru tests and Docker validation pass.

## Participants

- Human participant: unresolved; no `user-*` file was created.
- Agent participant: [ai-codex.md](ai-codex.md).

## Risks

- Initial adoption is an atomic governance bootstrap with 19 planned managed
  artifacts; runtime code, dependencies and generated analysis stay untouched.
- Koru's existing priority behavior remains unchanged until a later approved
  application ticket.
- Hosted smoke currently fails on 36 pre-existing Ruff findings under
  `src/koru`; the same workflow already fails on unchanged `main@5943447d`.
  Ticket-002 neither hides nor repairs this unrelated SERVICE debt.

## Session authorization

The user approved ticket-002 with the instruction to continue on 2026-08-05.
This authorizes the declared bootstrap, not protected merge approval.

## Required migration amendment

The first 0.11.0 gate exposed legacy state that check-only adoption cannot
discover. Completion requires a fresh, narrow approval to:

1. normalize only the metadata spelling in `project/ticket-001/README.md` from
   legacy `- Status: DONE` to canonical `- **Status**: DONE`, preserving its
   meaning and content;
2. align the ticket and target delivery budgets with the already reviewed
   atomic 19-file bootstrap;
3. assign `project/governance-check.*` to Koru's governance workstream and map
   every managed bootstrap target to the existing managed-package component;
4. mark the adoption correctly as no component-responsibility or persistent
   application-data movement.

No runtime, test, dependency, generated-analysis or Docker file enters scope.
The user approved the amendment and autonomous continuation on 2026-08-05, so
the ticket returned to `IN_PROGRESS / EDIT` and completed local validation.

## Validation evidence

- Goal adoption check: up to date at immutable new-project 0.11.0 SHA
  `cc9b04673bbd85cb4e35fb683d288ef34be1485f`.
- Governance gate: PASS with zero errors and warnings.
- Ruff: PASS.
- Focused Koru suite: 105 passed.
- Docker Compose configuration and `git diff --check`: PASS.
