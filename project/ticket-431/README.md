# Ticket 431: Refuse governed direct patch application without protected admission

- **ID**: ticket-431
- **Owner**: codex
- **Status**: IN_PROGRESS
- **Workflow state**: PUBLICATION
- **Created**: 2026-10-05

SESSION_EXECUTION_AUTHORIZATION: user requests continuation, repairs, tests and protected merges. Planfile PLF-2669 / GitHub #676 is the bounded child of PLF-2666 / #672.

## Acceptance criteria

- [x] AC-01: Governed primary and linked patch execution is refused without protected admission, irrespective of local callbacks, local leases and isolation flags; source, commits and verification remain untouched.
- [x] AC-02: Recheck workspace admission at mutation after callbacks and unavailable staging; reject symlink and Git redirection while preserving artifact and unmanaged execution.
- [ ] AC-03: Focused regressions, managed gate, actual local CI and independent protected publication succeed.

Parent #672 remains open for an actual scope-enforced AdmissionClient-to-OpenCode adapter and live protected enrollment. This ticket grants no vendor execution authority.

## Validation

- Before source repair: 40 failed, 6 passed across 46 real Git regression cases.
- After repair: all 46 new regression cases passed.
- Transaction, workspace, Planfile queue, admission, runners and explicit shell provider bundle: 270 passed and 15 subtests passed.
- Full src/koru and tests Ruff, root Docker Compose configuration and managed governance: passed.

Actual OneDev verification, independent exact-head Validator publication and installed readback remain required. Parent #672 remains open.
