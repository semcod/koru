# Ticket 385: feat(governance): wire pinned docs validation into doc generation path

- **ID**: ticket-385
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-29

## Goal and scope

STARTER-606: integrate pre-generation validation into the real documentation
path. Koru has no separate document generator; `.governance/docs_gate.py` is
the governed entry point. Align its pinned runtime with the adopted standard
0.6.0 revision declared in `.governance/docs.json`, pass the adoption-lock
managed-copy inventory through to the checker, and add a `generate` phase that
cannot write a document before `prepare` succeeds and fully rolls back when
completion validation fails.

## Acceptance criteria

- [x] AC-01: Scope is approved by a human owner.
- [x] AC-02: Adapter pins match `.governance/docs.json` source_revision.
- [x] AC-03: `generate` writes only at the plan-approved path after a successful prepare, stages the deliverable and index, and rolls back on `--complete` failure.
- [x] AC-04: Negative cases exercised through the real generation path in `.governance/tests/test_docs_gate.py`.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
