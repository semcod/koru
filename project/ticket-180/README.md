# Ticket 180: Model history dashboard and safe logs

- **ID**: ticket-180
- **Owner**: codex
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-19

SESSION_EXECUTION_AUTHORIZATION: user says popraw; STARTER-734.
Dependent UI/parser slice split from ticket179 to respect delivery budgets.
Own only the four UI/test files; source routing/history belongs to ticket179.

## Acceptance criteria

- [x] AC-01: Log parsing cannot execute expressions; existing dashboard tests pass.
- [x] AC-02: Models view shows actual metadata, unknown/missing states, project and
  application scope, and keeps requested models separate; browser acceptance passes.

Owner session codex-koru-ui180-20260919; maxActiveMinutes:120.
Publication uses protected local CI and independent Validator.

Validation: 98 dashboard tests passed, Ruff and diff checks passed. Browser readback
shows the exact Flash canary session, working model filter/empty result and HTTP503
state, with no JavaScript errors. Preview on loopback port8771, not deployed service.

User continuation 2026-09-19: improve Models table appearance and timestamp visibility;
fix the reported /favicon.ico 404. Same UI scope: full-width table, clear UTC time/date,
responsive scrolling and semantic status badges. Validate live preview on port8771.

Follow-up validation: 98 tests passed. Chromium at 1440px and 390px confirmed
full-width table, UTC conversion with milliseconds, preserved filter focus after
refresh, contained horizontal scrolling, and no JavaScript/HTTP resource errors.
Both favicon paths return HTTP200 image/svg+xml.
