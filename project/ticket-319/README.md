# Ticket 319: NL shell autocomplete and command history for koru config

- **ID**: ticket-319
- **Owner**: human:tom
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-27
- **Authorization**: SESSION_EXECUTION_AUTHORIZATION

## Goal and scope

Enhance the interactive `koru config` shell session with readline support:
1. Provide tab-completion for keywords, action verbs (e.g. `ide na`, `wlacz`, `wylacz`, `port na`, `host na`, `kolejka na`), available IDE lane names, and v2 feature sections (`mesh`, `vision`, `browse`, `sandbox`).
2. Persist command history across sessions in `.koru/config_history` so arrow-up/down navigation works seamlessly.
3. Gracefully fall back to standard `input()` in environments lacking `readline` (e.g., non-TTY pipes or systems without GNU readline).
4. Add automated unit tests covering completion logic and history setup.

## Acceptance criteria

- [ ] AC-01: Tab completion accurately proposes keywords, IDE lanes, and toggles in the interactive shell.
- [ ] AC-02: Command history saves and loads from `.koru/config_history`.
- [ ] AC-03: Headless / mock environments operate safely without errors when readline is unavailable.
- [ ] AC-04: Test suite passes with 0 regressions.
- [ ] AC-05: `./project/governance-check.sh` reports `GOV-PASS: passed (0 errors, 0 warnings)`.
