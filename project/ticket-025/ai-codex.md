---
participant-id: agent:codex
participant: codex
role: agent
ticket: ticket-025
---
# Participant: codex (AI agent)

## Understanding

The umbrella Planfile contains 59 terminal tickets but no output or sync
evidence, including six copies of several identical scan findings. Koru's
current policy intentionally ignores terminal tickets and only lists current
sprint entries, so each archive/apply cycle can recreate the same unchanged
signal. A permanent title ban would hide real regressions; terminal history
must therefore suppress only an identical evidence-bound finding.

The original local ID collided with concurrently published PR #53. Ticket 025
is the canonically allocated replacement on refreshed main; its implementation
scope and architecture are unchanged.

## Execution plan

1. Add a read-only current/history ticket index limited to the requested scan
   producer and structurally valid source context.
2. Compare stable dedupe keys and evidence fingerprints, retaining the current
   title/signal fallback only for active legacy tickets.
3. Cover indexed history, direct history files, malformed entries, unrelated
   producers and changed-evidence regressions.
4. Run focused tests, Ruff, governance and Docker checks, then publish the
   exact head through OneDev and Validator boundaries.

## Actual changes

- The plan is complete and no implementation file has changed on this branch.
- Activation is serialized behind the ticket-024 closure because the two plan
  diffs share `TODO.md` and `project/TICKETS.md`, despite distinct runtime
  workstreams.

## Blockers

- The unchanged scope was approved under the collided local allocation; an
  explicit continuation after this reticket will be recorded before entering
  `EDIT`.
