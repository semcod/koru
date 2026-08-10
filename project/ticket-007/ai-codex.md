---
participant-id: agent:codex
participant: codex
role: agent
ticket: ticket-007
---
# Participant: codex (AI agent)

## Understanding

The public 0.1.459 wheel proved that source-checkout tests can pass while the
installed CLI fails because development dependencies hide incomplete runtime
metadata. The test must execute the built distribution outside the project
environment.

## Execution plan

1. Build a wheel with the existing uv distribution path.
2. Remove the inherited virtualenv hint and run the wheel via isolated uv.
3. Compare CLI output with the canonical pyproject version.
4. Run governance, hosted smoke and exact-head validation.

## Actual changes

- Added a bounded installed-wheel CLI regression test.

## Blockers

- None; the user explicitly authorized autonomous execution.
