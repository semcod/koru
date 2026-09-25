# Ticket 212: Reduce god-function metrics in apply_patch_with_retry

- **ID**: ticket-212
- **Owner**: claude
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-25

## Goal and scope

Address code smell: God Function: `apply_patch_with_retry` in
`src/koru/queue/patch_retry.py:130` (PLF-030). The ticket-199 decomposition
(PLF-013) dropped CC 11→10, but the function still trips the god-function
thresholds: fan-out=13 (>10), mutations=18 (>6).

Carry the retry loop's mutable run state (budget, pinned base, attempt record)
in a small dedicated object with named policy steps, so the loop stops
rebinding a dozen locals per iteration. Preserve exact transaction execution,
budget clamping, drift detection, envelope wrapping and evidence recording
semantics, and keep the call-time imports that make the facade the single test
seam.

SESSION_EXECUTION_AUTHORIZATION: the PLF-030 planfile handoff instructs
autonomous execution (done/input/fail status commands included).

## Acceptance criteria

- [x] AC-01: Scope is approved by a human owner (planfile PLF-030 handoff).
- [ ] AC-02: `apply_patch_with_retry` and every helper it gains clear the
  god-function thresholds (fan-out <= 10, mutations <= 6, CC <= 12).
- [ ] AC-03: Existing unit and regression tests pass without changes.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
