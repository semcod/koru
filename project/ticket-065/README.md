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

- [ ] AC-01: Dry-run executes standard packs and observes the protected OneDev
  profile result for the frozen PR head and current `main`; currently blocked
  by the deployed executor image missing the configured Koru checker.
- [ ] AC-02: Full run posts REST statuses and invokes the deployed local
  `run-local-direct-pr.sh` adapter; it does not use hosted workflow dispatch.
- [x] AC-03: The local Validator environment and protected App key are loaded
  from the operator's protected configuration, and the adapter receives the
  frozen PR head plus optional pinned SubLLM root.
- [x] AC-04: `--merge` delegates merge authority to the local Validator adapter;
  the publication script never approves or merges directly.

## Validation evidence

- `bash -n scripts/publish-local-onedev-validator.sh` passed.
- The exact checkout passes `governance_check.py --actor ci` against the current
  `main` SHA.
- The script no longer executes `/app/...` profile commands on the operator
  host; it waits for the deployed OneDev executor's exact-head status.
- Focused shell contract checks confirm the hosted dispatch path is absent and
  the local adapter receives repository, PR, ticket, exact head and key.
- A fresh protected retry for PR #249 fails before tests because the active
  `ifuri-onedev-agent:taskand-browser-link` image lacks
  `/app/docker/pr/check-koru-docs.py`; the existing Koru deployment receipt
  records `ifuri-onedev-agent:koru-docs-350-required-canaries` instead. The
  adapter is therefore not invoked and no merge is attempted.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
