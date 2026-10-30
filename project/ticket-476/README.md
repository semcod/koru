# Ticket 476: Adopt published allocator for isolated quality-gate integration

- **ID**: ticket-476
- **Owner**: agent:codex
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-10-30

## Goal and scope

SESSION_EXECUTION_AUTHORIZATION: the operator requested continued quality-gate
integration and protected merges. The old allocator refuses a dirty primary,
preventing isolated source work. Adopt published new-project 0.20.119 through
its independently recomputed immutable allocation plan. Preserve the five
pre-existing primary edits and their digests; do not change application code.

## Acceptance criteria

- [ ] AC-01: Only exact published adoption payloads and native ticket carriers and the two declared packaging bindings change in the canonical checkout.
- [ ] AC-02: Existing primary edits, index and HEAD remain unchanged.
- [ ] AC-03: Native governance and protected checks pass before independent publication; subsequent source allocation uses the published allocator.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.

The published atomic adoption binding rule admits package.json and pyproject.toml
for the mechanical standard/revision refresh only. The bounded intent was
completed before changing those fields; application metadata stays untouched.
