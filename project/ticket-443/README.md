# Ticket 443: Give the unmanaged-workspace queue test its own Git identity

- **ID**: ticket-443
- **Owner**: claude-code
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-10-07

## Goal and scope

`test_unmanaged_workspace_and_scan_artifacts` (added on main in 06648f2a) runs `git commit` relying on a global Git identity. The OneDev executor runs as `nobody` without one, so `onedev/local-verify` fails for every koru pull request (observed on PR #702). Pass the identity explicitly, as the other tests in the file do. User authorization: continue the 8-hour monag/reflex remediation (`kontynuuj`).

## Acceptance criteria

- [ ] AC-01: The test passes with no global Git identity (`HOME` pointing to an empty directory).
- [ ] AC-02: Governance passes.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
