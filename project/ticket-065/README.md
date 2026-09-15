# Ticket 065: Local onedev+validator publication script

- **ID**: ticket-065
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-02

## Goal and scope

Replace the historical hosted `validator-agent` dispatch with the deployed
local Validator direct-PR adapter while preserving the existing frozen-head
standard-pack and OneDev gates. The adapter must receive the repository, PR,
ticket, exact head and protected App key explicitly; the target repository and
the Validator or OneDev source repositories are not modified.

## Acceptance criteria

- [x] AC-01: Dry-run executes standard packs and OneDev profile gates on the frozen PR head.
- [x] AC-02: Full run posts REST statuses and invokes the deployed local
  `run-local-direct-pr.sh` adapter; it does not use hosted workflow dispatch.
- [x] AC-03: The local Validator environment and protected App key are loaded
  from the operator's protected configuration, and the adapter receives the
  frozen PR head plus optional pinned SubLLM root.
- [x] AC-04: `--merge` delegates merge authority to the local Validator adapter;
  the publication script never approves or merges directly.

## Validation evidence

- `bash -n scripts/publish-local-onedev-validator.sh` passed.
- Focused shell contract checks confirm the hosted dispatch path is absent and
  the local adapter receives repository, PR, ticket, exact head and key.
- Final exact-head publication evidence is recorded after the PR is opened.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
