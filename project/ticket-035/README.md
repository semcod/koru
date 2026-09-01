# Ticket 035: Prove HOME standard pack S3 S4 evidence

- **ID**: ticket-035
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: PUBLICATION
- **Created**: 2026-09-01

## Goal and scope

Close issue #63 by replacing the truthful standard-pack audit with a complete,
independently checkable HOME-pack evidence chain. Each required pack is bound
to an immutable source revision, contract and deterministic conformance digest.
S3 evidence is a canonical, content-addressed successful CI receipt; every S4
claim additionally binds an active ruleset that requires the exact S3 check.

This first, governance-owned slice remains fail-closed. `worktrees` and `logs`
stay at S2 while the five HOME packs that already publish protected domain CI
receive complete S3/S4 projections. A following infrastructure ticket adds the
target-owned CI check; a final governance ticket may promote only its real
receipt and matching ruleset.

## Acceptance criteria

- [x] AC-01: The active user explicitly requested autonomous continuation and
  sequential closure of all remaining tasks on 2026-09-01.
- [x] AC-02: Every baseline HOME pack has a generated projection that binds an
  immutable repository revision plus non-empty contract and conformance
  SHA-256 digests.
- [x] AC-03: Each present S3 claim binds a canonical successful CI receipt and
  each present S4 claim binds an active ruleset requiring that exact check.
- [x] AC-04: The target projection checker reports `ok: true`, detects digest
  drift and accepts no empty artifact claim.
- [x] AC-05: Managed standard-pack audit reports exactly the two truthful S3
  gaps for `worktrees` and `logs`; this ticket does not promote them or switch
  the repository to `enforce`.
- [x] AC-06: Governance, required-check, Docker Compose, diff, focused Python
  and protected publication checks pass at the exact merged HEAD.

## Authorization

`SESSION_EXECUTION_AUTHORIZATION` was recorded from the active user's request
to continue autonomously and close all remaining tasks in sequence. It grants
no secret access, direct merge, self-approval or unrelated cross-repository
mutation.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
