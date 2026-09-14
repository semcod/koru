# Ticket 132: Execute a GitHub issue through Koru and Planfile

- **ID**: ticket-132
- **Owner**: codex
- **Status**: IN_PROGRESS
- **Workflow state**: PUBLICATION
- **Created**: 2026-09-14

## Goal and scope

`SESSION_EXECUTION_AUTHORIZATION`: user requested implementation, testing, repair and protected publication of `koru ticket <GitHub issue URL>`. C2004 explicitly retains main-only delivery; governed repositories use Wellmanifest v5 and independent OneDev/Validator approval.

## Acceptance criteria

- [x] AC-01: Resolve exactly one issue and its configured repository; preserve existing issue linkage and keep remote text outside authority fields.
- [x] AC-02: Select canonical worktree or main-only execution, run scoped Koru work and tests, and preserve recovery data.
- [ ] AC-03: Publish through the declared repository route and report the verified result through Planfile without duplicate comments or repeated execution.

## Tracking boundary

The user explicitly released src/koru/cli.py after the requested five-minute wait. Ticket-130 changes remain in its own checkout; this ticket adds a separate dispatcher entry and its matching command contract test. conflictsWith records the coordinated handoff. Preserve both commands when integrating the independently published branches.

## Verification and current publication boundary

109 focused tests and 54 dispatcher subtests passed with the native Planfile
comment API and the merged goal-remediation command. Eight queue/reporting tests
also passed after moving the clean-main preflight before GitHub authentication.
The existing C2004 fleet integration
suite passed 75 tests after installing the merged Planfile wheel.
Ruff, Compose and managed governance passed. A real Planfile delivery to C2004
issue 12 was repeated twice and produced exactly one comment; no executor ran.

The primary checkout queue prototype was preserved byte-for-byte in private
recovery before transfer to cli_ticket_queue.py. Explicit auto/list actions remain;
exact issue URLs use the scoped executor. Human approval is never synthesized,
backlog sync requires --sync, and dry-run cannot synchronize. The ticket-130
prerequisite was independently approved and merged as PR 168. Both dispatcher
entries are retained. Ticket-132 publication still requires exact-head OneDev
and Validator receipts.
