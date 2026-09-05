# Ticket 081: Migrate legacy skipped queue tickets through planfile

- **ID**: ticket-081
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: PUBLICATION
- **Created**: 2026-09-05

## Goal and scope

Publish the existing queue migration code and tests from the user primary
checkout as a bounded application change. Preserve every local queue snapshot.

## Acceptance criteria

- [x] AC-01: Dry-run reports legacy skipped records without writing; apply uses planfile and reports failures.
- [x] AC-02: Existing queue cleanup and CLI behavior remain tested.
- [ ] AC-03: Managed governance and relevant stack checks pass before protected publication through Goal.
