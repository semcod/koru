# Ticket 348: format shell activity logs with yaml URI header and alternating colored NL DSL blocks

- **ID**: ticket-348
- **Owner**: agent:antigravity
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-28

## Goal and scope

1. Format shell activity logs in `src/koru/activity_log.py` with YAML URI header (`uri: koru://...`), followed by alternating colored NL (`NL: ...` in green) and DSL (`DSL: ...` in blue) blocks.
2. Support fallback to legacy one-line format when `fmt="legacy"` or `KORU_LOG_FORMAT=legacy`.
3. Support writing activity logs to `project/ticket-*/koru.log.md` with markdown codeblocks when running within a wellmanifest project layout with an active ticket.
4. Update unit tests in `tests/test_activity_log.py` to verify the URI + NL/DSL formatting and markdown logging.

## Acceptance criteria

- [x] AC-01: Activity log unit tests in `tests/test_activity_log.py` pass.
- [x] AC-02: Governance check passes with 0 errors and 0 warnings.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
