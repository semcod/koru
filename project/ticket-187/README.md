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
dismissed. The analysis uses GitHub observations, protected validator
receipts and validator-agent source/release review. The initial Planfile
scope prohibited publication; on 2026-09-25 the human user explicitly
authorized pushing and merging overdue Koru tickets. This later instruction
authorizes publication of this report through the normal protected Validator
path. Actor bypass is not authorized.

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
- [x] AC-04: Protected receipts left untouched; no authorization inferred
  from older green checks; publication uses a fresh exact-head Validator
  approval and no bypass.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.

## Delivery contract

This is a documentation-only S-sized integration delivery. It appends the
version 5 audit to the existing analysis and indexes it in `docs/README.md`.
The report preserves versions 1–4, cites protected evidence by digest, and
does not change runtime, merge, approval, or Validator behavior. The contract
in `intent.json` records the accepted base, architecture, rollback, and the
governance, standard-pack, projection, and diff checks used for publication.

## Publication reconciliation (2026-09-25)

The work-start preflight reported stale registered worktrees as pending. Their
corresponding PRs (#396, #397, #398, #376, #377 and #386) are merged, and each
local ticket branch head is an ancestor of the observed `origin/main`. Their
remaining dirty paths are Gradle cache files outside this ticket's documentation
scope. The primary checkout's unrelated local changes were preserved. No
overlapping documentation writer was found.
