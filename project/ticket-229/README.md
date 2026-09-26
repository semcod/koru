# Ticket 229: Add koru sum and summary command for daily execution overview

- **ID**: ticket-229
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-26

## Goal and scope

1. Add `koru sum` and `koru summary` subcommands to the Koru CLI.
2. Provide a daily execution overview aggregating:
   - Living Planfile execution metrics (completed tickets today, pending queue tasks, duration estimates).
   - GitHub Pull Request status (open PRs, merged PRs today).
   - Recent tasks and backlog preview.
   - Support both rich markdown display and `--json` machine-readable output.
3. Allow usage when globally disabled as an informational/read-only command.
4. Add unit test coverage and ensure governance check passes with exit code 0.

## Acceptance criteria

- [x] AC-01: `koru sum` and `koru summary` are registered as recognized subcommands in `koru.cli`.
- [x] AC-02: `koru sum` executes the daily summary gathering and prints formatted markdown overview.
- [x] AC-03: `koru sum --json` outputs structured JSON summary metrics.
- [x] AC-04: Test coverage verifies CLI dispatch and summary generation.
- [x] AC-05: Test suite and `./project/governance-check.sh` pass.

## Session authorization

User explicit request "zamien koru summary na koru sum" treated as SESSION_EXECUTION_AUTHORIZATION.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
