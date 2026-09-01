# Ticket 038: Allow enforced standard-pack conformance

- **ID**: ticket-038
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: PUBLICATION
- **Created**: 2026-09-01

## Goal and scope

Make the stable standard-pack workflow accept both valid ends of issue #63's
rollout without weakening its assertions: the current audit must expose
exactly two known S3 gaps, while enforced adoption must be completely green.

## Acceptance criteria

- [x] AC-01: The active user explicitly authorized autonomous continuation and
  sequential closure of the remaining tasks on 2026-09-01.
- [x] AC-02: Audit mode passes only for profile `baseline` with exactly the
  worktrees and Logs S3 findings.
- [x] AC-03: Enforce mode passes only with `ok: true` and no findings; every
  other report shape or mode fails closed.
- [ ] AC-04: Governance, Docker Compose, focused workflow checks and protected
  exact-head publication pass before ticket-037 resumes.

## Authorization

`SESSION_EXECUTION_AUTHORIZATION` is recorded from the user's request to
continue autonomously and close all remaining tasks in sequence. It grants no
secret access, self-approval, direct merge or unrelated mutation.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
