# Ticket 042: Enforce complete Docker supply-chain inventory

- **ID**: ticket-042
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: PUBLICATION
- **Created**: 2026-09-02

## Goal and scope

Add the application-owned regression boundary for issue #64. Keep an explicit,
exhaustive inventory of every tracked Dockerfile-like and Compose declaration,
reject newly unreviewed build inputs, and enforce immutable base/Git selection
plus frozen non-root dependency installation. Harden the test-owned IDE matrix
fixture; infrastructure-owned example and orchestration inputs are delivered by
their prerequisite tickets.

## Acceptance criteria

- [x] AC-01: The active user authorized autonomous continuation and sequential
  closure of all remaining and discovered tasks.
- [x] AC-02: The audit enumerates all seven Dockerfile-like inputs and all
  eleven Compose declarations, failing on either an addition or omission.
- [x] AC-03: External `FROM` references and remote Git contexts are immutable;
  a variable base is accepted only when its default and every canonical matrix
  value are digest-pinned.
- [x] AC-04: Every consumed non-root Dockerfile is free of mutable pip
  installation, and the test-owned IDE matrix synchronizes the reviewed lock
  with pinned Python and uv inputs.
- [ ] AC-05: Focused tests, Docker/Compose checks, the managed governance gate
  and exact-head protected publication pass; the merge closes issue #64.

## Authorization

`SESSION_EXECUTION_AUTHORIZATION` is recorded from the user's request to
continue autonomously and close all remaining tasks in sequence. It grants no
secret access, self-approval, direct merge or unrelated mutation.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
