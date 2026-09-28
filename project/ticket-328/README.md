# Ticket 328: Autonomy trace report queue admission instead of false stuck waiting input

- **ID**: ticket-328
- **Owner**: agent:koru
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-28

## Goal and scope

1. Correct decision trace telemetry when queue admission is denied (e.g. missing duplication contract, unsupported executor, or infrastructure error):
   - Add `queue_admission` to `SKIP_CODE_DESCRIPTIONS` and `_TELEMETRY_SKIP_FLAGS`.
   - Surface exact admission reasons in `_skip_because_for_code`.
   - Prevent `stuck_waiting_input` from falsely masking `queue_admission` on repeated cycles.
   - Suppress `[auto llm-ready]` promotion hint in operator quick actions when queue admission is blocked.
2. Accelerate standard fleet git observation by directly inspecting `.git` filesystem descriptors, reducing unnecessary git subprocess invocations.

## Acceptance criteria

- [x] AC-01: Decision trace correctly classifies `queue_admission`, surfaces reason, avoids false `stuck_waiting_input`, and suppresses `[auto llm-ready]`.
- [x] AC-02: Filesystem-accelerated git observation passes all fleet scan tests and eliminates redundant subprocess calls.
- [x] AC-03: Governance check and all tests pass cleanly.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
