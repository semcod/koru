# Ticket 187: PR361 exact-head merge race audit report

- **ID**: ticket-187
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-20
- **Planfile tracking**: STARTER-735 (koru-model-routing-audit)

## Goal and scope

Publish the forensic report resolving STARTER-735: determine whether
exact-head CAS was enforced when `ifuri-validator-agent` merged
semcod/koru PR361 (merge commit `9ce405d0`, merged head `60510a80`)
while the visible approval `5257358794` targeted `acf71f47` and was
dismissed. Analysis is read-only: GitHub observations, protected
validator receipts and validator-agent source/release review. No merge,
push, branch deletion or actor bypass is authorized or performed.

## Deliverable

- `docs/analysis/simple-task-model-routing.md` — appended version 5
  section (timeline, facts, hypotheses, recommendations) preserving the
  existing v1–v4 append-only history.
- `docs/README.md` — index entry for the analysis document.

## Acceptance criteria

- [x] AC-01: Scope is approved by a human owner.
- [x] AC-02: Exact-head CAS question answered from protected receipts,
  live GitHub observations and the deployed validator release source.
- [x] AC-03: Report published at the canonical docs path with versioned
  metadata and indexed in `docs/README.md`.
- [x] AC-04: Protected receipts left untouched; no authorization
  inferred from older green checks; no merge or bypass executed.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
