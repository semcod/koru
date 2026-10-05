# Ticket 430: Reject incompatible queue transport for explicit shell providers

- **ID**: ticket-430
- **Owner**: codex
- **Status**: IN_PROGRESS
- **Workflow state**: PUBLICATION
- **Created**: 2026-10-05

SESSION_EXECUTION_AUTHORIZATION: user requests continuation, repairs, tests and protected merges. PLF-2667 / GitHub673 is the bounded child of PLF-2666 / GitHub672 and willmux#17.

## Acceptance criteria

- [x] AC-01: SDK provider survives request translation; explicit OpenCode/vendor shell requests are denied before claims or model calls, with stable diagnostic and no fallback even under conflicting environment.
- [x] AC-02: Direct runner cannot bypass refusal; legacy and non-shell tickets retain the central SubLLM route.
- [ ] AC-03: Managed gate, focused regressions, actual local CI and independent exact-head protected publication succeed.

The remaining protected admission adapter, real OpenCode canary and willmux intake stay tracked by the parent issues.

## Bounded delivery prerequisite

The full Ruff gate also fails on existing main at tests/test_agent_backend_runtime.py:192 (E501). Its distinct Planfile/GitHub issue is bound in the external checkpoint. Extend this same implementation only to format that test call, without suppression or behavior change, then run its existing tests and full Ruff.

## Validation

- Regression before fix: 19 failed, 4 passed; after fix: all 23 passed.
- Queue, admission, runner and Tillm regression bundle: 194 passed and 12 subtests passed.
- Backend and provider bundle: 45 passed, including 22 existing backend tests.
- Full src/koru and tests Ruff, root Docker Compose configuration and managed governance: passed.

Independent exact-head OneDev/Validator publication and installed readback remain required; parent #672 stays open for real admitted OpenCode execution.
