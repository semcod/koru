# Ticket 481: Expectation audit: resolve indexed constant URI arrays

- **ID**: ticket-481
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-11-04

## Goal and scope

Make `koru.expectation_audit` resolve verifying URIs written as `NAME[index]` over a constant string array
(`const NAME = Object.freeze([...])`). In subactor founder-form.mjs four expectations use this form and were
reported as `S4-unresolved`; on the live data S4 findings go from 4 to 8 and unresolved from 5 to 1.
Follow-up to ticket-480 (merged). The operator asked for the audit to be extended; no verifier or producer changes.

## Acceptance criteria

- [x] AC-01: `NAME[i]` over a constant string array is resolved; an out-of-range index stays `S4-unresolved`.
- [x] AC-02: Existing audit tests, ruff and `./project/governance-check.sh` pass.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
