# Ticket 037: Enforce complete HOME standard pack evidence

- **ID**: ticket-037
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: PUBLICATION
- **Created**: 2026-09-01

## Goal and scope

Finish issue #63 by binding the successful target-owned conformance check from
ticket-036 to the remaining `worktrees` and `logs` projections, making the
stable check a declared and protected requirement, and switching the complete
HOME pack from truthful audit to fail-closed enforcement.

## Acceptance criteria

- [x] AC-01: The active user explicitly authorized autonomous continuation and
  sequential closure of the remaining tasks on 2026-09-01.
- [x] AC-02: Worktrees and Logs claim S3 only through content-addressed
  receipts bound to successful check-run `100007807439`, exact subject
  `10ed0141…`, and their immutable HOME source revisions.
- [x] AC-03: The stable `standard packs / conformance` workflow is allowlisted,
  declared in required checks and required by Koru's active main ruleset.
- [x] AC-04: Standard-pack audit and projection checks both report `ok: true`
  after adoption changes from `audit` to `enforce`.
- [ ] AC-05: Governance, Docker Compose and protected exact-head publication
  pass, issue #63 closes, and all ticket resources are reconciled.

## Authorization

`SESSION_EXECUTION_AUTHORIZATION` is recorded from the user's request to
continue autonomously and close all remaining tasks in sequence. The issue's
accepted scope includes the target repository's protected required-check rule;
no external HOME repository mutation, secret access, self-approval or direct
merge is authorized.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
