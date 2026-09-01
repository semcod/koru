---
participant-id: agent:codex
participant: codex
role: agent
ticket: ticket-023
---
# Participant: codex (AI agent)

## Understanding

Koru needs a deterministic planning boundary that standardizes POA and
Wellmanifest Logs without turning configuration discovery into implicit
execution authority. The dynamic registry is therefore a pure snapshot built
from actual `subactor.config-response/v1` Registry and Strategy responses. A
Policy decision is verified independently against the exact planning input.
All external contract bytes and every accepted response are hash-pinned.

## Execution plan

1. Vendor and pin the upstream POA process schema and Logs v0.3 contract, plus
   a closed Koru source-registry schema.
2. Implement canonical validation, dynamic Config evidence resolution and
   separately bound Policy verification.
3. Compile an inert POA plan and project it into hash-linked Logs events.
4. Test malformed, drifted, ambiguous, unbound and happy-path behavior.
5. Run governance, stack and Docker checks, then publish a stacked GitHub PR
   through the local OneDev verification boundary.

## Actual changes

- Added the bounded ticket plan and transitioned to `EDIT` after explicit
  session approval.
- Added the vendored POA, Koru source-registry and Wellmanifest Logs contracts.
- Added the pure `koru.poa` validation, planning and event modules.
- Added focused contract, registry/policy and Logs event-chain tests.
- Verified 22 focused tests, Ruff, mypy, governance, Docker configuration,
  contract pins and wheel contents; recorded unrelated full-suite baseline
  failures without editing their paths.

## Blockers

- Trusted validator publication still requires the protected Validator App
  signer, which is unavailable in this checkout; no repository-authored
  substitute will be treated as approval.
