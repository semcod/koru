# Ticket 317: Interactive table and NL shell configurator for koru config

- **ID**: ticket-317
- **Owner**: human:tom
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-27
- **Authorization**: SESSION_EXECUTION_AUTHORIZATION

## Goal and scope

Implement rich table configuration display and an interactive Natural Language (NL) shell assistant for `koru config`:
1. Expose `koru config` alongside `koru configure` in `src/koru/cli.py`.
2. When invoked, render an ASCII/Unicode table showing current project settings (IDE lane, default queue, dashboard host/port/lan/auto_port, active feature toggles, etc.).
3. Provide an interactive shell session prompting: "Co chcesz zmienić? / What would you like to change? (NL or DSL)".
4. Parse natural language intent via deterministic tripartite patterns (e.g., "zmień ide na cursor", "port na 9000", "włącz lan", "turn on mesh", "show config") and update `.koru/config.json`.
5. Add unit and integration tests in `tests/test_configurator*.py`.

## Acceptance criteria

- [x] AC-01: `koru config` renders a formatted table with current project settings.
- [x] AC-02: Interactive NL prompt parses property changes (IDE, queue, port, host, lan, features) in Polish and English.
- [x] AC-03: Changes are validated, applied to `.koru/config.json`, and the refreshed table is displayed.
- [x] AC-04: Test suite in `tests/test_configurator*.py` passes with zero regressions.
- [x] AC-05: `./project/governance-check.sh` reports `GOV-PASS: passed (0 errors, 0 warnings)`.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
