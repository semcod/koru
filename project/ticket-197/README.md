# Ticket 197: Reduce cyclomatic complexity in supervise_once

- **ID**: ticket-197
- **Owner**: antigravity
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-25

## Goal and scope

Reduce the cyclomatic complexity of `src.koruapi.opencode_supervisor.supervise_once`
from CC=37 to <= 15 (STARTER-738 / PLF-005 / issue #388).

Extract focused helper functions for session pruning, target resolution, failover
steering, permission replying, question replying, and single-instance supervision.
Preserve exact semantics, error handling, and log messages.

## Acceptance criteria

- [x] AC-01: Scope is approved by a human owner.
- [x] AC-02: `supervise_once` cyclomatic complexity drops from 37 to <= 15 with all helpers <= 15.
- [x] AC-03: Existing unit and regression tests pass without changes.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
