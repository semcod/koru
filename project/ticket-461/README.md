# Ticket 461: Allow staging_worktree on baseline-only .governance/manifest.json repos

- **ID**: ticket-461
- **Owner**: agent:antigravity
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-10-19

SESSION_EXECUTION_AUTHORIZATION: User authorized autonomous resilience improvements in `semcod/koru` so repositories with baseline-only `.governance/manifest.json` (`wellmanifest.manifest/v1` / `profile:baseline`) and no `project/new-ticket.sh` can stage and verify patches via `staging_worktree`.

## Goal and scope

Ensure `_has_governance_marker` in `src/koru/queue/workspace.py` returns `False` when `.governance/manifest.json` only declares `wellmanifest.manifest/v1` / `profile:*` and `project/new-ticket.sh` does not exist, while continuing to enforce governed ticket admission on `wellmanifest/new-project` repositories.

## Acceptance criteria

- [x] AC-01: `pytest -q tests/test_planfile_queue.py -k test_unmanaged_workspace_and_scan_artifacts tests/test_queue_workspace_retention.py`, `python3 -m ruff check src/koru/queue/workspace.py tests/test_planfile_queue.py`, and `./project/governance-check.sh` pass.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
