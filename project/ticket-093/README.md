# Ticket 093: Accurate quality gate results

- **Status**: IN_PROGRESS
- **Workflow state**: PUBLICATION
- **Owner**: codex

## Goal and scope

Diagnose the c2004 absolute-versus-delta Regix discrepancy and correct false-success reporting in the shared Koru quality gate runner. Preserve the selected quality policy.

## Acceptance criteria

- [x] AC-01: Missing tools, execution errors and unknown gates fail overall and obey fail_fast.
- [x] AC-02: Reports include executed argv; absolute Regix gates remain unchanged and explicit TestQL no-scenario skips remain supported.
- [x] AC-03: Regression tests, managed governance and stack checks pass before protected publication.

Validation: 7 failing regressions reproduced before the fix; 25 focused tests pass (16 deselected by repository configuration). Ruff, Compose and managed governance pass. Regix absolute policy is unchanged.
