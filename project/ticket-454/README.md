# Ticket 454: fix(queue): mount ephemeral .subactor/cache inside verification sandbox

- **ID**: ticket-454
- **Owner**: antigravity
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-10-18

SESSION_EXECUTION_AUTHORIZATION: user requests autonomous execution to allow verification scripts that create scratch files under `.subactor/cache` to succeed inside the isolated bubblewrap sandbox without modifying the host checkout.

## Goal and scope

1. In `src/koru/queue/verification_sandbox.py` (`_command`), create `subactor-cache/koru-verification/<scratch.name>` inside `scratch` and bind-mount `subactor-cache` at `project / ".subactor/cache"` before binding `scratch`.
2. Add regression coverage in `tests/test_queue_verification_sandbox.py`.

## Acceptance criteria

- [x] AC-01: Verification processes can write temporary files inside `.subactor/cache` without `Read-only file system` errors, and no files written there persist on the host checkout after verification finishes.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
