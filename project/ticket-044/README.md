# Ticket 044: Harden remaining Docker build inputs

- **ID**: ticket-044
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: PUBLICATION
- **Created**: 2026-09-02

## Goal and scope

Harden the two remaining infrastructure-owned Docker build inputs found by the
complete issue #64 inventory. The reusable example image must build from
digest-pinned Python and uv images and install only the reviewed lockfile; the
IDE matrix launcher must supply digest-pinned bases for every canonical and
custom system selection.

## Acceptance criteria

- [x] AC-01: The active user authorized autonomous continuation and sequential
  closure of all remaining and discovered tasks.
- [x] AC-02: The reusable example image uses immutable Python and uv inputs,
  validates `uv.lock` without source overrides and performs only frozen uv
  synchronization from that reviewed lock.
- [x] AC-03: The NLP2URI/TestQL example no longer injects mutable package
  requirements and remains covered by the repository's locked `browser` extra.
- [x] AC-04: Every canonical IDE matrix base and any caller-provided base is
  accepted only with a `sha256` manifest digest.
- [ ] AC-05: Focused shell, Docker and Compose checks, the managed governance
  gate and exact-head protected publication all pass.

## Authorization

`SESSION_EXECUTION_AUTHORIZATION` is recorded from the user's request to
continue autonomously and close all remaining tasks in sequence. It grants no
secret access, self-approval, direct merge or unrelated mutation.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
