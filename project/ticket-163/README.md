# Ticket 163: scan collect-only skips governance plugin

- **ID**: ticket-163
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-17

## Goal and scope

SESSION_EXECUTION_AUTHORIZATION: the user asked to fix the detected koru
autonomy problems ("naprawiaj"), including the recurring
`pytest_collect_timeout` tickets (planfile STARTER-675) that leave
`koru scan` unable to report suite health.

Root cause: `pyproject.toml` loads the managed `wellmanifest_governance`
bridge for every pytest session, and its `pytest_sessionstart` runs
`project/governance-check.sh` (~25s) even for `--collect-only` inventory
probes, pushing them past the 30s scan budget — and aborting collection
entirely when the checkout is dirty (INTERNALERROR).

The bridge file itself is managed by the `wellmanifest/new-project`
adoption lock (GOV-SYNC-001), so a local patch needs an upstream standard
release — that remains ticket-154's track. This ticket takes the
complementary probe-side fix: `scan_pytest_collect` passes
`-p no:wellmanifest_governance`, a no-op for projects without the plugin,
so collection probes measure the suite, not the gate.

## Acceptance criteria

- [x] AC-01: Scope is approved by the user's explicit execution request.
- [x] AC-02: Probe argv contains `-p no:wellmanifest_governance`
      (regression test).
- [x] AC-03: `timeout 30 python3 -m pytest --collect-only -q --no-header
      -p no:wellmanifest_governance` completes inside the scan budget.
- [x] AC-04: `./project/governance-check.sh` reports GOV-PASS.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
