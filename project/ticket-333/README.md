# Ticket 333: Prevent shell-agent source corruption

- **ID**: ticket-333
- **Owner**: agent:codex
- **Status**: IN_PROGRESS
- **Workflow state**: PUBLICATION
- **Created**: 2026-09-28

## Goal and scope

SESSION_EXECUTION_AUTHORIZATION: user requests continued testing and repair of Koru regressions in files and contents (2026-09-28). The stopped PLF031 lane overwrote context.py with a Planfile shell command. Prevent unadmitted direct mutation and honor preview before fallback. Protected publication is included in the continuing delivery authorization.

## Acceptance criteria

- [x] AC-01: A local corrupting executor cannot run against primary, dirty or governed targets, including nested paths and symlinks; original content and index are unchanged. Clean isolated unmanaged linked checkouts still execute.
- [x] AC-02: submit=False and execute=False never launch editing, model policy or editor rescue; admission rejection never invokes GUI fallback. Focused tests and managed gate pass.

## Limits

This is an execution admission barrier, not a process sandbox or semantic validation of edits. Governed execution remains unavailable until the independent controller adapter exists. The production lane stays stopped pending verified immutable rollout and canary.

## Validation

131 focused tests passed, including real Git fixtures, malicious local executor, preview and fallback regressions. Scoped source/test Ruff and managed governance gate passed. Full-tree Ruff is blocked by the pre-existing I001 in src/koru/queue/loop.py:68, owned by ticket331 / PR573; integrated CI must confirm its resolution. Reproduction against base 44fd805b invokes the corrupting executor and loses source; repaired bridge refuses before invocation and preserves it. No paid model or production editing used in the reproduction.
