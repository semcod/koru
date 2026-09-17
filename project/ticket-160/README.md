# Ticket 160: Lazy-import heavy CLI subcommand modules to fix slow --help/--version

- **ID**: ticket-160
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-16

## Goal and scope

`koru --help`/`koru --version` took ~0.6-3.5s (variance driven by host load)
because `koru.cli`'s legacy entrypoint eagerly imported `koru.autonomous`,
`koru.cli_scan`, `koru.git_cli`, `koru.autopilot.cli_command`,
`koru.autoloop_cli`, and the `koru.cli` package compat shim eagerly imported
`koru.cli_ide_router` and `koru.cli_auto` — all before argument parsing even
happened. `koru.autonomous` alone pulls in the cycle engine, dashboard/MCP
server and the `nlp2uri` compiler. This surfaced as flaky WUP quick-probe
failures (`STARTER-667`, `cli-koru.testql.toon.yaml`) whose 5s (now bumped to
15s) timeout for `koru --help`/`--version` was regularly blown under load.

Route the affected subcommands through the existing `_lazy_module_main`
pattern already used by most of `_SUBCOMMANDS`, and make the `koru.cli`
package's compat shim resolve `ide_router_main`/`_auto_main` lazily via
`__getattr__` instead of importing them at package-import time.

## Acceptance criteria

- [x] AC-01: `import koru.cli` cost drops (~0.6s -> ~0.3s); none of
  `koru.autonomous`, `koru.cli_auto`, `koru.cli_scan`, `koru.git_cli`,
  `koru.autopilot.cli_command`, `koru.autoloop_cli`, `koru.cli_ide_router`
  appear in `-X importtime` output for `koru --version`.
- [x] AC-02: `mock.patch("koru._legacy_cli_impl.autonomous_main", ...)` and
  `mock.patch("koru._legacy_cli_impl.stop_prior_autonomous_for_auto_start", ...)`
  keep working unchanged (verified via `cli_auto`'s `_legacy_attr` dynamic
  lookup, the actual test contract).
- [x] AC-03: `tests/test_cli.py`, `tests/test_ide_router.py`,
  `tests/test_agent_backends_cli.py`, `tests/test_loop.py`,
  `tests/test_autonomous.py` pass (one pre-existing, unrelated failure in
  `test_autonomous.py` confirmed identical on `main` before this change).

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
