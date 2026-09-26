# Ticket 233: Enhance terminal markdown rendering and add cross-system docker test environments

- **ID**: ticket-233
- **Owner**: antigravity
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-26

## Goal and scope

SESSION_EXECUTION_AUTHORIZATION: On 2026-09-26 the user requested to improve terminal rendering of markdown elements in `koru sum` / `koru summary` (removing raw `#`, `**`, and backticks when run interactively in the terminal), support `--raw` and `--plain` flags, and create multi-distribution Docker testing environments across different operating systems (Ubuntu, Alpine, Fedora) to verify shell display correctness.

## Acceptance criteria

- [ ] AC-01: Terminal Markdown rendering formats headers and lists cleanly without raw `#`, `**`, and backtick markers when attached to an interactive TTY.
- [ ] AC-02: `koru sum` supports `--raw` (pure Markdown output for redirects/pipes) and `--plain` (clean plaintext without ANSI or Markdown syntax).
- [ ] AC-03: Multi-distribution Docker test harness (`tests/docker/Dockerfile.ubuntu`, `tests/docker/Dockerfile.alpine`, `tests/docker/Dockerfile.fedora`, `tests/docker/test_terminals.sh`) verifies terminal output across glibc, musl, and RPM environments.
- [ ] AC-04: All unit tests pass in `tests/test_cli_summary.py` and governance checks pass.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
