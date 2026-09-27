# Ticket 282: Address code smell: Shotgun Surgery: explicit locals in koru autonomy config startup

- **ID**: ticket-282
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-27
- **Planfile**: PLF-057 (dedupe key
  `code2llm:smell:shotgun_surgery:src/koru/autonomy/configuration/config_startup.py:85:Shotgun Surgery: explicit`)

## Goal and scope

Clear the code2llm Shotgun Surgery smell for the variable `explicit`
in `src/koru/autonomy/configuration/config_startup.py` (reported at line 85,
planfile ticket PLF-057). Five functions in the module each assigned a
generic local named `explicit`; the code2llm shotgun-surgery detector groups
mutations by (file, variable) and fires at >= 5 scopes, so the shared
generic name read as one cross-cutting concern.

Replace the generic local in each function with a stage-accurate name for
the piece of lane resolution that stage actually consumes:

- `ide_env_lane` (`_terminal_agent_lane_from_env`) - the lane declared by
  the `KORU_AUTOPILOT_IDE` env var, consulted only as a fallback when the
  terminal host IDE could not be detected (a different env var from the
  instance selection below).
- `instance_lane` (`_explicit_agent_lane_from_env`, and with
  `instance_source` in `resolve_agent_lane`) - the normalized
  `KORU_AUTOPILOT_INSTANCE` selection the producer returns and the legacy
  `resolve_agent_lane` entry reads straight from the facade.
- `explicit_lane` / `explicit_lane_source` (`_runtime_lane_hints`,
  `resolve_agent_lane_id`) - the explicit-selection hint pair gathered with
  the focused/terminal/running hints and forwarded to
  `_resolve_lane_from_runtime_hints`.

Function parameters named `explicit` / `explicit_source`
(`_resolve_lane_from_runtime_hints`, `_try_focused_lane`,
`_try_runtime_lanes`, `_resolve_lane_from_explicit`,
`_should_terminal_override_explicit`, `_should_running_override_explicit`)
are function arguments, not assignments, so the DFG mutation extractor does
not count them; they keep the accurate domain name for the explicit
selection flowing through the resolution chain. Pure rename: no signature,
return shape, env var or behavior change.

## Acceptance criteria

- [x] AC-01: Standalone code2llm DFGExtractor mutation grouping on the file
  AST reports the `explicit` group dropping from 5 scopes (matching the
  ticket's "spans 5 functions") to 0, with the file mutation record count
  unchanged at 118 (pure rename) and every new name landing at 2/2/2/1/1
  scopes, far below the >= 5 threshold; the untouched `focused` and `picked`
  groups stay at 4.
- [x] AC-02: `python3 -m pytest tests/test_autonomous_startup.py
  tests/test_autonomous.py tests/test_autonomous_cycle_config.py
  tests/test_autonomous_runtime.py tests/test_operator_pipeline.py -q`
  passes unchanged and `ruff check
  src/koru/autonomy/configuration/config_startup.py` reports zero errors -
  pure rename of function-internal locals.
- [x] AC-03: `bash project/governance-check.sh --base <merge-base>` returns
  GOV-PASS from the ticket worktree.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant
prose and raw command logs are not required delivery output.
