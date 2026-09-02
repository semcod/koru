# Ticket 063: Fetch accepted base history in pull-request smoke CI

- **ID**: ticket-063
- **Owner**: Codex
- **Status**: IN_PROGRESS
- **Workflow state**: PUBLICATION
- **Created**: 2026-09-02

## Goal and scope

Make the pull-request smoke checkout retain the Git history required by the
fail-closed governance plugin.  The incident is reproducible on PR #96: its
valid `delivery.acceptedBaseSha` is an ancestor of `main`, but the default
shallow checkout cannot resolve that commit and aborts pytest before tests run.

This ticket changes only the smoke workflow.  It does not rewrite the accepted
base, weaken governance, broaden GitHub permissions, or modify PR #96.

## Acceptance criteria

- [x] AC-01: the smoke checkout fetches complete history so an older, reachable
  `delivery.acceptedBaseSha` can be resolved.
- [x] AC-02: workflow permissions and governance enforcement remain unchanged.
- [x] AC-03: local workflow-contract validation and the managed governance gate
  pass before protected publication.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
