# Ticket 164: auto-cli-legacy-proxy-kwarg

- **ID**: ticket-164
- **Owner**: devin
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-17

## Goal and scope

`koru auto status` (and every other `koru auto` invocation that resolves
`autonomous_main` through `cli_auto._legacy_attr`) crashes with
`TypeError: autonomous_main() got an unexpected keyword argument
'invoked_as_auto'`. The package `koru/cli/__init__.py` registers `cli.py` as
`koru._legacy_cli_impl`, whose `autonomous_main` is a lazy proxy taking only
`argv`. `cli_auto` calls it with `invoked_as_auto=...`.

Fix: let the legacy proxy accept and forward `**kwargs`.

## Acceptance criteria

- [x] AC-01: `tests/test_cli_legacy_proxy.py` proves the legacy proxy forwards
  `invoked_as_auto` and `_auto_main(["status"])` completes without TypeError.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
