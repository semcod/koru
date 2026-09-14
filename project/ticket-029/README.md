# Ticket 029: Implement leased issue execution and living status

- **ID**: ticket-029
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: PUBLICATION
- **Created**: 2026-09-01

## Goal and scope

`SESSION_EXECUTION_AUTHORIZATION`: continue the existing queue lease contract
with a one-hour Planfile lease, a ten-minute takeover grace period and an
idempotent handoff notice. Planfile remains the canonical ticket store and its
configured sync process remains the sole owner of GitHub, OneDev, Jira or
GitLab publication credentials.

After `takeoverAt`, autonomous hygiene emits one non-runnable Planfile ticket
that tells another agent where the handoff is eligible. The notice is never
write authority: the replacement must obtain the authoritative lease
controller's exact generation and fencing receipt before changing a worktree,
branch or commit. Legacy triage remains fail-closed after the same grace period.

## Acceptance criteria

- [x] AC-01: The active user explicitly requested implementation and
  deployment; session execution authorization applies.
- [x] AC-02: Queue claims default to 3600 seconds and remain bounded and
  configurable through `KORU_TICKET_LEASE_SECONDS`.
- [x] AC-03: A successful claim is followed by one marker-delimited Living
  Status update in Planfile containing ticket, actor, state and lease expiry.
- [x] AC-04: Repeated updates replace the same marker block without duplicating
  the source description.
- [x] AC-05: A leased in-progress ticket reaches takeover eligibility only
  after its 3600-second lease plus 600-second grace period; legacy tickets
  without lease metadata retain the configured stale cutoff.
- [x] AC-06: Planfile owns remote synchronization; Koru neither calls GitHub
  Issues directly nor requires a GitHub credential in the worker.
- [x] AC-07: Focused tests, Ruff, governance and Docker checks pass before
  protected OneDev/Validator publication.
- [x] AC-08: Each eligible target emits one deduplicated non-runnable handoff
  ticket, and a renewed lease resolves the notice without granting takeover.

The owner re-authorized this bounded continuation on 2026-09-14. Existing
ticket-029 source work is preserved; the new behavior is limited to the
declared queue hygiene and ticket-construction paths.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
