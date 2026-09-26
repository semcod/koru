# Ticket 256: decompose _action_set_token and switch_profile in git_cli to reduce cyclomatic complexity

- **ID**: ticket-256
- **Owner**: antigravity
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-26

## Goal and scope

Reduce cyclomatic complexity in `src/koru/git_cli.py`:
1. `_action_set_token` (CC=23 -> <=4): Decompose into vault token acquisition (`_acquire_vault_token`), gh CLI auth (`_login_gh_cli`), and shared `.env` writer (`_write_github_env`).
2. `_action_switch_profile`: Reuse `_write_github_env` to eliminate duplicate `.env` file updating logic.
3. Ensure 100% backward compatibility of all CLI commands and verify that all tests in `tests/test_git_cli.py` pass.

## Acceptance criteria

- [x] AC-01: Decompose `_action_set_token` in `src/koru/git_cli.py` so CC <= 4.
- [x] AC-02: All existing tests in `tests/test_git_cli.py` pass without modification.
- [x] AC-03: `ruff check` and `ruff format` report 0 findings.
- [x] AC-04: `./project/governance-check.sh` passes with 0 errors and 0 warnings.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
