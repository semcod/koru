# Ticket 036: Run target standard-pack conformance CI

- **ID**: ticket-036
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-01

## Goal and scope

Add one target-owned, read-only GitHub Actions check that exercises Koru's
adopted HOME standard-pack projections. The stable check supplies a real
successful CI subject for the remaining `wellmanifest/worktrees` and
`wellmanifest/logs` S3 evidence; it does not promote either claim by itself.

## Acceptance criteria

- [x] AC-01: The active user explicitly authorized autonomous continuation and
  sequential closure of the remaining tasks on 2026-09-01.
- [x] AC-02: `standard packs / conformance` runs for pull requests with
  read-only permissions and immutable action pins.
- [x] AC-03: The job checks the standard-pack audit and generated projections,
  validates a canonical worktree record, and verifies the local Logs contract
  identity and safety vocabulary without network-fetched evidence.
- [ ] AC-04: Governance, Docker Compose, workflow-focused checks and protected
  exact-head publication pass; the successful immutable check receipt remains
  available for the following governance ticket.

## Authorization

`SESSION_EXECUTION_AUTHORIZATION` is recorded from the user's request to
continue autonomously and close all remaining tasks in sequence. It grants no
secret access, self-approval, direct merge or unrelated external mutation.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
