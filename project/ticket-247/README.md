# Ticket 247: Assign services python code to application workstream in governance manifest

- **ID**: ticket-247
- **Owner**: claude
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-26

## Goal and scope

Remediate GOV-WORKSTREAM-003 by giving the Python code under `services/` an owning
workstream in `.governance/manifest.json`:

1. Add `services/**/*.py` to `coordination.workstreams.application.ownedPaths`
   (placed with the other code-root globs, after `packages/**`).
2. Leave `services/**/Dockerfile*` with the infrastructure workstream; the new
   Python-only glob is disjoint from it, so `rejectActiveScopeOverlap` stays
   satisfied and Dockerfile ownership does not change.
3. No source changes inside `services/` itself and no changes to any other
   workstream's `ownedPaths`.

Context: `services/healing-webhook/*.py` matched no workstream's `ownedPaths`, so
code2llm-discovered planfile tickets scoped to `services/healing-webhook/app.py`
(PLF-039 `Shotgun Surgery: cmd` and the `payload`/`proc`/`outcome` siblings) were
unallocatable and parked in `waiting_input`. Once this merges, those tickets can
be re-dispatched.

Authorization: the operator handoff for PLF-039 explicitly requested this
integration-workstream manifest change and its execution, recorded here as
SESSION_EXECUTION_AUTHORIZATION (agent-owned file; no `user-*.md` input used).

## Acceptance criteria

- [x] AC-01: `services/**/*.py` is present in `application.ownedPaths`; the gate
  ownership predicate resolves every `services/healing-webhook/*.py` file to
  application only and `services/**/Dockerfile*` targets to infrastructure only.
- [x] AC-02: `bash project/governance-check.sh` passes with 0 errors from the
  ticket worktree (GOV-PASS: 0 errors, 0 warnings).

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
