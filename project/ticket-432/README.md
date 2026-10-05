# Ticket 432: Preserve autonomous diagnostics after launch and timeout failures

- **ID**: ticket-432
- **Owner**: codex
- **Status**: IN_PROGRESS
- **Workflow state**: PUBLICATION
- **Created**: 2026-10-05

SESSION_EXECUTION_AUTHORIZATION: continue diagnosis, tests, repairs and protected publication. PLF-2671 / GitHub #679 is this bounded implementation; parent #672 stays open for real independently admitted OpenCode execution.

## Acceptance criteria

- [x] AC-01: Failed launch and timeout are observed as failed checks, create the existing durable local diagnostic ticket, and permit the following healthy check to execute.
- [x] AC-02: Each command has a finite runtime budget; success/nonzero behavior and marker dedup remain intact; diagnostics do not expose raw exception content.
- [ ] AC-03: Focused and relevant broader tests, Ruff, Compose, managed gate, independent protected publication and installed readback pass.

Validation: all seven new regressions failed against the accepted base; focused bundle 19 passed, relevant broader diagnostic/intake/cycle bundle 46 passed. Independent audit bundle on base: 116 passed / 56 subtests passed. Ruff and Compose configuration passed. Runtime budget is five minutes per diagnostic check; tests use a short controlled limit with actual subprocesses. Independent protected publication and installed readback remain pending; ticket stays IN_PROGRESS / PUBLICATION.
