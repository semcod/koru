# Ticket 264: assign scripts python code to application workstream ownedPaths

- **ID**: ticket-264
- **Owner**: claude
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-26

## Goal and scope

Remediate GOV-WORKSTREAM-003 by giving the Python code under `scripts/` an owning
workstream in `.governance/manifest.json`:

1. Add `scripts/**/*.py` to `coordination.workstreams.application.ownedPaths`
   (placed with the other code-root globs, after `services/**/*.py`).
2. Leave the two individually-owned shell scripts where they are: governance
   keeps `scripts/publish-local-onedev-validator.sh` and infrastructure keeps
   `scripts/docker-ide-matrix.sh`. The new Python-only glob never matches a
   `.sh` file, so `rejectActiveScopeOverlap` stays satisfied and shell-script
   ownership does not change.
3. No source changes inside `scripts/` itself and no changes to any other
   workstream's `ownedPaths`.

Context: `scripts/sync-vscode-plugin-version.py` matched no workstream's
`ownedPaths`, so the code2llm-discovered planfile ticket scoped to it (PLF-041
`Shotgun Surgery: content`) was unallocatable (`new-ticket.sh --path
scripts/sync-vscode-plugin-version.py` fails closed with GOV-WORK-START-001).
Once this merges, that ticket can be allocated under application.

Authorization: the operator handoff for PLF-041 explicitly requested the smell
refactor and its execution; the ownership fix is the only compliant allocation
route, recorded here as SESSION_EXECUTION_AUTHORIZATION (agent-owned file; no
`user-*.md` input used).

## Acceptance criteria

- [x] AC-01: `scripts/**/*.py` is present in `application.ownedPaths`; the gate
  ownership predicate resolves `scripts/sync-vscode-plugin-version.py` to
  application only, and `scripts/publish-local-onedev-validator.sh` /
  `scripts/docker-ide-matrix.sh` stay with governance / infrastructure only.
- [x] AC-02: `bash project/governance-check.sh` passes with 0 errors from the
  ticket worktree.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
