# Ticket 154: Skip governance gate for pytest collect-only probes

- **ID**: ticket-154
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-16

## Goal and scope

SESSION_EXECUTION_AUTHORIZATION: the user handed over planfile STARTER-675
(koru-scan signal `pytest_collect_timeout`, semcod/koru#269) with explicit
execution instructions and a completion handoff (`planfile ticket done
STARTER-675`), asking for the pytest collection timeout to be fixed.

SESSION_EXECUTION_AUTHORIZATION (continuation, 2026-09-19): the user asked to
"continue with the next ticket"; work_start_check routed RECONCILE to this
active IN_PROGRESS ticket, so this session resumes the same lease
(`opencode-glm-skip-governance-collect-only-20260916`), completes validation,
and delivers through the repository's protected local publication process.

`pytest --collect-only` from the project root did not finish within the 30s
`koru scan` probe budget. Root cause is not collection itself (pure collection
of the 4441-test suite takes ~11-14s) but the `wellmanifest_governance`
pytest bridge: `pyproject.toml` `addopts` loads it for every pytest session,
and `pytest_sessionstart` runs the `project/governance-check.sh` subprocess
(~25s on this host) even when pytest only collects. When the checkout is
dirty outside the active ticket's intent the gate also fails, aborting
collection with an INTERNALERROR, so the probe can neither finish in time
nor distinguish suite health from checkout-governance state.

Fix: a `--collect-only` session never executes tests; it is a read-only
inventory probe (koru scan / doctor suite-health checks, IDE discovery).
`wellmanifest_governance.py` now returns from `pytest_sessionstart` before
gate resolution whenever `session.config.option.collectonly` is set. Every
session that can execute tests keeps the full gate, including the
recursion guard and GOV-PACKAGING-003 failure modes.

Path ownership: `wellmanifest_governance.py` was previously owned by no
workstream, so any diff to it failed GOV-WORKSTREAM-003. This ticket's
manifest edit assigns the bridge and its regression test to the
integration workstream (the same workstream that owns the `pyproject.toml`
addopts entry that activates the plugin).

Managed-file sync (2026-09-19 continuation): `wellmanifest_governance.py`
and `.governance/manifest.json` are digest-pinned managed files, so their
`.governance/manifest.lock.json` entries are updated in the same delivery
commit (GOV-SYNC-001), following the ticket-005 precedent for a local
managed-file change bound to one ticket. The branch was rebased from
`aec675af` to the current protected main `96f8b7be`; no upstream conflict
resulted and `delivery.acceptedBaseSha` now records the new base.

## Acceptance criteria

- [x] AC-01: Scope is approved by the user's explicit execution request
      (planfile STARTER-675 handoff).
- [x] AC-02: `timeout 30 python3 -m pytest --collect-only -q --no-header`
      exits 0 from a clean ticket checkout in well under 30s.
- [x] AC-03: A collect-only session start does not execute
      `project/governance-check.sh` (regression test asserts no gate
      subprocess).
- [x] AC-04: Non-collect sessions keep enforcement: the gate subprocess
      still runs and a failing gate still raises `GovernanceGateError`
      (regression tests).
- [x] AC-05: `.governance/manifest.json` integration ownedPaths covers
      `wellmanifest_governance.py` and
      `tests/test_wellmanifest_governance.py`.
- [x] AC-06: `./project/governance-check.sh` reports GOV-PASS for this
      ticket branch.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
