# Ticket 135: Support wildcard issue URLs and Planfile synchronization in ticket command

- **ID**: ticket-135
- **Owner**: codex
- **Status**: IN_PROGRESS
- **Workflow state**: PUBLICATION
- **Created**: 2026-09-14

## Goal and scope

`SESSION_EXECUTION_AUTHORIZATION`: Support wildcard GitHub issue URLs such as `https://github.com/maskservice/c2004/issues/*` when running `koru ticket`, ensuring seamless sequential batch execution and bidirectional Planfile synchronization with GitHub issues for configured repositories.

## Acceptance criteria

- [x] AC-01: Support wildcard GitHub issue URLs (matching `issues/*` and `issues*`) alongside existing `issues` and `issues/` URLs.
- [x] AC-02: Trigger bidirectional Planfile synchronization (`planfile.cli sync github --direction both`) on the target repository when configured.
- [x] AC-03: Pass focused test suites and isolate environment in IDE doctor test.

## Tracking boundary

Deliverables are limited to application ticket commands and tests. Remote issue text and private tokens remain excluded from tracking.

## Verification and publication

70 focused ticket command tests passed including batch execution, wildcard URL routing and Planfile sync tests. 11 IDE doctor tests passed with proper HOME/XDG environment isolation. A live dry-run of `koru ticket https://github.com/maskservice/c2004/issues/*` successfully resolved open issues 7, 12, 16, 17, and 18 in order. Ruff lint and wellmanifest governance check passed.
