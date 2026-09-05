# Ticket 079: Extract photo VQL drive result normalization

- **ID**: ticket-079
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-05

## Goal and scope

Extract result shaping and its ordered gates from vdisplay_client into a focused
module. Keep the facade entry point and resolve policy callbacks at call time.

## Acceptance criteria

- [ ] AC-01: Normalization lives in a focused module with no reverse facade import.
- [ ] AC-02: Contract tests pass before and after extraction; existing photo-VQL tests and managed gates pass.
- [ ] AC-03: Publish the verified HEAD through trusted GitHub delivery.
