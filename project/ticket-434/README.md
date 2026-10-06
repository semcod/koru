# Ticket 434: Reject commandless shell completion

- **ID**: ticket-434
- **Owner**: agent:codex / codex-koru434-oct6
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-10-06

SESSION_EXECUTION_AUTHORIZATION: user requested continued fixes, tests, deployment and protected publication.

## Goal and scope

Reject missing/blank/invalid shell actions before any claim or execution. Publish the complete resulting queue runtime through independent exact-head review; preserve older runtimes and admission bindings. No historical approval is invented for PR #698.

## Acceptance criteria

- AC-01: Regression proves a successful no-op cannot close a commandless shell ticket; declared valid commands, LLM answer/edit contracts and patch evidence still pass.
- AC-02: Governance, Ruff, protected OneDev, independent current-head approval/merge and installed-runtime canary; bounded fleet activation with verified rollback and no live claim interruption.
