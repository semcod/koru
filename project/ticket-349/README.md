# Ticket 349: refine action URI slugs, multiline YAML formatting, and route operator logs to activity

- **ID**: ticket-349
- **Owner**: agent:antigravity
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-28

## Goal and scope

1. Refine `_action_slug` in `src/koru/activity_log.py` to stop before filepaths, strip common warning/info prefixes, remove trailing prepositions, and produce clean concise action slugs.
2. Properly format multiline messages under `NL:` and `DSL:` using standard YAML block indentation (`    `).
3. Route raw `print(...)` in `src/koru/autonomy/operator/operator_wup.py` (`_wup_stdio_info`) and `src/koru/autonomy/cycle/cycle_config.py` through `activity_info()`.
4. Update and add unit tests in `tests/test_activity_log.py`.

## Acceptance criteria

- [x] AC-01: Activity log unit tests in `tests/test_activity_log.py` pass.
- [x] AC-02: Governance check passes with 0 errors and 0 warnings.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
