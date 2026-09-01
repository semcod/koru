---
participant-id: agent:codex
participant: codex
role: agent
ticket: ticket-026
---
# Participant: codex (AI agent)

## Understanding

The user asked to finish and correctly merge outstanding branches and issues.
PR #43 was not mergeable: it conflicted with main, failed smoke and OneDev,
changed dozens of files under ticket 021 after that ticket closed for another
delivery, and was therefore closed as superseded. Issue #41 remains valid and
blocks issue #37 because current standard 0.11.0 does not own `packages/**`.

The first replacement plan was serialized locally as ticket 025, validated and
approved for continuation. Before implementation, a concurrent protected PR
merged a different ticket 025 first. The winning merge receipt is authoritative,
so this equivalent plan has been preserved as ticket 026 on refreshed main; no
implementation content from the losing allocation was mixed into the winner.

The latest final upstream release is 0.19.18 at immutable revision
`7dd68589340bfd4b18b94f3141f41833280c2985`. Its changelog includes the 0.19.3
monorepo ownership fix and later atomic-adoption, worktree and ticket-activity
repairs. A read-only Goal preflight identifies 75 managed operations. Koru's
broad local ignores require four exact negations first.

## Execution plan

1. Wait for explicit approval of the successor ID in
   `PLAN / WAIT_FOR_APPROVAL`.
2. Move to `IN_PROGRESS / EDIT` and add only the four exact `.gitignore`
   trackability exceptions declared by the ticket.
3. Run Goal 2.1.300 with `governance adopt --upgrade` against the exact
   published revision; do not hand-edit generated governance files.
4. Reconcile the ticket intent mechanically with the adopted schema without
   widening product scope, then verify repeated adoption reports zero drift.
5. Validate package ownership, closed-ticket activity, ticket allocation,
   governance, focused Python smoke, diff hygiene and Docker configuration.
6. Publish a replacement PR bound to issue #41 and request protected
   exact-head review and merge. After delivery close #41 and proceed to a
   separate application ticket for #37.

## Actual changes

- None; waiting for approval.

## Blockers

- Human approval is required before implementation.
