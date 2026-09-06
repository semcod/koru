# Ticket 092: Fail closed in bootstrap verification

- **Status**: IN_PROGRESS
- **Workflow state**: PUBLICATION
- **Owner**: codex

SESSION_EXECUTION_AUTHORIZATION: user requested autonomous continuation, implementation, testing and protected publication. Fix the false-success verification boundary before attempting unattended refactoring. This does not grant the runtime broader mutation or publication permissions.

## Acceptance criteria

- [x] AC-01: Missing test tools and failing selected tests return nonzero; a failure cannot fall back to a different passing runner.
- [x] AC-02: Optional stages that execute propagate failure. Successful verification still passes, and existing user policy remains unchanged.
- [x] AC-03: Regression tests, managed gate and stack checks pass before protected publication.

Validation: 43 bootstrap tests pass; extended bootstrap and OneDev queue/MCP profile suite passes 153 tests with 16 deselected by repository configuration. Ruff, managed governance, Compose and whitespace checks pass. Existing user policies are preserved and must be migrated through their own accepted scope.
