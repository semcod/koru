# Ticket 121: Adopt wellmanifest/new-project 0.20.25

- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-12

SESSION_EXECUTION_AUTHORIZATION: adopt, test, push and protected merge, requested by the owner on 2026-09-12.

## Goal and scope

Koru pinned `0.20.13` (`82462523`). The current published release is `0.20.25`
(`d54878a1`), which fixes a defect affecting every adopter that runs Python
3.10: `scripts/agent_host_check.py` imported `tomllib` at module scope,
`governance_check.py` reported the resulting `ImportError` as a missing managed
validator (`GOV-SYNC-001`), and because `GOV-PACKAGING-003` binds the gate to
the test lifecycle, the session aborted. Found and fixed while adopting the
standard in `semcod/planfile`: wellmanifest/new-project#325 (fix), #326
(release 0.20.25).

The adoption advances the managed governance payload, the pre-commit hook,
`AGENTS.md`, `project/new-ticket.sh` and `scripts/runtime.sh`, and realigns both
packaging pins — `pyproject.toml` and `package.json` — with the regenerated lock
(`GOV-PACKAGING-002` compares them).

`pyproject.toml` and `package.json` are integration-required paths, so the
ticket runs in the `integration` workstream. The manifest instance and evidence
files the adoption must rewrite (`.governance/manifest.json`,
`manifest.base.json`, `manifest.lock.json`, `package-manifest.json`) are owned
here by `governance` only, which would split a single atomic adoption across two
workstreams. They are therefore added to `integration.ownedPaths`, matching how
every other repository in the fleet declares them.

Out of scope: any change to Koru's own source, tests or released behaviour.

## Acceptance criteria

- [ ] AC-01: `goal governance adopt --source-revision d54878a… --check` reports no drift.
- [ ] AC-02: `./project/governance-check.sh --base origin/main --head HEAD --actor agent` passes.
- [ ] AC-03: The existing test suite still passes (no source change).

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
