# Ticket 300: Decompose ticket-response parsing to clear god-function smell in context

- **ID**: ticket-300
- **Owner**: claude
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-27

## Session authority

SESSION_EXECUTION_AUTHORIZATION: the operator handed this lane over with an
explicit request to work planfile ticket PLF-031 (high priority, current
sprint): code2llm reports `God Function: build_context` at
`src/koru/context.py:462` (CC=9, fan-out=20, mutations=23) — make the
smallest refactor that removes the smell and run local tests.

## Why

## Why

code2llm reports `God Function: build_context` at `src/koru/context.py:462`
(CC=9, fan-out=20, mutations=23). The evidence snapshot (file sha256
`7edaabf6…`, revision `ebbcd55f`) predates two merged decompositions:

- `120509a0` (ticket-213) shrank `build_context` itself — at HEAD it is
  CC=4 / mutations=6, under every god threshold.
- `84318d61` (ticket-244) split the surrounding module.

But ticket-213's extraction moved the reported 23-mutation block verbatim
into the new helper `_parse_ticket_response` (now lines 423–467, containing
the cited line 462), which code2llm still flags today: CC=10, fan-out=10,
mutations=23 (god threshold: fan-out > 10 or mutations > 6 or CC > 12).
The smell is live at the cited location under the helper's name.

## What changes

- `_process_list_payload` / `_process_dict_payload` return the existing
  `_TicketFetch` NamedTuple instead of bare tuples (tuple-unpack targets
  are double-counted by the mutation metric — 10 of the 23 records).
- `_parse_ticket_response` returns `_TicketFetch` with one direct return
  per response shape instead of mutating four accumulator locals; the
  idle-output probe moves to a new `_is_idle_planfile_output` predicate.
- `_fetch_ticket_data` (sole caller) drops its `*_parse_ticket_response(…)`
  re-pack.

Behavior-preserving: same outputs for idle/banner/JSON-null outputs,
list payloads, dict payloads (incl. fixture rejection and the follow-up
`ticket list` history fetch), stderr errors, and the scalar-JSON
fall-through (pinned by a new test).

Out of scope: `_process_list_payload` keeps its pre-existing mutations=8
(a separate unreported dedupe key at :339) — this lane only clears the
cited smell lineage.

## Evidence

See `intent.json` → `delivery.validation`.
