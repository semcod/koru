# Ticket 293: integrate-nolimits-storage-check-in-autonomous-prechecks

- **ID**: ticket-293
- **Owner**: agent:gemini
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-27

## Goal and scope

Integrate wellmanifest/nolimits pre-flight storage check (LIM-STORAGE-001) into koru autonomous pre-checks:
- Detect low available disk space (< 10 GB) or ENOSPC before running the autonomous loop cycle.
- Emit structured warning / log directing to `fixos cleanup --threshold-gb 10 && fixos quick`.
- Ensure clean non-failing recovery if fixos is not present or if disk space is sufficient.

## Acceptance criteria

- [x] AC-01: Storage pre-flight check unit tests in `tests/test_autonomous_pre_checks.py` pass 100%.
- [x] AC-02: `./project/governance-check.sh` reports GOV-PASS with 0 errors and 0 warnings.
