# Ticket Changelog (ticket-025)

## [0.1.0] - 2026-09-01

- Created the canonical replacement for a concurrently colliding local ticket
  allocation; no human participant identity or content was generated.
- Recorded the observed historical clone pattern and bounded an
  evidence-sensitive history dedupe design.
- Kept Planfile mutation and the ticket-022 work lifecycle out of scope.

## [0.2.0] - 2026-09-01

- Recorded the protected ticket-024 closure, refreshed the accepted main base
  and removed the temporary conflict binding.
- Bound the user's continuation approval to the unchanged reticketed plan and
  entered `IN_PROGRESS / EDIT` before transferring implementation changes.

## [0.3.0] - 2026-09-01

- Added producer- and evidence-bound dedupe across direct and indexed Planfile
  history without mutating archived tickets.
- Preserved active-ticket compatibility and allowed changed evidence to create
  a new regression ticket.
- Added focused policy and end-to-end apply coverage and advanced the ticket to
  publication after all declared local gates passed.

## [0.4.0] - 2026-09-01

- Recorded exact-head smoke, OneDev and protected Validator evidence for PR
  #55 and its merge commit.
- Closed the ticket lifecycle as `DONE / DONE` without changing runtime code,
  tests or publication policy.
