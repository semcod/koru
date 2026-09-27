# Ticket 325: Prepare protected publication approval ruleset migration

- **ID**: ticket-325
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-27
- **Intake**: PLF-064 (semcod/koru#545), operator queue, priority high

## Goal and scope

Prepare — without deploying — the ruleset 22026679 migration that requires one
trusted exact-head approving review and stops the ordinary author/operator
account from merging directly: tracked desired body, read-only readback/verify
gate, canary evidence schema and validator, fork-sandbox validation, tested
rollback mechanics and a documented remediation path for the already-merged
unapproved heads (PR542/543/550).

Deliverables:

- `.governance/publication-policy/ruleset.desired.json` — exact PUT-able
  desired body plus migration metadata (3 changes, preserved requirements,
  deployment and rollback commands, fork-sandbox variant).
- `.governance/publication-policy/ruleset_readback.py` — `readback` / `verify`
  / `canary` / `--self-test` gate (read-only against GitHub; fails closed).
- `.governance/publication-policy/fixtures/ruleset-observed-2026-09-27.json` —
  baseline live snapshot (the drift reference and content-addressed rollback
  source).
- `.governance/docs/RULESET_APPROVAL_MIGRATION.md` — incident evidence,
  admin-bypass assessment, canary report, deployment runbook, recovery.
- `project/ticket-325/evidence/ruleset-canary-fork-2026-09-27.json` —
  fork-sandbox canary records validated by the gate.

## Acceptance criteria

- [x] AC-01: self-test suite covers profile comparison, canary validation and
      fail-closed behavior over the baseline fixture and synthetic records.
- [x] AC-02: baseline verify reports exactly the approval-count,
      last-push-approval and RepositoryRole bypass gaps while all required
      checks, strictness and OS/test matrix stay PASS.
- [x] AC-03: fork canary evidence validates: desired body round-trips,
      author/operator merge without review is rejected (HTTP 405), ruleset
      removal recovery works.
- [ ] AC-04: governance gate and independent exact-head publication.

## Non-goals

No production ruleset modification, no receipt forging, no retroactive
approval of historical merges, no weakening of OneDev/conformance/OS
requirements. Positive App-reviewed canary and live deployment belong to the
successor ticket (PLF-062 intake line).

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
