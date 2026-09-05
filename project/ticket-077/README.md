# Ticket 077: Restore clean test lint checks

- **ID**: ticket-077
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: PUBLICATION
- **Created**: 2026-09-05

## Goal and scope

Correct the two confirmed Ruff findings in existing autonomous and CI tests.
Publish the correction on GitHub through the protected delivery process.

## Acceptance criteria

- [x] AC-01: Fix UP037 and I001 without changing tested behavior.
- [x] AC-02: Ruff, focused pytest, governance and Docker Compose validation pass.
- [ ] AC-03: Publish the exact verified HEAD through trusted GitHub delivery.
