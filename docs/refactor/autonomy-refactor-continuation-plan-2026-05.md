# Autonomy Refactor Continuation Plan

Date: 2026-05-25

This plan captures the next refactor wave after stabilizing:

- plugin/socket timeout handling
- submit retry after paste
- duplicate vs create-failed scan outcomes
- shell decision trace
- shell `current mission`

## Current state

The highest-value operator paths are now much clearer:

- `decision: observed -> decided -> action -> evidence -> next`
- `blocked_by=...` appears in decision evidence
- `current mission ticket=... blocker=...` appears in the shell
- repeated `scan -> create_failed` churn is rate-limited

The remaining complexity is concentrated in a few modules that still mix
policy, side effects, and operator narration.

## Refactor priorities

### 1. Split chat-activity policy from side effects

Target:

- `src/koru/autonomous_cycle_chat_activity.py`

Reason:

- `_skip_due_to_recent_chat_activity` still owns too many decisions:
  cooldown policy, intake detection, old/new prompt protection, and shell wording.

Desired outcome:

- `classify_chat_activity(...)`
- `decide_chat_blocker(...)`
- `build_chat_activity_explanation(...)`
- side-effect-free policy helpers with focused unit tests

Acceptance:

- no single helper in this area should need to know about both queue state
  and shell phrasing
- blocker reason should map cleanly to `blocked_by=chat_activity`

### 2. Extract operator narration from loop runner

Target:

- `src/koru/autonomous_loop_runner.py`

Reason:

- `_operator_next_steps`, `_quick_action_lines`, and `current mission`
  are now useful, but the runner still mixes orchestration and human narration.

Desired outcome:

- create an `operator_narration.py` helper module
- runner passes a compact cycle snapshot into that module
- one place builds:
  - `current mission`
  - `next 1/3..3/3`
  - action lines

Acceptance:

- outer loop runner reads like control flow, not presentation code

### 3. Isolate plugin reload / reconnect recovery

Target:

- `src/koru/ide_adapters/ide_reload.py`
- startup/plugin recovery helpers

Reason:

- plugin mismatch, reload, and reconnect policy still fan out across
  startup and autopilot-recovery paths.

Desired outcome:

- one recovery entrypoint that returns:
  - `ok`
  - `blocked_by`
  - operator instructions
  - retryability

Acceptance:

- shell can say `blocked_by=plugin_version_mismatch`
  instead of the more generic `plugin_missing`

### 4. Normalize scan outcomes into a first-class state machine

Target:

- `src/koru/scan.py`
- `src/koru/autonomy/phases/scan_phase.py`

Reason:

- duplicates, reused tickets, create failures, and cooldowns are now present,
  but the model is still partly implicit.

Desired outcome:

- formal scan outcome classes:
  - `applied`
  - `duplicate_active`
  - `reused`
  - `create_failed`
  - `create_failed_cooldown`

Acceptance:

- shell summary, telemetry, and dashboard use the same vocabulary

### 5. Unify compatibility exports during migration

Targets:

- `src/koru/autonomous_cycle.py`
- older test/import compatibility surfaces

Reason:

- some tests and legacy call-sites still expect names that moved to newer modules.

Desired outcome:

- intentional compatibility exports with comments
- one cleanup ticket later removes them after callers migrate

Acceptance:

- no accidental breakage in matrix tests caused only by symbol relocation

## Suggested implementation order

1. `plugin_version_mismatch` blocker classification
2. `operator_narration.py` extraction
3. chat-activity policy split
4. scan outcome normalization
5. cleanup compatibility exports

## Test strategy for the next wave

Keep the test surface layered:

- unit tests for policy helpers
- focused loop-runner tests for shell narration
- matrix tests for IDE-specific flags
- plugin tests for VSIX strategy quirks
- one end-to-end scenario per blocker class

## Antigravity baseline

Validated on 2026-05-25:

- `python -m pytest -q tests/test_autopilot_ide.py -k antigravity`
- `python -m pytest -q tests/test_autonomous_startup.py -k antigravity`
- `python -m pytest -q tests/test_docker_ide_matrix.py tests/ides/test_all_ide_strategies.py -k antigravity`
- `cd plugins/koru-autopilot-vscode && npm run compile && node out/antigravity-fastpath.test.js`

All passed at the time of writing.
