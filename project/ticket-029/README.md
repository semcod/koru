# Ticket 029: Implement leased issue execution and living status

- **ID**: ticket-029
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: VALIDATION
- **Created**: 2026-09-01

## Goal and scope

Complete Koru's low-risk queue contract with a two-hour Planfile lease and a
single, idempotently replaced Living Status projection. Planfile remains the
canonical ticket store and its configured sync process remains the sole owner
of GitHub, OneDev, Jira or GitLab publication credentials.

After the lease expires, autonomous hygiene must stop recycling the ticket as
ordinary open work. It moves the ticket to `blocked`, projects
`waiting_human_triage` and `sla:urgent`, and leaves a deterministic recovery
note for Subactor `/tickets` and `/watch` consumers.

## Acceptance criteria

- [x] AC-01: The active user explicitly requested implementation and
  deployment; session execution authorization applies.
- [x] AC-02: Queue claims default to 7200 seconds and remain bounded and
  configurable through `KORU_TICKET_LEASE_SECONDS`.
- [x] AC-03: A successful claim is followed by one marker-delimited Living
  Status update in Planfile containing ticket, actor, state and lease expiry.
- [x] AC-04: Repeated updates replace the same marker block without duplicating
  the source description.
- [x] AC-05: An expired in-progress ticket becomes blocked with
  `waiting_human_triage` and `sla:urgent` in its status projection; a legacy
  ticket without lease metadata uses the same two-hour cutoff.
- [x] AC-06: Planfile owns remote synchronization; Koru neither calls GitHub
  Issues directly nor requires a GitHub credential in the worker.
- [x] AC-07: Focused tests, Ruff, governance and Docker checks pass before
  protected OneDev/Validator publication.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
