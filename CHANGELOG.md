# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.10] - 2026-05-21

### Fixed
- Fix unused-imports issues (ticket-fc801415)
- Fix string-concat issues (ticket-a8763d2d)

## [0.1.10] - 2026-05-21

### Fixed
- Fix duplicate-imports issues (ticket-85954cf4)
- Fix unused-imports issues (ticket-02034a47)

## [0.1.10] - 2026-05-21

### Fixed
- Fix unused-imports issues (ticket-550c3386)
- Fix string-concat issues (ticket-e09efa67)

## [0.1.10] - 2026-05-20

### Fixed
- Fix wildcard-imports issues (ticket-7590895b)
- Fix unused-imports issues (ticket-0a61d6be)
- Fix unused-imports issues (ticket-9e01d7c7)
- Fix string-concat issues (ticket-b5e9485d)
- Fix string-concat issues (ticket-358e3d99)
- Fix string-concat issues (ticket-e9489236)
- Fix string-concat issues (ticket-5d4bc4ce)
- Fix unused-imports issues (ticket-45a43753)
- Fix string-concat issues (ticket-48b58582)
- Fix string-concat issues (ticket-e3fb4dfc)
- Fix unused-imports issues (ticket-f0d4bfb2)
- Fix string-concat issues (ticket-b3d48613)
- Fix string-concat issues (ticket-d657eabc)
- Fix unused-imports issues (ticket-f5b7db64)
- Fix string-concat issues (ticket-742be79f)
- Fix duplicate-imports issues (ticket-385fa7ca)
- Fix string-concat issues (ticket-b2ab541b)
- Fix unused-imports issues (ticket-8c527fde)
- Fix string-concat issues (ticket-e0b2d29b)
- Fix unused-imports issues (ticket-8032453c)
- Fix string-concat issues (ticket-48d5f9c0)
- Fix unused-imports issues (ticket-4b62c609)
- Fix llm-generated-code issues (ticket-0355e9e1)
- Fix unused-imports issues (ticket-75d68704)
- Fix unused-imports issues (ticket-025da852)
- Fix unused-imports issues (ticket-577b930b)
- Fix llm-generated-code issues (ticket-aa321302)
- Fix ai-boilerplate issues (ticket-1fbcf810)
- Fix unused-imports issues (ticket-c7c3d857)
- Fix llm-generated-code issues (ticket-65f0dfb8)
- Fix unused-imports issues (ticket-145676c9)
- Fix wildcard-imports issues (ticket-6b64b45b)
- Fix unused-imports issues (ticket-72b5fd2b)
- Fix unused-imports issues (ticket-e5adde4b)
- Fix unused-imports issues (ticket-d940493a)
- Fix string-concat issues (ticket-c919e166)
- Fix string-concat issues (ticket-0a1f98bb)
- Fix unused-imports issues (ticket-e2cd6a64)
- Fix unused-imports issues (ticket-672a7b01)
- Fix string-concat issues (ticket-7dfdde8d)
- Fix unused-imports issues (ticket-304ec8df)
- Fix unused-imports issues (ticket-92901632)
- Fix string-concat issues (ticket-b3256774)
- Fix smart-return-type issues (ticket-d2370920)
- Fix string-concat issues (ticket-daabb08a)
- Fix unused-imports issues (ticket-a484e8f1)
- Fix unused-imports issues (ticket-33228f4b)
- Fix unused-imports issues (ticket-b7f41e1c)
- Fix ai-boilerplate issues (ticket-efe78ad6)
- Fix unused-imports issues (ticket-2d5133c1)
- Fix string-concat issues (ticket-4b9139d2)
- Fix unused-imports issues (ticket-ea1e7cbc)
- Fix unused-imports issues (ticket-ef4a8613)
- Fix unused-imports issues (ticket-9f7812b0)
- Fix llm-generated-code issues (ticket-9525d2d9)
- Fix string-concat issues (ticket-1bd8c441)
- Fix unused-imports issues (ticket-f504f243)
- Fix ai-boilerplate issues (ticket-e11aa041)

## [0.1.156] - 2026-05-20

### Changed
- Keep the base runtime dependency set intentionally small and move optional
  lanes into extras: `api`, `agent`, `obs`, `queue`, `quality`, `watch`, and
  the aggregate `all`.
- Refresh `uv.lock` so package metadata for `koru` exposes the same extras as
  `pyproject.toml`.

### Added
- Document installation extras in the README.
- Add pyproject metadata tests that guard the lightweight runtime dependency
  set, `koru[all]` aggregation, and README coverage for each extra.
- Cross-link the formal IDE control-plane protocol specification from the
  README and documentation index, with documentation tests guarding those
  links.

### Docs
- Synchronize `docs/IDE_PROTOCOL.md` and
  `docs/specs/kide-002-koruide-api-v1.md` with current implementation state:
  keep `v1` wire contract normative, mark plugin lifecycle/reply-capture paths
  as capability-dependent, and clarify that `post_run_verify` is executed by
  the autonomous loop.

## [0.1.10] - 2026-05-19

### Fixed
- Fix relative-imports issues (ticket-f7325658)
- Fix string-concat issues (ticket-706f74be)

## [0.1.10] - 2026-05-17

### Fixed
- Fix unused-imports issues (ticket-a4a995e4)
- Fix magic-numbers issues (ticket-e4000400)
- Fix unused-imports issues (ticket-2c96edda)
- Fix magic-numbers issues (ticket-b4d2f46e)
- Fix ai-boilerplate issues (ticket-d939da3b)
- Fix magic-numbers issues (ticket-fc4c2035)
- Fix unused-imports issues (ticket-bac2611c)

## [0.1.10] - 2026-05-13

### Fixed
- Fix string-concat issues (ticket-4db6394c)

## [0.1.10] - 2026-05-12

### Fixed
- Fix wildcard-imports issues (ticket-4577c0f1)
- Fix ai-boilerplate issues (ticket-f68e6a91)
- Fix string-concat issues (ticket-c4df3c8f)

## [0.1.10] - 2026-05-12

### Fixed
- Fix unused-imports issues (ticket-de208989)
- Fix ai-boilerplate issues (ticket-844c8511)
- Fix unused-imports issues (ticket-67ef5047)

## [0.1.77] - 2026-05-13

### Added (WUP watch integration in `koru autonomous up`)
- `--wup-watch` flag: starts `wup watch <project> --mode testql` as a
  background subprocess alongside the autonomous loop; auto-detected via
  `wup.yaml` presence; respects `gate:wup` topology toggle.
- Per-cycle WUP health read from `.wup/service-health.json`: services with
  status `down`, `failed`, `failure`, or `error` are treated as diagnostics
  failures.
- **Automatic high-priority Planfile tickets** for every failing WUP service:
  `[AUTO-DIAG] wup-<service> needs attention` created in the queue specified
  by `--wup-ticket-queue` (default `default`) with `priority: high`;
  deduplicated via `.planfile/.koru/autoloop-diag/wup-<service>.failed` marker
  files — duplicate tickets are never created until the marker is removed.
- `--wup-diagnostic-tickets / --no-wup-diagnostic-tickets` (default on).
- `--wup-mode {default,testql}` (default `testql`): passed to `wup watch --mode`.
- Full `wup watch` CLI forwarding: `--wup-deps`, `--wup-scenarios-dir`,
  `--wup-testql-bin`, `--wup-track-dir`, `--wup-debounce`, `--wup-cooldown`,
  `--wup-cpu-throttle`, `--wup-quick-limit`, `--wup-config`.
- Env-var overrides: `WUP_WATCH`, `WUP_MODE`, `WUP_DEPS`,
  `WUP_SCENARIOS_DIR`, `WUP_TESTQL_BIN`, `WUP_TRACK_DIR`,
  `WUP_DIAGNOSTIC_TICKETS`, `WUP_TICKET_QUEUE`.
- `wup=<status>` field in per-cycle summary line; WUP subprocess cleanly
  terminated on loop exit/interrupt via `_stop_process`.

### Added (package-native autoloop diagnostics, previously shell-only)
- `--idle-diagnostics {off,quick,full,deep}`: runs `regix`, `wup status`,
  `redup`, `testql suite`, `redsl gate check`, `sumr` when queue is idle.
- `--diagnostic-tickets`: creates deduplicated Planfile tickets for each
  failing diagnostic check; controlled by `ENABLE_DIAGNOSTIC_TICKETS`.
- `--strict-diagnostics`: stops loop with exit code 2 on diagnostics failure.
- `--autopilot-action {drive,handoff,off}`, `--autopilot-on-idle-only`,
  `--autopilot-skip-on-diagnostics-fail`, `--autopilot-skip-statuses`.
- `--backoff-on-stagnation / --no-backoff-on-stagnation` + `--max-sleep-seconds`.
- `--scan-skip-if-clean` + `--scan-skip-after N`.
- `--topology-integration / --no-topology-integration`.
- Full legacy env-var compatibility: `ENABLE_IDLE_DIAGNOSTICS`,
  `IDLE_DIAGNOSTICS_PROFILE`, `ENABLE_DIAGNOSTIC_TICKETS`,
  `DIAGNOSTIC_TICKET_QUEUE`, `DIAGNOSTIC_TICKET_PRIORITY`, `DIAG_STATE_DIR`,
  `STRICT_DIAGNOSTICS`, `AUTOPILOT_ACTION`, `AUTOPILOT_ON_IDLE_ONLY`,
  `AUTOPILOT_SKIP_ON_DIAGNOSTICS_FAIL`, `AUTOPILOT_SKIP_STATUSES`,
  `BACKOFF_ON_STAGNATION`, `SCAN_SKIP_IF_CLEAN`, `TOPOLOGY_INTEGRATION`.

### Fixed
- `koru autonomous up`: `QueueLoopResult` has no `ticket_id` — log line after
  autopilot `drive` on `waiting_input` now uses the last id from ``waiting``;
  added `_queue_loop_waiting_ticket_label` helper.

### Added (autoloop stagnation control)
- `scripts/koru-autoloop.sh` now detects stagnation (same
  `last_status + waiting_ticket_id` across consecutive cycles) and reacts:
  - **Skip-autopilot-on-stuck-status** — `AUTOPILOT_SKIP_STATUSES`
    (default `waiting_input`): autopilot drive fires once when the status
    appears, then is skipped on subsequent identical cycles to stop hammering
    a ticket that is genuinely blocked on human input.
  - **Exponential sleep backoff** — `BACKOFF_ON_STAGNATION=true` (default) +
    `MAX_SLEEP_SECONDS=900`: sleep grows `SLEEP_SECONDS × 2^streak` capped at
    `MAX_SLEEP_SECONDS`. Resets when status or waiting ticket id changes.
  - **Scan-skip-if-clean** — `SCAN_SKIP_IF_CLEAN=false` (opt-in) +
    `SCAN_SKIP_AFTER=1`: after N consecutive `koru scan: no suggestions`
    outputs, subsequent scans are skipped while `git rev-parse HEAD` is
    unchanged.
- Per-cycle summary line now includes `waiting=<ticket_id|none>`,
  `streak=<n>`, and the effective `sleep=<seconds>s`.
- New vars surfaced in `queue:autoloop` Taskfile entry with sane defaults.

### Added
- `scripts/koru-autoloop.sh` rewritten as the canonical unattended loop:
  supports `TICKET_SOURCES=queue|scan|all`, optional idle diagnostics
  (regix / wup / redup / testql / redsl / sumr) with `IDLE_DIAGNOSTICS_PROFILE`,
  `STRICT_DIAGNOSTICS`, `[AUTO-DIAG]` ticket auto-creation with dedup markers,
  autopilot `drive|handoff|off`, `MAX_CYCLES`, `INITIAL_DELAY_SECONDS`, and
  source-install overrides (`KORU_CMD`, `KORU_PLANFILE_CMD`, `KORU_PYTHONPATH`).
  Backward compatible: previous env vars (`PROJECT`, `ACTOR`, `QUEUE_NAME`,
  `MAX_ITERATIONS`, `SLEEP_SECONDS`, `ENABLE_SCAN`, `ENABLE_AUTOPILOT_DRIVE`,
  `ENABLE_INTERACTIVE`, `DRIVE_PROMPT`) keep their original semantics.
- `scripts/koru-autoloop-reset-diag-markers.sh` (+ tiny
  `scripts/_koru_autodiag_filter_tickets.py` helper) — clears autoloop
  diagnostic dedup markers and optionally closes matching open `[AUTO-DIAG]`
  tickets via `planfile ticket update`.
- New `queue:autoloop:reset-diag-markers` Taskfile entry; `queue:autoloop`
  extended to expose every new env var with sane defaults.

### Changed
- Consumer Taskfiles can now replace ~400-line inline autoloop blocks with a
  thin `bash $KORU_HOME/scripts/koru-autoloop.sh` wrapper driven by env vars.
- Added project topology support (`.koru/topology.yaml`) and new
  `koru topology` subcommand for viewing/editing component and pipeline
  enablement from CLI (`--format json`, `--enable/--disable`,
  `--enable-pipeline/--disable-pipeline`, `--is-enabled`).
- `koru serve` dashboard now exposes `GET/POST /api/topology` and renders a
  new **Topology & pipelines** panel with checkbox-based edits persisted to
  `.koru/topology.yaml`.
- `scripts/koru-autoloop.sh` now honors topology toggles:
  `scan:on-change`, `autoloop:queue`, `idle-diagnostics`, `autopilot:drive`
  pipelines and per-tool diagnostic component switches (regix/wup/redup/
  testql/redsl/sumr).
- Quality tasks now honor topology gate flags:
  `quality:regix` ↔ `gate:regix`, `quality:redup*` ↔ `gate:redup`,
  `quality:sumr:*` ↔ `gate:sumr`.

## [0.1.76] - 2026-05-13

### Docs
- Update README.md

### Test
- Update tests/test_autonomous.py

### Other
- Update uv.lock

## [0.1.75] - 2026-05-13

### Docs
- Update README.md

### Test
- Update tests/test_autonomous.py

### Other
- Update uv.lock

## [0.1.74] - 2026-05-13

### Docs
- Update README.md

### Test
- Update tests/test_autonomous.py

### Other
- Update uv.lock

## [0.1.73] - 2026-05-13

### Docs
- Update CHANGELOG.md
- Update README.md

### Test
- Update tests/test_planfile_queue.py

### Other
- Update uv.lock

## [0.1.72] - 2026-05-13

### Docs
- Update README.md

### Test
- Update tests/test_autonomous.py

### Other
- Update .planfile/config.yaml
- Update .planfile/sprints/current.yaml
- Update uv.lock

## [0.1.71] - 2026-05-13

### Docs
- Update README.md

### Other
- Update plugins/koru-autopilot-vscode/out/extension.js
- Update plugins/koru-autopilot-vscode/out/extension.js.map
- Update plugins/koru-autopilot-vscode/package.json
- Update plugins/koru-autopilot-vscode/src/extension.ts
- Update uv.lock

## [0.1.70] - 2026-05-13

### Docs
- Update README.md
- Update SUMD.md
- Update SUMR.md
- Update TODO.md

### Other
- Update project/duplication.toon.yaml
- Update project/map.toon.yaml
- Update uv.lock

## [0.1.69] - 2026-05-13

### Docs
- Update CHANGELOG.md
- Update README.md
- Update SUMD.md
- Update SUMR.md
- Update TODO.md
- Update project/README.md
- Update project/context.md

### Other
- Update .code2llm_cache/app_1778613276699000000_28970.pkl
- Update .code2llm_cache/autonomous_1778659699568702189_15048.pkl
- Update .code2llm_cache/bootstrap_1778612883007000000_15786.pkl
- Update .code2llm_cache/cli_command_1778651740833531424_27525.pkl
- Update .code2llm_cache/context_1778651740838531442_42132.pkl
- Update .code2llm_cache/doctor_1778651740875531574_19704.pkl
- Update .code2llm_cache/extension_1778666364997964239_11430.pkl
- Update .code2llm_cache/extension_1778668075114051194_11664.pkl
- Update .code2llm_cache/package_1778666405224925115_2330.pkl
- Update .code2llm_cache/package_1778668061289910171_2330.pkl
- ... and 28 more files

## [0.1.68] - 2026-05-13

### Docs
- Update README.md

### Other
- Update plugins/koru-autopilot-vscode/package.json
- Update plugins/koru-autopilot-vscode/src/extension.ts
- Update uv.lock

## [0.1.67] - 2026-05-13

### Docs
- Update README.md

### Other
- Update plugins/koru-autopilot-vscode/out/extension.js
- Update plugins/koru-autopilot-vscode/out/extension.js.map
- Update plugins/koru-autopilot-vscode/src/extension.ts
- Update uv.lock

## [0.1.66] - 2026-05-13

### Docs
- Update README.md

### Test
- Update tests/test_autonomous.py

### Other
- Update uv.lock

## [0.1.65] - 2026-05-13

### Docs
- Update README.md
- Update plugins/koru-autopilot-vscode/CHANGELOG.md
- Update plugins/koru-autopilot-vscode/README.md

### Test
- Update tests/test_scan.py

### Other
- Update plugins/koru-autopilot-vscode/out/extension.js
- Update plugins/koru-autopilot-vscode/out/extension.js.map
- Update plugins/koru-autopilot-vscode/src/extension.ts
- Update uv.lock

## [0.1.64] - 2026-05-12

### Docs
- Update README.md

### Test
- Update tests/test_planfile_queue.py

### Other
- Update uv.lock

## [0.1.63] - 2026-05-12

### Docs
- Update README.md

### Other
- Update services/healing-webhook/app.py
- Update uv.lock

## [0.1.62] - 2026-05-12

### Docs
- Update README.md

### Test
- Update tests/test_autonomous.py

### Other
- Update uv.lock

## [0.1.61] - 2026-05-12

### Docs
- Update README.md

### Test
- Update tests/test_autonomous.py
- Update tests/test_scan.py

### Other
- Update uv.lock

## [0.1.60] - 2026-05-12

### Docs
- Update README.md

### Test
- Update tests/test_doctor.py

### Other
- Update plugins/koru-autopilot-vscode/out/extension.js
- Update plugins/koru-autopilot-vscode/out/extension.js.map
- Update uv.lock

## [0.1.59] - 2026-05-12

### Docs
- Update README.md

### Other
- Update uv.lock

## [0.1.58] - 2026-05-12

### Docs
- Update README.md
- Update SUMD.md
- Update SUMR.md
- Update TODO.md
- Update project/README.md
- Update project/context.md

### Test
- Update tests/test_docker_e2e.py

### Other
- Update .code2llm_cache/Dockerfile_1778596139000000000_1532.pkl
- Update .code2llm_cache/planfile-sync-todo_1778596054089531179_8721.pkl
- Update .code2llm_cache/planfile_1778596141701942870_35943.pkl
- Update .code2llm_cache/pyproject_1778596186490937936_2031.pkl
- Update planfile.yaml
- Update project/analysis.toon.yaml
- Update project/calls.mmd
- Update project/calls.png
- Update project/calls.toon.yaml
- Update project/calls.yaml
- ... and 10 more files

## [0.1.57] - 2026-05-12

### Docs
- Update CHANGELOG.md
- Update README.md
- Update SUMD.md
- Update SUMR.md
- Update TODO.md
- Update project/README.md
- Update project/context.md

### Test
- Update tests/test_context.py
- Update tests/test_doctor.py
- Update tests/test_init.py
- Update tests/test_planfile_queue.py

### Other
- Update .code2llm_cache/autonomous_1778595812604000000_13364.pkl
- Update .gitignore
- Update .planfile/config.yaml
- Update .planfile/sprints/current.yaml
- Update app.doql.less
- Update planfile.yaml
- Update project/analysis.toon.yaml
- Update project/calls.mmd
- Update project/calls.png
- Update project/calls.toon.yaml
- ... and 14 more files

## [0.1.56] - 2026-05-12

### Docs
- Update README.md
- Update project/context.md

### Test
- Update tests/test_scan.py

### Other
- Update project/analysis.toon.yaml
- Update project/calls.mmd
- Update project/calls.toon.yaml
- Update project/calls.yaml
- Update project/compact_flow.mmd
- Update project/compact_flow.png
- Update project/evolution.toon.yaml
- Update project/flow.mmd
- Update project/flow.png
- Update project/map.toon.yaml
- ... and 2 more files

## [0.1.55] - 2026-05-12

### Docs
- Update README.md

### Other
- Update uv.lock

## [0.1.54] - 2026-05-12

### Docs
- Update README.md

### Test
- Update tests/test_docker_e2e.py

## [0.1.53] - 2026-05-12

### Docs
- Update README.md

### Other
- Update uv.lock

## [0.1.52] - 2026-05-12

### Docs
- Update README.md

### Test
- Update tests/test_autopilot_daemon.py

### Other
- Update uv.lock

## [0.1.51] - 2026-05-12

### Docs
- Update README.md
- Update docs/cli-examples.md
- Update docs/llm-tools/goal/README.md

### Test
- Update tests/test_autonomous.py
- Update tests/test_autopilot_client_drive_errors.py
- Update tests/test_autopilot_plugin_installer.py

### Other
- Update uv.lock

## [0.1.50] - 2026-05-12

### Docs
- Update README.md

### Other
- Update uv.lock

## [0.1.49] - 2026-05-12

### Docs
- Update README.md
- Update docs/ai-tool-support-roadmap-2026.md
- Update docs/cli-examples.md

### Test
- Update tests/test_autopilot_plugin_installer.py
- Update tests/test_e2e.py
- Update tests/test_tools.py

### Other
- Update uv.lock

## [0.1.48] - 2026-05-12

### Docs
- Update README.md
- Update docs/autopilot-quickstart.md

### Test
- Update tests/test_autonomous.py
- Update tests/test_autopilot_cli.py
- Update tests/test_autopilot_host_setup.py
- Update tests/test_autopilot_plugin_installer.py

### Other
- Update uv.lock

## [0.1.47] - 2026-05-12

### Docs
- Update README.md
- Update docs/autopilot-quickstart.md

### Test
- Update tests/test_autopilot_cli.py
- Update tests/test_autopilot_host_setup.py
- Update tests/test_init.py

### Other
- Update uv.lock

## [0.1.46] - 2026-05-12

### Docs
- Update README.md

### Test
- Update tests/test_autonomous.py

### Other
- Update uv.lock

## [0.1.45] - 2026-05-12

### Docs
- Update README.md

### Other
- Update .planfile/config.yaml
- Update .planfile/sprints/current.yaml
- Update uv.lock

## [0.1.44] - 2026-05-12

### Docs
- Update README.md

### Test
- Update tests/test_autopilot_injector.py

### Other
- Update .planfile/config.yaml
- Update .planfile/sprints/current.yaml
- Update uv.lock

## [0.1.43] - 2026-05-12

### Docs
- Update README.md

### Test
- Update tests/test_autonomous.py

### Other
- Update .planfile/config.yaml
- Update .planfile/sprints/current.yaml
- Update uv.lock

## [0.1.42] - 2026-05-12

### Docs
- Update README.md

### Test
- Update tests/test_cli.py
- Update tests/test_init.py

### Other
- Update uv.lock

## [0.1.41] - 2026-05-12

### Docs
- Update README.md
- Update docs/ai-tool-registry-2026.yaml

### Test
- Update tests/test_agent_cli.py
- Update tests/test_agents.py
- Update tests/test_cli.py
- Update tests/test_init.py

### Other
- Update uv.lock

## [0.1.40] - 2026-05-12

### Docs
- Update README.md
- Update docs/ai-tool-registry-2026.yaml
- Update docs/autopilot-quickstart.md

### Test
- Update tests/test_agent_cli.py
- Update tests/test_agents.py
- Update tests/test_autonomous.py

### Other
- Update plugins/koru-autopilot-vscode/out/extension.js
- Update plugins/koru-autopilot-vscode/out/extension.js.map
- Update plugins/koru-autopilot-vscode/package.json
- Update plugins/koru-autopilot-vscode/src/extension.ts
- Update plugins/koru-autopilot-vscode/src/socketPath.ts
- Update uv.lock

## [0.1.39] - 2026-05-12

### Docs
- Update README.md
- Update docs/ai-tool-registry-2026.yaml

### Test
- Update tests/test_agent_cli.py
- Update tests/test_agents.py

### Other
- Update uv.lock

## [0.1.38] - 2026-05-12

### Docs
- Update README.md
- Update docs/ai-tool-registry-2026.yaml
- Update docs/cli-examples.md

### Test
- Update tests/test_agents.py
- Update tests/test_e2e.py
- Update tests/test_serve.py
- Update tests/test_tasks.py
- Update tests/test_tools.py

### Other
- Update uv.lock

## [0.1.37] - 2026-05-12

### Docs
- Update README.md
- Update docs/autopilot-quickstart.md

### Test
- Update tests/test_autopilot_socket_path.py
- Update tests/test_planfile_queue.py

### Other
- Update uv.lock

## [0.1.36] - 2026-05-12

### Docs
- Update README.md
- Update docs/ai-tool-registry-2026.yaml
- Update docs/ai-tool-support-roadmap-2026.md
- Update docs/cli-examples.md

### Test
- Update tests/test_cli.py
- Update tests/test_context.py
- Update tests/test_tools.py

### Other
- Update uv.lock

## [0.1.35] - 2026-05-12

### Docs
- Update README.md
- Update docs/cli-examples.md

### Test
- Update tests/test_autonomous.py
- Update tests/test_cli.py

### Other
- Update uv.lock

## [0.1.34] - 2026-05-12

### Docs
- Update README.md

### Other
- Update scripts/autopilot-ide-autodetect-smoke.sh
- Update uv.lock

## [0.1.33] - 2026-05-12

### Docs
- Update README.md

### Test
- Update tests/test_autopilot_ide.py

### Other
- Update todo.txt
- Update uv.lock

## [0.1.32] - 2026-05-12

### Docs
- Update README.md

### Test
- Update tests/test_cli.py

### Other
- Update uv.lock

## [0.1.31] - 2026-05-12

### Docs
- Update CHANGELOG.md
- Update README.md
- Update SUMD.md
- Update SUMR.md
- Update TODO.md
- Update project/README.md
- Update project/context.md

### Test
- Update tests/test_cli.py
- Update tests/test_serve.py
- Update tests/test_topology.py

### Other
- Update .code2llm_cache/Taskfile_1778525237055265475_27883.pkl
- Update .code2llm_cache/_koru_autodiag_filter_tickets_1778524403703486605_1528.pkl
- Update .code2llm_cache/cli_1778567150374650580_51708.pkl
- Update .code2llm_cache/cli_command_1778518432434194270_18308.pkl
- Update .code2llm_cache/goal_1778518324199028450_12224.pkl
- Update .code2llm_cache/ide_1778518418959049129_8357.pkl
- Update .code2llm_cache/koru-autoloop-reset-diag-markers_1778524392710367896_3447.pkl
- Update .code2llm_cache/koru-autoloop_1778525155990423131_17609.pkl
- Update .code2llm_cache/planfile_1778518061975203793_35931.pkl
- Update .code2llm_cache/prefact_1778517966479175023_1664.pkl
- ... and 25 more files

## [0.1.30] - 2026-05-11

### Docs
- Update CHANGELOG.md
- Update README.md

### Other
- Update Taskfile.yml
- Update scripts/_koru_autodiag_filter_tickets.py
- Update scripts/koru-autoloop-reset-diag-markers.sh
- Update scripts/koru-autoloop.sh
- Update uv.lock

## [0.1.10] - 2026-05-11

### Fixed
- Fix relative-imports issues (ticket-df60c7f0)
- Fix string-concat issues (ticket-4db6394c)
- Fix unused-imports issues (ticket-a4a995e4)
- Fix magic-numbers issues (ticket-e4000400)
- Fix ai-boilerplate issues (ticket-00ecf056)
- Fix magic-numbers issues (ticket-4979d10a)
- Fix unused-imports issues (ticket-3705da7f)
- Fix string-concat issues (ticket-96ddfeb6)
- Fix unused-imports issues (ticket-0338382e)
- Fix magic-numbers issues (ticket-43342122)
- Fix llm-generated-code issues (ticket-c7cbd75b)
- Fix relative-imports issues (ticket-8da0d779)
- Fix unused-imports issues (ticket-e20874cd)
- Fix relative-imports issues (ticket-36924c04)
- Fix unused-imports issues (ticket-9d4026f3)
- Fix relative-imports issues (ticket-cad96eb7)
- Fix string-concat issues (ticket-608b1621)
- Fix unused-imports issues (ticket-fc801415)
- Fix magic-numbers issues (ticket-49c9c9c5)
- Fix unused-imports issues (ticket-3b3357ce)
- Fix string-concat issues (ticket-8d9ad20b)
- Fix unused-imports issues (ticket-7a764393)
- Fix magic-numbers issues (ticket-093c00aa)
- Fix unused-imports issues (ticket-d47ebcbc)
- Fix relative-imports issues (ticket-7f1158ec)
- Fix unused-imports issues (ticket-eac56b85)
- Fix string-concat issues (ticket-fb0360b5)
- Fix unused-imports issues (ticket-e6f909a4)
- Fix relative-imports issues (ticket-3c6aebf4)
- Fix string-concat issues (ticket-ca671eed)
- Fix unused-imports issues (ticket-a7be5c1c)
- Fix relative-imports issues (ticket-6ebc4f95)
- Fix string-concat issues (ticket-c6a19a28)
- Fix unused-imports issues (ticket-79ba281f)
- Fix ai-boilerplate issues (ticket-2f8a1a61)
- Fix string-concat issues (ticket-d14c56ab)
- Fix unused-imports issues (ticket-2c1f1e0f)
- Fix relative-imports issues (ticket-50ba1aa7)
- Fix string-concat issues (ticket-f1e7e2d6)
- Fix unused-imports issues (ticket-eb177141)
- Fix magic-numbers issues (ticket-8d13328a)
- Fix relative-imports issues (ticket-ff2879d8)
- Fix string-concat issues (ticket-7212e0d5)
- Fix unused-imports issues (ticket-676b4c09)
- Fix magic-numbers issues (ticket-2db1406e)
- Fix unused-imports issues (ticket-b9312e6e)
- Fix duplicate-imports issues (ticket-164ccfc7)
- Fix unused-imports issues (ticket-18e9417b)
- Fix ai-boilerplate issues (ticket-8faeb137)
- Fix string-concat issues (ticket-e11f3ca1)
- Fix unused-imports issues (ticket-c53e0bb6)
- Fix relative-imports issues (ticket-42f3229a)
- Fix string-concat issues (ticket-ca610d9b)
- Fix unused-imports issues (ticket-ff4a380a)
- Fix unused-imports issues (ticket-174985ce)
- Fix magic-numbers issues (ticket-1fb15901)
- Fix string-concat issues (ticket-7b5daa64)
- Fix unused-imports issues (ticket-2043d52d)
- Fix relative-imports issues (ticket-5b0ce565)
- Fix unused-imports issues (ticket-71583a1e)
- Fix magic-numbers issues (ticket-90f432d9)
- Fix relative-imports issues (ticket-434675f8)
- Fix string-concat issues (ticket-821fb723)
- Fix unused-imports issues (ticket-c141f52a)
- Fix duplicate-imports issues (ticket-46c07111)
- Fix string-concat issues (ticket-04318be7)
- Fix unused-imports issues (ticket-cbcfbd1e)
- Fix magic-numbers issues (ticket-ad2e997e)
- Fix relative-imports issues (ticket-1abcf896)
- Fix string-concat issues (ticket-cd3c6a54)
- Fix unused-imports issues (ticket-5dd5179a)
- Fix magic-numbers issues (ticket-072eeb06)
- Fix unused-imports issues (ticket-c4d3680e)
- Fix relative-imports issues (ticket-33785319)
- Fix string-concat issues (ticket-f1f786ff)
- Fix unused-imports issues (ticket-c4d9199a)
- Fix magic-numbers issues (ticket-88e20104)
- Fix unused-imports issues (ticket-1c4d6d92)
- Fix relative-imports issues (ticket-6f83ea0c)
- Fix unused-imports issues (ticket-e177bc99)
- Fix magic-numbers issues (ticket-690814b1)
- Fix string-concat issues (ticket-16057a27)
- Fix unused-imports issues (ticket-2e9ca6b2)
- Fix magic-numbers issues (ticket-11ae8d32)
- Fix unused-imports issues (ticket-bd7736ee)
- Fix smart-return-type issues (ticket-a572c882)
- Fix string-concat issues (ticket-82292562)
- Fix unused-imports issues (ticket-9e5b9187)
- Fix unused-imports issues (ticket-11348133)
- Fix llm-hallucinations issues (ticket-b656f940)
- Fix smart-return-type issues (ticket-b8bffb20)
- Fix string-concat issues (ticket-29475b85)
- Fix unused-imports issues (ticket-fe372ae0)
- Fix unused-imports issues (ticket-eab5287c)
- Fix llm-hallucinations issues (ticket-c12f1cde)
- Fix smart-return-type issues (ticket-247474b0)
- Fix string-concat issues (ticket-0fdbde7e)
- Fix unused-imports issues (ticket-513c873c)
- Fix llm-hallucinations issues (ticket-bc05499e)
- Fix unused-imports issues (ticket-f56c986e)

## [Unreleased]

### Added — Autopilot: drive an IDE's LLM chat from the terminal

- **New subsystem `koru.autopilot`** — `src/koru/autopilot/{protocol,
  injector, ide, daemon, client, cli_command}.py`. Brokers between IDE
  plugins and CLI clients over a local unix socket
  (`$XDG_RUNTIME_DIR/koru-autopilot.sock`, mode `0600`,
  `SO_PEERCRED`-enforced same-UID). Wire protocol is NDJSON with a 1
  MiB per-line cap and a fixed type whitelist (see
  [`docs/autopilot-design.md`](docs/autopilot-design.md)).
- **New CLI verb `koru autopilot`** with sub-actions `daemon`, `drive`,
  `status`, `shutdown`, `ide-list`, `doctor`. Wired in
  `src/koru/cli.py` alongside the existing `task`, `agent`, `serve`,
  `scan`, `gate`, `queue`, `gc` subcommand routes.
- **Auto-handoff** — when an IDE-side plugin emits `session.ended`,
  the daemon builds the canonical koru brief
  (`koru.context.build_context` + `render_markdown_handoff`) and
  injects it back into the chat as `chat.send`. Anti-loop cooldown
  via `--handoff-cooldown` (default 2 s); fully opt-outable with
  `--no-handoff`. Real-world smoke shipped a 5388-char brief in
  one round trip.
- **Three injection backends** (auto-picked by session type): plugin
  socket → `xdotool` (X11) → `wtype` / `ydotool` (Wayland). Per-IDE
  submit keymap (`Return` for VS Code family, `Ctrl+Return` for
  JetBrains).
- **IDE process scan** (`src/koru/autopilot/ide.py`) recognises
  Windsurf, VS Code / VSCodium / code-oss, Cursor, JetBrains IDEs
  (idea / pycharm / webstorm / phpstorm / goland / clion / rubymine),
  and Zed via `/proc/<pid>/comm` + `cmdline` matching.
- **VS Code / Windsurf / Cursor extension scaffolding**
  (`plugins/koru-autopilot-vscode/`, TypeScript): connects to the
  daemon, status bar indicator, paste-and-submit injection, auto-
  reconnect.
- **JetBrains plugin stub** (`plugins/koru-autopilot-jetbrains/`) —
  Phase 3 placeholder. JetBrains users currently get keyboard-sim.
- **Documentation:** new
  [`docs/autopilot-quickstart.md`](docs/autopilot-quickstart.md),
  [`docs/autopilot-design.md`](docs/autopilot-design.md), and
  [`docs/autopilot-roadmap.md`](docs/autopilot-roadmap.md); README
  section "Autopilot — drive your IDE from the terminal" added under
  the no-args brief description.
- **Tests:** 53 new in `tests/test_autopilot_{protocol,injector,ide,
  daemon,cli}.py` (protocol round-trip, backend selection per
  session type, IDE process scan, in-thread daemon round-trip,
  plugin-forward path, handoff happy path / disabled / cooldown,
  CLI smoke). Full suite: **343 passed, 0 regressions**.

### Changed — Autopilot refactor pass 1

- **R14 / TS compile fix** (`plugins/koru-autopilot-vscode/src/extension.ts`)
  — `Thenable<T>` has no `.catch`, which broke `npm run compile`.
  New `runCommand()` helper wraps each `vscode.commands.executeCommand`
  call in `Promise.resolve(...)` + `try/catch`, returns a `boolean`,
  and logs failures.
- **R10 / reconnect jitter** — the VS Code extension's reconnect timer
  now uses `3000 ± 500 ms` instead of a fixed 3 s, so when the daemon
  restarts with N IDE windows open they no longer dog-pile in the same
  window.
- **R8 (partial) / clipboard restore** — `injectChat` now snapshots
  the clipboard *before* the `try` block and restores it in a `finally`,
  so a thrown paste/submit no longer strands our payload in the
  user's clipboard. The long-term plan (switch to
  `vscode.chat.sendMessage` once it stabilises) is still open.
- **R1 / handler-dispatch indirection** — the module-level
  `_HANDLERS` dict and the seven `_h_*` thin wrappers are gone.
  `AutopilotDaemon._build_handler_table()` now builds a per-instance
  `{type → bound method}` dispatch table; `_dispatch` calls the bound
  method directly.
- **R9 / `_handle_drive` split** — the plugin-path and
  keyboard-simulation branches now live in dedicated
  `_drive_via_plugin` / `_drive_via_keyboard` methods, each testable
  in isolation.
- **R2 / test plumbing** — extracted `_DaemonHarness` context manager,
  `_LineReader` (stateful NDJSON parser), `_connect_plugin()` and
  `_assert_no_more_data()` helpers in
  `tests/test_autopilot_daemon.py`. Every socket-level test now uses
  the helpers; future tests will need ~5 lines instead of ~20.

Full suite still **343 passed, 0 regressions** after these changes.
Real-world smoke (`koru autopilot daemon` + scripted plugin) still
delivers the 5388-char brief in one round trip.

### Changed — Autopilot refactor pass 2

- **R12 / protocol schema cap** — new `_FIELD_SCHEMA` whitelist in
  `src/koru/autopilot/protocol.py`. `decode()` now silently drops
  unknown fields per message type, e.g. a plugin sending
  `{"type":"hello","ide":"vscode","version":"…","pid":1,"__proto__":"evil"}`
  no longer propagates `__proto__` into `Message.data`. Strict types:
  `hello`, `chat.send`, `drive`, `session.{started,ended}`, `ping`,
  `shutdown`, `status`. Pass-through (informational): `ack`, `error`.
- **R4 / lazy-import memoisation** — `_default_handoff` no longer
  re-imports `koru.context` on every `session.ended`. The new
  `_load_context_module()` is `functools.lru_cache(maxsize=1)`.
- **R5 / IDE detection cache** — `ide.detect_running_ides_cached(ttl=2.0)`
  + `clear_detect_cache()`. The daemon now binds the cached entry-point
  via `from .ide import detect_running_ides_cached as detect_running_ides`,
  so a tight loop of `drive` / `status` calls doesn't rescan `/proc`.
- **R3 / fail loud on multi-modifier wtype combos** —
  `Injector._press_wtype` now raises `InjectorError` when a submit key
  has more than one modifier (e.g. `ctrl+shift+Return`), preventing
  silent misbehaviour from the previous naive press/release ordering.

**Tests added (11):** 6× protocol field whitelist (strict drop, ack
pass-through, error pass-through, drive valid, ping zero-field, fixed
schema), 2× wtype modifier guard (rejects multi, accepts single), 3×
IDE detection cache (within-TTL, ttl=0 refresh, clear forces refresh).

Full suite: **354 passed, 0 regressions.** Real-world smoke now also
confirms protocol cap (plugin `hello` with `__proto__:"evil"` produces
clean ack with no propagation).

### Added — Autopilot user config (R7, refactor pass 3)

- **New module** `src/koru/autopilot/config.py` reads
  `$XDG_CONFIG_HOME/koru/autopilot.toml` (defaults to
  `~/.config/koru/autopilot.toml`). Provides `AutopilotConfig`,
  `load_config()`, process-cached `cached_config()`, and
  `clear_config_cache()`.
- **`[submit_keys]` section** lets the operator override the submit
  shortcut per IDE without patching code, e.g.:
  ```toml
  [submit_keys]
  windsurf  = "Return"
  jetbrains = "ctrl+Return"
  fleet     = "alt+Return"   # teach autopilot a new IDE id
  ```
- `injector._submit_key_for(ide)` is the single resolution point —
  consults the config, falls back to built-in defaults defined in
  `config._BUILTIN_SUBMIT_KEYS`. The previous module-level
  `_SUBMIT_KEY` dict in `injector.py` is gone; adding a new editor no
  longer requires a code edit.
- Loader is fail-safe by design: missing file → defaults silently;
  malformed TOML → defaults + one stderr warning (autopilot never
  crashes because of a bad config); non-string values inside
  `[submit_keys]` are ignored individually.
- **Quickstart docs** updated with a "Configuration" section showing
  the TOML schema and override rules
  ([`docs/autopilot-quickstart.md`](docs/autopilot-quickstart.md#configuration)).

**Tests added (11):** missing file → defaults, user keys override,
malformed TOML survives with stderr warning, non-string values
ignored, unrelated sections accepted, `submit_key_for` fallback chain
(3 cases), `XDG_CONFIG_HOME` honoured, `HOME` fallback, `cached_config`
memoisation + cache invalidation.

Full suite: **365 passed, 0 regressions.** Real-world smoke confirms
`XDG_CONFIG_HOME` override loads correctly: `windsurf → ctrl+Return`
(overridden), `jetbrains → ctrl+Return` (default kept), `custom_ide →
alt+Return` (new IDE accepted), `unknown_ide → Return` (fallback).

### Changed — Autopilot refactor pass 4 + Phase 2.1 (VSIX packaging)

- **R6 / CLI dispatch table** — the eight-branch `if/elif` ladder in
  `koru.cli.main` for subcommand routing (`task`, `agent`, `serve`,
  `scan`, `gate`, `queue`, `gc`, `autopilot`) is replaced with a
  single `_SUBCOMMANDS: dict[str, Callable[[list[str]], int]]`.
  Adding a new subcommand is now one line.
- **`TestSubcommandDispatch`** (5 tests + 8 subtests) — table-completeness,
  per-subcommand routing, fall-through to argparse, bare invocation
  doesn't trigger any handler.

#### Added — Phase 2.1: VS Code extension packaging

- **`npm run package`** — produces an installable `.vsix`
  (`koru-autopilot-0.1.0.vsix`, 12.8 KB) via `@vscode/vsce`.
  `vscode:prepublish` runs `npm run compile` automatically.
- **Package metadata** — `repository`, `bugs`, `homepage`, `keywords`.
- **`.vscodeignore`** trims the VSIX to the minimum runtime payload.
- **`LICENSE`** copied from repo root.
- **`plugins/koru-autopilot-vscode/CHANGELOG.md`** added.
- **README** rewritten with VSIX install recipe for Windsurf / VS Code / Cursor.

Verified end-to-end:
```
$ npm run package
   Packaged: koru-autopilot-0.1.0.vsix (8 files, 12.79 KB)
$ windsurf --install-extension koru-autopilot-0.1.0.vsix
   Extension 'koru-autopilot-0.1.0.vsix' was successfully installed.
$ windsurf --list-extensions | grep koru
   semcod.koru-autopilot-vscode
```

Full suite: **370 passed, 0 regressions** (365 → 370).

### Added — Phase 2 wave 2: handoff + audit log + tail (P2.5, P2.7, P2.8)

- **`koru autopilot handoff`** (P2.5) — one-shot "build the koru brief
  for `--project` and type it into the IDE chat". Internally lazy-imports
  `koru.context.build_context` + `render_markdown_handoff`, then calls
  `AutopilotClient.drive`. Flags: `--project`, `--ide`, `--no-submit`,
  `--dry-run`. Returns a JSON summary (`{ok, chars, ide, submit, backend}`).
- **Persistent audit log** (P2.7) — new module
  `src/koru/autopilot/audit.py` ships `AuditLog`, `default_log_path()`,
  rotation constants. Every meaningful event is appended as one
  NDJSON line to `$XDG_STATE_HOME/koru/autopilot.log` (defaults to
  `~/.local/state/koru/autopilot.log`). Rotation at 10 MiB × 5 backups
  via `logging.handlers.RotatingFileHandler`. Permissions locked down
  to `0600` on the file and `0700` on the directory.
- **Events recorded:** `daemon_started`, `daemon_stopped`,
  `plugin_connected`, `drive` (with `ide`/`backend`/`chars`/`submit`/`ok`,
  plus `error` on failure), `handoff` (with `chat`/`reason`/`chars`),
  `shutdown`.
- **`koru autopilot tail`** (P2.8) — pretty-prints the last N audit
  entries. Flags: `-n/--lines` (default 20), `--log` (override path),
  `--format {text,json}`. Text rendering surfaces `ide`, `backend`,
  `chars`, `submit`, `ok`, `chat`, `reason`. JSON dumps the full
  parsed array. Gracefully skips malformed lines.
- **Daemon CLI wiring** — `koru autopilot daemon` now constructs an
  `AuditLog(enabled=True)` by default and prints the log path on
  startup so the operator knows where to look.

**Tests added (18):**
- 10× `tests/test_autopilot_audit.py` — NDJSON shape, `None`-drop,
  file/dir permissions, `XDG_STATE_HOME` honoured, ordering, rotation,
  `enabled=False` no-op, unwritable directory silently disables.
- 8× `tests/test_autopilot_cli.py` — `handoff --dry-run`, daemon-not-running
  guard, happy-path drive forwarding; `tail` text + JSON + `-n` limit +
  missing log + malformed lines.

**Real-world smoke (maintainer's machine):**
```
$ koru autopilot daemon --project ~/github/semcod/koru
   koru autopilot daemon: audit log at /home/tom/.local/state/koru/autopilot.log
   koru autopilot daemon: handoff enabled for project=...
$ koru autopilot handoff --dry-run
   # koru handoff — /home/tom/github/semcod/koru
   ...
$ koru autopilot tail -n 10
   2026-05-11T16:35:55Z  daemon_started  socket=/tmp/...  handoff=True
   2026-05-11T16:36:05Z  drive  ide=windsurf  backend=keyboard  chars=5388  ok=False
```

Full suite: **388 passed, 0 regressions** (370 → 388).

### Added — Phase 2 wave 3: systemd user unit + peercred regression (P2.6, R11)

- **P2.6 / daemon persistence** — shipped
  `systemd/koru-autopilot.service` for `systemd --user` installs:
  `ExecStart=... koru autopilot daemon --idempotent --no-handoff`,
  `Restart=on-failure`, journald wiring, and tightened service sandboxing
  (`NoNewPrivileges`, `ProtectSystem`, `ProtectHome`, `ReadWritePaths`).
- **New CLI action `koru autopilot install-unit`** — writes the user unit
  to `$XDG_CONFIG_HOME/systemd/user/koru-autopilot.service` (or
  `~/.config/systemd/user/` fallback) with flags:
  - `--print` (render only)
  - `--dest <path>` (custom output)
  - `--force` (overwrite existing file)
- **ExecStart path resolution hardened** — the installer now resolves the
  `koru` binary in this order: `PATH` (`shutil.which`), sibling of
  `sys.executable` (virtualenv-friendly), then `sys.prefix/bin/koru`,
  with `%h/.local/bin/koru` as the final fallback.
- **R11 / security regression test** — added a daemon test that
  monkeypatches `_peer_uid` to a foreign UID and asserts the connection
  is closed before any client registration (`SO_PEERCRED` same-UID gate).
- **Docs refreshed:**
  [`docs/autopilot-quickstart.md`](docs/autopilot-quickstart.md) now
  recommends `install-unit` + `systemctl --user` flow; roadmap marks
  **P2.6 ✅** and **R11 ✅**.

**Tests added (5):** 4× `tests/test_autopilot_cli.py`
(`install-unit` print/write/overwrite guard + resolver fallback),
1× `tests/test_autopilot_daemon.py` (`SO_PEERCRED` rejection regression).

Full suite: **393 passed, 8 subtests passed** (388 → 393).

### Changed — Autopilot refactor pass 6: focused-window arbitration (R13)

- **Focused IDE detection (X11)** in `src/koru/autopilot/ide.py`:
  - `_active_window_pid_x11()` probes `xdotool getactivewindow getwindowpid`
    with strict fallbacks (`DISPLAY` missing, xdotool absent, timeout,
    non-numeric output → `None`).
  - `detect_focused_ide_id()` maps active-window PID to autopilot IDE id
    via existing process-signature matching.
  - `focused_ide()` helper resolves focused item from an already detected
    IDE list.
- **Target arbitration update:** `pick_target()` now selects in order:
  1) explicit `--ide` preference, 2) focused IDE (when detectable),
  3) legacy signature-order fallback.
- **CLI visibility** in `src/koru/autopilot/cli_command.py`:
  - `koru autopilot ide-list` marks focused entry with `[focused]`.
  - `koru autopilot doctor --format json` now includes
    `"focused_ide": <id|null>`.
  - text doctor output marks focused IDE in the list.

**Tests added (6):**
- 5× `tests/test_autopilot_ide.py` (focused id detection, helper mapping,
  arbitration precedence).
- 1× `tests/test_autopilot_cli.py` (+ JSON assertion extended) for
  `[focused]` rendering and `focused_ide` field.

Full suite: **399 passed, 8 subtests passed** (393 → 399).

### Added — On-change gates triad (wup + regix + testql)

- **New brief section "On-change gates"** — `render_markdown_handoff()`
  now emits a dedicated table whenever a project has any of the three
  on-change gate packages configured. Detection markers (in
  `agents.detect_project_environment()`):
  - `wup_yaml`         → `wup.yaml` at project root
  - `regix_yaml`       → `regix.yaml` at project root
  - `testql_scenarios` → `testql-testing/scenarios/` or `testql-scenarios/`
  Section lists each gate, whether it's configured, its role, and the
  exact command to invoke it. Skipped silently when none are present
  (no noise for non-adopting projects).
- **New template** `templates/wup.yaml.template` — base file watcher
  config with debounce, gitignore-aware excludes, 2-layer test strategy
  (quick: ≤3 testql endpoints; full: only on quick-fail), and CPU
  throttling. Placeholder `__PROJECT__` substituted by the install task.
- **New install tasks**:
  - `task template:install:wup PROJECT=<name>` — copies wup.yaml
    template, substitutes `__PROJECT__`, prints next-steps (map-deps,
    testql-endpoints, watch).
  - `task template:install:on-change-gates PROJECT=<name>` — composite:
    wup.yaml + regix.yaml + reminder for testql scenarios.
- **New workflow doc** `workflows/on-change-gates.md` — full description
  of the wup→testql→regix cycle with ASCII diagram, package
  responsibilities table, bootstrap recipe, and failure-mode escape
  hatches. Documents the rationale: behaviour probe + metric gate +
  blame report = continuous per-save analogue of `quality:gate`.
- **New slash command** `.windsurf/workflows/koru-gate.md` (`/koru-gate`)
  — read-only manual triad invocation: detect → regix gates → testql
  smoke → wup status → aggregate decision. Used by the agent before
  `planfile ticket complete`.

### Added — Onboarding & diagnostics (Phase 5)
- `koru --init [--from <yaml>] [--force]` — one-command project bootstrap.
  Creates `.planfile/{config.yaml, sprints/current.yaml}`,
  `.planfile/.koru/policy.yaml` (commented stub with safe defaults), and
  appends `.planfile/.koru/` to `.gitignore` (idempotent). Without
  `--from`, generates a 2-ticket starter scaffold (`STARTER-001` shell,
  `STARTER-002` human). Policy stub is never overwritten on `--force`.
- `koru` (no args) — bare invocation now emits the markdown LLM brief
  (`--context --format markdown`). If the project is uninitialised, the
  brief leads with **⚠ Setup required** and the exact `koru --init`
  command. Self-service commands swap to init-only vocabulary until
  the project is bootstrapped.
- `koru --doctor [--format json|text]` — read-only project diagnostics.
  Probes 8 checks: `git_repo`, `planfile_binary`, `planfile_config`,
  `planfile_sprints`, `runtime_dir`, `policy_yaml`, `gitignore`,
  `ci_command`. Exit 1 on failure, 0 on warnings-only. Human-readable
  text by default; `--format json` for machine consumption.
- Pre-flight check in `build_context`: planfile subprocess is skipped
  when the project is uninitialised (prevents planfile from auto-creating
  a half-state `config.yaml`).

### Added — Queue runner (Phases 3.5 / 3.6 / 4)
- `koru --queue --interactive` — when the next runnable ticket is a
  `human` executor, koru collects the answer on stdin (multi-line,
  Ctrl-D submit, Ctrl-C cancel) and completes the ticket via
  `planfile ticket complete` with the answer recorded in `--note` and
  `--result-json`. No more switching to the planfile CLI to satisfy
  human prompts. (`5a28201`)
- `koru --queue --loop --max-iterations N` — drains the queue
  ticket-by-ticket until idle / human input needed (without
  `--interactive`) / unsupported executor / planfile error / cap hit.
  Failed tickets do **not** halt the loop. Live progress is rendered
  with status glyphs (✓/✗/⏸/•). Composes with `--interactive` to
  drain shell + human tickets in one invocation. (`ca90446`)
- `executor.kind=llm` — Phase 4 of the gateway design is live. LLM
  tickets call any OpenAI-compatible chat-completion endpoint
  (default OpenRouter, falls back to OpenAI via `KORU_LLM_ENDPOINT`),
  capture the assistant's text as `stdout`, and embed `llm_model` +
  `llm_usage` (token counts) in the result-json for cost tracking.
  Supports `inputs.{prompt, llm_model, llm_endpoint, system_prompt,
  llm_max_tokens, llm_temperature, response_schema,
  llm_timeout_seconds}` and forwards `KORU_LLM_HTTP_REFERER` /
  `KORU_LLM_X_TITLE` to OpenRouter. Refuses to call without an API
  key (returns a clear, actionable error). (`8858505`)
- `LlmRunResult`, `QueueLoopResult`, `run_planfile_queue_loop` —
  added to the public `koru` package API.
- `docs/cli-examples.md` — three new sections:
  *Answer human-input tickets interactively*,
  *Drain the queue with --loop*,
  *Auto-answer tickets with an LLM (executor.kind=llm)*,
  each with worked PLF-067-style examples and an env-var matrix.
- 14 new unit tests (3 interactive + 6 loop + 5 LLM) +
  1 fix to `test_unsupported_executor_kind` (now uses `mcp` since
  `llm` is supported). Total: **50/50 unit tests + 6/6 smoke e2e +
  9/9 bootstrap e2e**.

### Added — Earlier today
- `docs/llm-tools/sumd/` — dokumentacja + `install.sh` dla `sumd`/`sumr`
  (LLM refactor snapshots). Siódmy tool w matrix.
- `templates/sumr-refresh.sh.template` — debounced wrapper generujący
  `SUMR.md` tylko gdy stale (≥25 commitów lub ≥7 dni).
- `templates/git-hooks/{post-merge,post-commit,install.sh}.template` —
  portable git hooks: branch-aware post-merge (async bg), lightweight
  post-commit (hint-only), idempotentny installer z marker-based
  uninstall.
- `templates/sumr-weekly.yml.template` — GitHub Actions workflow
  (weekly Monday 04:00 UTC + manual dispatch) z PR-botem
  (`peter-evans/create-pull-request@v7`, branch `automation/sumr-refresh`).
- `workflows/sumr-refresh-loop.md` — 3-layer workflow doc z 9-krokowym
  deployment checklistem dla docelowego repo.
- `docs/llm-tools/redeploy/` — dokumentacja + `install.sh` dla `redeploy`
  (multi-target deployment via markpact specs). Ósmy tool w matrix.
- `templates/redeploy/local/deployment.md.template` — local Docker
  Compose markpact spec (dev) z plugin-based testing (process_control,
  http_check, hardware_diagnostic).
- `templates/redeploy/device/{manifest.yaml,migration.md,diagnose.md}.template`
  — multi-phase SSH device deployment: hardware-init / deploy / diagnose
  / detect / fix-* fazy. Podman Quadlet rootless + Docker Compose.
- `workflows/redeploy-multi-device.md` — 9-krokowy deployment checklist
  + multi-device topologie (single device, multi device same strategy,
  multi strategy jak c2004) + drift loop z `doql adopt`.
- `docs/llm-tools/goal/` — dokumentacja + `install.sh` dla `goal`
  (automated git push + smart conventional commits + release workflow).
  Koru ma już `goal.yaml` (510 linii), brakowało doc.
- `docs/llm-tools/doql/` — dokumentacja + `install.sh` dla `doql`
  (declarative IaC, companion sumd/redeploy). Pokrywa `app.doql.less`,
  `doql adopt`, drift detection, format adapters.
- `docs/llm-tools/costs/` — dokumentacja + `install.sh` dla `costs`
  (zero-config AI cost tracker, badge w README.md per commit).
- `docs/llm-tools/op3/` — dokumentacja + `install.sh` dla `op3`
  (layered infra observation: physical/os/runtime/service/endpoint/
  business). Companion redeploy/doql dla deeper device snapshots.
- `docs/llm-tools/README.md` — sekcja **ORCHESTRATION** w mapie warstw
  (goal/doql/costs), 4 nowe wiersze w tabeli config, install loop +=
  goal, doql, costs, op3.

#### Fala 2 — observability + bootstrap
- `templates/observability/` — kompletny stack monitoring:
  - `docker-compose.observability.yml.template` (10 services: prometheus,
    grafana, loki, alertmanager, blackbox, node-exporter, cadvisor,
    promtail, uptime-kuma, healing-webhook)
  - `prometheus/prometheus.yml.template` + `rules/app-alerts.yml.template`
    z generic alert rules (EndpointDown, HighErrorRate, HighMemoryUsage,
    DuplicationCheck, RegressionDetected)
  - `alertmanager/alertmanager.yml.template` z webhook routing
  - `README.md` — index + manual install
- `templates/.windsurf/` — bootstrap dla Windsurf agent:
  - `rules.md.template` (workflow + tool table + anti-patterns +
    citation format)
  - `mcp_config.example.json.template` (3 MCP servers: planfile, testql, redup)
- `templates/github-workflows/{version-drift,code-quality}.yml.template` —
  GH Actions: SSOT version drift check + ruff/lizard/regix/redup/vallm
  quality gate + pytest job.
- `templates/scripts/check-version-drift.sh.template` — Python helper
  validating VERSION ↔ pyproject.toml/package.json/__init__.py/.env
- `templates/.pre-commit-config.yaml.template` — generic hygiene + ruff
  + version-drift gate + regix advisory + redsl-gate (commented)
- `docs/llm-tools/toonic/` — dokumentacja + `install.sh` dla `toonic`
  (universal TOON format converter, LLM-optimized compact YAML).
- `workflows/observability-bootstrap.md` — 9-krokowy deployment
  checklist + alert healing strategies + customization guide +
  troubleshooting.

#### Fala 3 — specialized tools + runtime templates
- `docs/llm-tools/protogate/` — migration tool dla legacy systems
  (bounded slices), built on SUMD + DOQL + testql + Taskfile.
- `docs/llm-tools/rebuild/` — historical deployment analysis +
  code intelligence (git history walker, dashboard at :7821,
  rebuild restore w healing-webhook).
- `docs/llm-tools/mdflow/` — markdown dependency analyzer (extract
  markpact:ref, generate Mermaid diagrams, validate links).
- `docs/llm-tools/metrun/` — execution intelligence + bottleneck
  detection (turn raw cProfile data w actionable fix suggestions).
- `templates/redeploy/runtime/quadlet/` — Podman Quadlet templates
  (rootless systemd) — companion dla redeploy device deployment.
  Pliki: `app-backend.container`, `app-frontend.container`, `app.network`.
- `templates/python-monorepo/shared-compat/` — compatibility shim
  pattern dla monorepo z `packages/<APP>-shared-py/`. Helper z
  `export_backend_shared_module()` + `export_connect_module()`.
  88% size reduction w shim files (na bazie c2004).

### Changed
- `Taskfile.yml` → `install:tools` obejmuje teraz `sumd`, `code2llm`,
  `doql`, `redeploy`, `goal`, `costs`, `op3`, `toonic` (13 narzędzi total).
- `Taskfile.yml` → 5 nowych `template:install:*` tasków
  (observability, windsurf, ci, precommit + already-existing redeploy/sumr).
- `Taskfile.yml` → 8 nowych `monitor:*` tasków (net, up, up:lite, down,
  status, logs, probe, reload-prometheus).
- `README.md` + `docs/llm-tools/README.md` — toonic dodane do list.
- `Taskfile.yml` → nowe taski: `template:install:sumr`,
  `template:install:redeploy`,
  `quality:sumr:{status,auto,refresh,install-hook,uninstall-hook}`,
  `deploy:{plan,dry,local,device,diagnose,resume,drift}`.
- `README.md` + `docs/llm-tools/README.md` — sumd/sumr i redeploy dodane
  do list narzędzi i matrix konfiguracji.

## [0.1.174] - 2026-05-21

### Docs
- Update README.md

### Test
- Update tests/test_autonomous.py
- Update tests/test_autopilot_daemon.py
- Update tests/test_cli.py

### Other
- Update .planfile/config.yaml
- Update .planfile/sprints/current.yaml
- Update uv.lock

## [0.1.173] - 2026-05-21

### Docs
- Update README.md

### Test
- Update tests/test_autonomous.py
- Update tests/test_autopilot_daemon.py
- Update tests/test_scan.py

### Other
- Update .koru/runtime-context.json
- Update .planfile/config.yaml
- Update .planfile/sprints/current.yaml
- Update plugins/koru-autopilot-vscode/out/extension.js
- Update plugins/koru-autopilot-vscode/out/extension.js.map
- Update plugins/koru-autopilot-vscode/package-lock.json
- Update plugins/koru-autopilot-vscode/package.json
- Update plugins/koru-autopilot-vscode/src/extension.ts
- Update uv.lock

## [0.1.172] - 2026-05-21

### Docs
- Update README.md

### Other
- Update uv.lock

## [0.1.171] - 2026-05-21

### Docs
- Update README.md

### Test
- Update tests/test_autopilot_cli.py

### Other
- Update uv.lock

## [0.1.170] - 2026-05-21

### Docs
- Update CHANGELOG.md
- Update README.md
- Update SUMD.md
- Update SUMR.md
- Update TODO.md
- Update docs/IDE_PROTOCOL.md
- Update docs/autopilot-quickstart.md
- Update docs/autopilot-roadmap.md
- Update project/README.md
- Update project/context.md

### Test
- Update tests/test_autopilot_cli.py
- Update tests/test_autopilot_daemon.py
- Update tests/test_drive_orchestrator.py
- Update tests/test_queue_cli_helpers.py

### Other
- Update app.doql.less
- Update planfile.yaml
- Update project/analysis.toon.yaml
- Update project/calls.mmd
- Update project/calls.png
- Update project/calls.toon.yaml
- Update project/calls.yaml
- Update project/compact_flow.mmd
- Update project/compact_flow.png
- Update project/duplication.toon.yaml
- ... and 9 more files

## [0.1.169] - 2026-05-21

### Docs
- Update README.md
- Update SUMD.md
- Update SUMR.md
- Update TODO.md
- Update docs/README.md
- Update docs/autopilot-design.md
- Update docs/autopilot-roadmap.md
- Update project/README.md
- Update project/context.md

### Test
- Update tests/test_doctor.py

### Other
- Update app.doql.less
- Update project/analysis.toon.yaml
- Update project/calls.mmd
- Update project/calls.png
- Update project/calls.toon.yaml
- Update project/calls.yaml
- Update project/compact_flow.mmd
- Update project/compact_flow.png
- Update project/duplication.toon.yaml
- Update project/evolution.toon.yaml
- ... and 8 more files

## [0.1.168] - 2026-05-21

### Docs
- Update CHANGELOG.md
- Update README.md
- Update SUMD.md
- Update SUMR.md
- Update TODO.md
- Update docs/IDE_PROTOCOL.md
- Update docs/autodiagnostics-auto-repair.md
- Update docs/autonomy-ide-cursor.md
- Update docs/autopilot-quickstart.md
- Update docs/local-service.md
- ... and 3 more files

### Test
- Update tests/test_autopilot_daemon.py
- Update tests/test_autopilot_plugin_installer.py
- Update tests/test_drive_orchestrator.py
- Update tests/test_install_manager.py
- Update tests/test_local_service.py
- Update tests/test_planfile_queue.py
- Update tests/test_queue_cli_helpers.py

### Other
- Update .planfile/sprints/current.yaml
- Update app.doql.less
- Update planfile.yaml
- Update project/analysis.toon.yaml
- Update project/calls.mmd
- Update project/calls.png
- Update project/calls.toon.yaml
- Update project/calls.yaml
- Update project/compact_flow.mmd
- Update project/compact_flow.png
- ... and 10 more files

## [0.1.167] - 2026-05-21

### Docs
- Update README.md

### Test
- Update tests/test_autopilot_plugin_installer.py
- Update tests/test_install_manager.py

### Other
- Update uv.lock

## [0.1.166] - 2026-05-21

### Docs
- Update README.md
- Update SUMD.md
- Update SUMR.md
- Update TODO.md
- Update project/context.md

### Test
- Update tests/test_autopilot_daemon.py
- Update tests/test_dashboard_topology_post.py
- Update tests/test_drive_orchestrator.py
- Update tests/test_plugin_router.py
- Update tests/test_runtime_insights.py
- Update tests/test_scan.py

### Other
- Update app.doql.less
- Update plugins/koru-autopilot-vscode/out/extension.js
- Update plugins/koru-autopilot-vscode/out/extension.js.map
- Update plugins/koru-autopilot-vscode/src/extension.ts
- Update plugins/koru-autopilot-vscode/src/probe-ladder.test.ts
- Update plugins/koru-autopilot-vscode/src/probe-ladder.ts
- Update project/analysis.toon.yaml
- Update project/calls.mmd
- Update project/calls.png
- Update project/calls.toon.yaml
- ... and 10 more files

## [0.1.165] - 2026-05-21

### Docs
- Update README.md
- Update SUMD.md
- Update SUMR.md
- Update TODO.md
- Update project/README.md
- Update project/context.md

### Test
- Update tests/test_autonomous.py
- Update tests/test_autonomous_startup.py
- Update tests/test_operator_pipeline.py

### Other
- Update .planfile/config.yaml
- Update .planfile/sprints/current.yaml
- Update app.doql.less
- Update project/analysis.toon.yaml
- Update project/calls.mmd
- Update project/calls.png
- Update project/calls.toon.yaml
- Update project/calls.yaml
- Update project/compact_flow.mmd
- Update project/compact_flow.png
- ... and 10 more files

## [0.1.164] - 2026-05-21

### Docs
- Update README.md

### Test
- Update tests/test_autonomous.py
- Update tests/test_autonomous_startup.py

### Other
- Update uv.lock

## [0.1.163] - 2026-05-21

### Docs
- Update README.md

### Test
- Update tests/test_autopilot_daemon.py

### Other
- Update .planfile/sprints/current.yaml
- Update uv.lock

## [0.1.162] - 2026-05-21

### Docs
- Update README.md

### Test
- Update tests/test_autonomous.py
- Update tests/test_autonomous_startup.py
- Update tests/test_autopilot_cli.py

### Other
- Update .planfile/config.yaml
- Update .planfile/sprints/current.yaml
- Update uv.lock

## [0.1.161] - 2026-05-20

### Docs
- Update CHANGELOG.md
- Update README.md
- Update SUMD.md
- Update SUMR.md
- Update TODO.md
- Update project/README.md
- Update project/context.md

### Test
- Update tests/test_autopilot_cli.py

### Other
- Update app.doql.less
- Update planfile.yaml
- Update project/analysis.toon.yaml
- Update project/calls.mmd
- Update project/calls.png
- Update project/calls.toon.yaml
- Update project/calls.yaml
- Update project/compact_flow.mmd
- Update project/compact_flow.png
- Update project/duplication.toon.yaml
- ... and 9 more files

## [0.1.160] - 2026-05-20

### Docs
- Update CHANGELOG.md
- Update README.md
- Update docs/IDE_PROTOCOL.md
- Update docs/specs/kide-002-koruide-api-v1.md

### Test
- Update tests/test_autonomous_startup.py
- Update tests/test_autopilot_cli.py
- Update tests/test_autopilot_daemon.py

### Other
- Update .planfile/config.yaml
- Update .planfile/sprints/current.yaml
- Update plugins/koru-autopilot-vscode/out/extension.js
- Update plugins/koru-autopilot-vscode/out/extension.js.map
- Update plugins/koru-autopilot-vscode/package-lock.json
- Update plugins/koru-autopilot-vscode/src/extension.ts
- Update uv.lock

## [0.1.159] - 2026-05-20

### Docs
- Update README.md

### Test
- Update tests/test_autopilot_daemon.py
- Update tests/test_autopilot_injector.py

### Other
- Update uv.lock

## [0.1.158] - 2026-05-20

### Docs
- Update README.md
- Update docs/IDE_PROTOCOL.md

### Test
- Update tests/test_autopilot_cli.py
- Update tests/test_autopilot_socket_path.py
- Update tests/test_docs_ide_control_surfaces.py

### Other
- Update prefact.yaml
- Update uv.lock

## [0.1.157] - 2026-05-20

### Docs
- Update CHANGELOG.md
- Update README.md
- Update docs/IDE_PROTOCOL.md
- Update docs/README.md
- Update project/README.md
- Update project/context.md

### Test
- Update tests/test_docs_ide_control_surfaces.py
- Update tests/test_pyproject_metadata.py

### Other
- Update prefact.yaml
- Update project/analysis.toon.yaml
- Update project/calls.mmd
- Update project/calls.png
- Update project/calls.toon.yaml
- Update project/calls.yaml
- Update project/compact_flow.mmd
- Update project/compact_flow.png
- Update project/duplication.toon.yaml
- Update project/evolution.toon.yaml
- ... and 9 more files

## [0.1.156] - 2026-05-19

### Docs
- Update README.md

### Other
- Update scripts/koru-autoloop.sh
- Update src/koru/scripts/koru-autoloop.sh
- Update uv.lock

## [0.1.155] - 2026-05-19

### Docs
- Update README.md

### Test
- Update tests/test_autonomy_env.py

### Other
- Update scripts/koru-autoloop.sh
- Update src/koru/scripts/koru-autoloop.sh
- Update uv.lock

## [0.1.154] - 2026-05-19

### Docs
- Update README.md

### Other
- Update uv.lock

## [0.1.153] - 2026-05-19

### Docs
- Update README.md

### Test
- Update tests/test_autoloop_cli.py
- Update tests/test_autonomy_env.py
- Update tests/test_cli.py

### Other
- Update scripts/koru-autoloop.sh
- Update src/koru/scripts/koru-autoloop.sh
- Update uv.lock

## [0.1.152] - 2026-05-19

### Docs
- Update README.md

### Test
- Update tests/test_cli.py
- Update tests/test_dev_sync.py

### Other
- Update .redup/cache/hash_cache.db
- Update uv.lock

## [0.1.151] - 2026-05-19

### Docs
- Update README.md

### Test
- Update tests/test_mcp_server.py
- Update tests/test_redup_integration.py

### Other
- Update .redup/cache/hash_cache.db
- Update Taskfile.yml
- Update scripts/koru-autoloop.sh
- Update scripts/koru-semcod-gates.sh
- Update uv.lock

## [0.1.150] - 2026-05-19

### Test
- Update tests/test_autonomous_diagnostics.py
- Update tests/test_redup_integration.py

### Other
- Update uv.lock

## [0.1.149] - 2026-05-19

### Docs
- Update SUMD.md
- Update SUMR.md
- Update TODO.md
- Update project/README.md
- Update project/context.md

### Other
- Update app.doql.less
- Update project/analysis.toon.yaml
- Update project/calls.mmd
- Update project/calls.png
- Update project/calls.toon.yaml
- Update project/calls.yaml
- Update project/compact_flow.mmd
- Update project/compact_flow.png
- Update project/duplication.toon.yaml
- Update project/evolution.toon.yaml
- ... and 6 more files

## [0.1.148] - 2026-05-19

### Docs
- Update SUMD.md
- Update SUMR.md
- Update TODO.md
- Update project/README.md
- Update project/context.md

### Other
- Update app.doql.less
- Update plugins/koru-autopilot-vscode/src/extension.ts
- Update project/analysis.toon.yaml
- Update project/calls.mmd
- Update project/calls.png
- Update project/calls.toon.yaml
- Update project/calls.yaml
- Update project/compact_flow.mmd
- Update project/compact_flow.png
- Update project/duplication.toon.yaml
- ... and 9 more files

## [0.1.147] - 2026-05-19

### Docs
- Update SUMD.md
- Update SUMR.md
- Update TODO.md
- Update project/README.md
- Update project/context.md

### Other
- Update app.doql.less
- Update project/analysis.toon.yaml
- Update project/calls.mmd
- Update project/calls.png
- Update project/calls.toon.yaml
- Update project/calls.yaml
- Update project/compact_flow.mmd
- Update project/compact_flow.png
- Update project/duplication.toon.yaml
- Update project/evolution.toon.yaml
- ... and 9 more files

## [0.1.146] - 2026-05-19

### Docs
- Update README.md
- Update SUMD.md
- Update SUMR.md
- Update TODO.md
- Update project/README.md
- Update project/context.md

### Test
- Update tests/test_autonomous.py

### Other
- Update app.doql.less
- Update project/analysis.toon.yaml
- Update project/calls.mmd
- Update project/calls.png
- Update project/calls.toon.yaml
- Update project/calls.yaml
- Update project/compact_flow.mmd
- Update project/compact_flow.png
- Update project/duplication.toon.yaml
- Update project/evolution.toon.yaml
- ... and 8 more files

## [0.1.145] - 2026-05-19

### Docs
- Update README.md
- Update SUMD.md
- Update SUMR.md
- Update TODO.md
- Update project/context.md

### Test
- Update tests/test_activity_log.py
- Update tests/test_agent_cli.py
- Update tests/test_agents.py
- Update tests/test_autonomous.py
- Update tests/test_autonomous_diagnostics.py
- Update tests/test_autonomous_startup.py
- Update tests/test_autonomy_config.py
- Update tests/test_autonomy_environment.py
- Update tests/test_autonomy_prompts.py
- Update tests/test_autopilot_audit.py
- ... and 36 more files

### Other
- Update app.doql.less
- Update project/analysis.toon.yaml
- Update project/calls.mmd
- Update project/calls.toon.yaml
- Update project/calls.yaml
- Update project/compact_flow.mmd
- Update project/compact_flow.png
- Update project/duplication.toon.yaml
- Update project/evolution.toon.yaml
- Update project/flow.mmd
- ... and 3 more files

## [0.1.144] - 2026-05-19

### Docs
- Update README.md
- Update SUMD.md
- Update SUMR.md
- Update TODO.md
- Update project/README.md
- Update project/context.md

### Test
- Update tests/test_autopilot_audit.py
- Update tests/test_planfile_queue.py

### Other
- Update app.doql.less
- Update project/analysis.toon.yaml
- Update project/calls.mmd
- Update project/calls.png
- Update project/calls.toon.yaml
- Update project/calls.yaml
- Update project/compact_flow.mmd
- Update project/compact_flow.png
- Update project/duplication.toon.yaml
- Update project/evolution.toon.yaml
- ... and 7 more files

## [0.1.143] - 2026-05-19

### Docs
- Update README.md
- Update SUMD.md
- Update SUMR.md
- Update TODO.md
- Update project/context.md

### Test
- Update tests/test_autopilot_ide.py
- Update tests/test_e2e.py
- Update tests/test_gc.py
- Update tests/test_queue_clean.py

### Other
- Update app.doql.less
- Update project/analysis.toon.yaml
- Update project/calls.mmd
- Update project/calls.toon.yaml
- Update project/calls.yaml
- Update project/compact_flow.mmd
- Update project/duplication.toon.yaml
- Update project/evolution.toon.yaml
- Update project/flow.mmd
- Update project/map.toon.yaml
- ... and 1 more files

## [0.1.142] - 2026-05-19

### Docs
- Update README.md
- Update SUMD.md
- Update SUMR.md
- Update TODO.md
- Update project/README.md
- Update project/context.md

### Test
- Update tests/test_autonomous.py

### Other
- Update app.doql.less
- Update project/analysis.toon.yaml
- Update project/calls.mmd
- Update project/calls.png
- Update project/calls.toon.yaml
- Update project/calls.yaml
- Update project/compact_flow.mmd
- Update project/compact_flow.png
- Update project/duplication.toon.yaml
- Update project/evolution.toon.yaml
- ... and 5 more files

## [0.1.141] - 2026-05-19

### Docs
- Update SUMD.md
- Update SUMR.md
- Update TODO.md
- Update project/context.md

### Test
- Update tests/test_operator_pipeline.py

### Other
- Update app.doql.less
- Update project/analysis.toon.yaml
- Update project/calls.mmd
- Update project/calls.png
- Update project/calls.toon.yaml
- Update project/calls.yaml
- Update project/duplication.toon.yaml
- Update project/evolution.toon.yaml
- Update project/index.html
- Update project/map.toon.yaml
- ... and 1 more files

## [0.1.140] - 2026-05-19

### Docs
- Update README.md
- Update SUMD.md
- Update SUMR.md
- Update TODO.md
- Update project/README.md
- Update project/context.md

### Other
- Update app.doql.less
- Update project/analysis.toon.yaml
- Update project/calls.mmd
- Update project/calls.png
- Update project/calls.toon.yaml
- Update project/calls.yaml
- Update project/compact_flow.mmd
- Update project/duplication.toon.yaml
- Update project/evolution.toon.yaml
- Update project/flow.mmd
- ... and 7 more files

## [0.1.139] - 2026-05-19

### Docs
- Update README.md
- Update project/context.md

### Test
- Update tests/test_agent_cli.py
- Update tests/test_agents.py
- Update tests/test_autonomous_diagnostics.py
- Update tests/test_autopilot_host_setup.py
- Update tests/test_autopilot_ide.py
- Update tests/test_autopilot_plugin_installer.py
- Update tests/test_bootstrap.py
- Update tests/test_cli.py
- Update tests/test_context.py
- Update tests/test_doctor.py
- ... and 16 more files

### Other
- Update project/analysis.toon.yaml
- Update project/calls.mmd
- Update project/calls.toon.yaml
- Update project/calls.yaml
- Update project/compact_flow.mmd
- Update project/compact_flow.png
- Update project/evolution.toon.yaml
- Update project/flow.mmd
- Update project/flow.png
- Update project/map.toon.yaml
- ... and 2 more files

## [0.1.138] - 2026-05-19

### Docs
- Update README.md

### Other
- Update uv.lock

## [0.1.137] - 2026-05-19

### Docs
- Update README.md
- Update SUMD.md
- Update SUMR.md
- Update TODO.md
- Update project/README.md
- Update project/context.md

### Other
- Update app.doql.less
- Update plugins/koru-autopilot-vscode/src/extension.ts
- Update project/analysis.toon.yaml
- Update project/calls.mmd
- Update project/calls.png
- Update project/calls.toon.yaml
- Update project/calls.yaml
- Update project/compact_flow.mmd
- Update project/compact_flow.png
- Update project/duplication.toon.yaml
- ... and 9 more files

## [0.1.136] - 2026-05-19

### Docs
- Update README.md
- Update SUMD.md
- Update SUMR.md
- Update TODO.md

### Test
- Update tests/test_autopilot_ide.py

### Other
- Update app.doql.less
- Update project/map.toon.yaml
- Update uv.lock

## [0.1.135] - 2026-05-19

### Docs
- Update README.md
- Update project/README.md
- Update project/context.md

### Other
- Update project/analysis.toon.yaml
- Update project/calls.mmd
- Update project/calls.png
- Update project/calls.toon.yaml
- Update project/calls.yaml
- Update project/compact_flow.mmd
- Update project/compact_flow.png
- Update project/duplication.toon.yaml
- Update project/evolution.toon.yaml
- Update project/flow.mmd
- ... and 6 more files

## [0.1.134] - 2026-05-19

### Docs
- Update SUMD.md
- Update SUMR.md
- Update TODO.md
- Update project/README.md
- Update project/context.md

### Other
- Update app.doql.less
- Update project/analysis.toon.yaml
- Update project/calls.mmd
- Update project/calls.png
- Update project/calls.toon.yaml
- Update project/calls.yaml
- Update project/compact_flow.mmd
- Update project/compact_flow.png
- Update project/duplication.toon.yaml
- Update project/evolution.toon.yaml
- ... and 8 more files

## [0.1.133] - 2026-05-19

### Docs
- Update SUMD.md
- Update SUMR.md
- Update TODO.md
- Update project/README.md
- Update project/context.md

### Test
- Update tests/test_autonomous_diagnostics.py

### Other
- Update Taskfile.yml
- Update app.doql.less
- Update project/analysis.toon.yaml
- Update project/calls.mmd
- Update project/calls.png
- Update project/calls.toon.yaml
- Update project/calls.yaml
- Update project/compact_flow.mmd
- Update project/compact_flow.png
- Update project/duplication.toon.yaml
- ... and 9 more files

## [0.1.132] - 2026-05-19

### Docs
- Update SUMD.md
- Update SUMR.md
- Update TODO.md
- Update code2llm_output/README.md
- Update code2llm_output/context.md
- Update project/README.md
- Update project/context.md

### Test
- Update tests/test_autonomous_diagnostics.py
- Update tests/test_autonomous_parser_detection.py
- Update tests/test_dashboard_topology_post.py
- Update tests/test_gc_cli_helpers.py
- Update tests/test_koruapi.py
- Update tests/test_mcp_server.py
- Update tests/test_queue_cli_helpers.py
- Update tests/test_scan.py
- Update tests/test_topology_cli.py

### Other
- Update .redup/cache/hash_cache.db
- Update Taskfile.yml
- Update app.doql.less
- Update code2llm_output/analysis.toon.yaml
- Update code2llm_output/evolution.toon.yaml
- Update code2llm_output/map.toon.yaml
- Update code2llm_output/src_scripts_services/analysis.toon.yaml
- Update project/analysis.toon.yaml
- Update project/batch_1/analysis.toon.yaml
- Update project/calls.mmd
- ... and 16 more files

## [0.1.131] - 2026-05-19

### Docs
- Update CHANGELOG.md
- Update SUMD.md
- Update SUMR.md
- Update TODO.md
- Update project/README.md
- Update project/context.md

### Test
- Update tests/test_operator_pipeline.py

### Other
- Update app.doql.less
- Update planfile.yaml
- Update project/analysis.toon.yaml
- Update project/calls.mmd
- Update project/calls.png
- Update project/calls.toon.yaml
- Update project/calls.yaml
- Update project/compact_flow.mmd
- Update project/compact_flow.png
- Update project/duplication.toon.yaml
- ... and 9 more files

## [0.1.130] - 2026-05-19

### Docs
- Update README.md

### Test
- Update tests/test_autonomous.py
- Update tests/test_autonomy_prompts.py
- Update tests/test_autopilot_daemon.py

### Other
- Update uv.lock

## [0.1.129] - 2026-05-18

### Docs
- Update README.md

### Test
- Update tests/test_autonomous.py

### Other
- Update uv.lock

## [0.1.128] - 2026-05-18

### Docs
- Update README.md

### Test
- Update tests/test_scan.py

### Other
- Update uv.lock

## [0.1.127] - 2026-05-18

### Docs
- Update README.md

### Test
- Update tests/test_planfile_queue.py
- Update tests/test_scan.py

### Other
- Update uv.lock

## [0.1.126] - 2026-05-18

### Docs
- Update README.md

### Test
- Update tests/test_operator_pipeline.py
- Update tests/test_wup_taskfile.py

### Other
- Update .gitignore
- Update .planfile/config.yaml
- Update .planfile/sprints/current.yaml
- Update Taskfile.yml
- Update uv.lock

## [0.1.125] - 2026-05-18

### Docs
- Update README.md

### Other
- Update uv.lock

## [0.1.124] - 2026-05-18

### Docs
- Update README.md
- Update SUMD.md
- Update SUMR.md
- Update TODO.md
- Update docs/autonomy-ide-cursor.md
- Update docs/autopilot-quickstart.md
- Update docs/korudsl-koruapi.md
- Update docs/post-run-verify.md
- Update plugins/koru-autopilot-vscode/CHANGELOG.md
- Update plugins/koru-autopilot-vscode/README.md
- ... and 2 more files

### Test
- Update tests/test_activity_log.py
- Update tests/test_autonomous.py
- Update tests/test_autonomous_startup.py
- Update tests/test_autopilot_cli.py
- Update tests/test_autopilot_daemon.py
- Update tests/test_autopilot_ide.py
- Update tests/test_autopilot_os_injector.py
- Update tests/test_autopilot_plugin_installer.py
- Update tests/test_cli.py
- Update tests/test_ide_work.py
- ... and 5 more files

### Other
- Update .gitignore
- Update .planfile/config.yaml
- Update .planfile/sprints/current.yaml
- Update Taskfile.yml
- Update app.doql.less
- Update koru.yaml
- Update plugins/koru-autopilot-vscode/.gitignore
- Update plugins/koru-autopilot-vscode/.planfile/config.yaml
- Update plugins/koru-autopilot-vscode/.planfile/sprints/current.yaml
- Update plugins/koru-autopilot-vscode/koru.yaml
- ... and 29 more files

## [0.1.123] - 2026-05-17

### Other
- Update plugins/koru-autopilot-vscode/out/extension.js
- Update plugins/koru-autopilot-vscode/out/extension.js.map
- Update uv.lock

## [0.1.122] - 2026-05-17

### Docs
- Update CHANGELOG.md
- Update SUMD.md
- Update SUMR.md
- Update TODO.md
- Update project/README.md
- Update project/context.md

### Test
- Update tests/test_koruide_bridges.py

### Other
- Update .code2llm_cache/agent_backend_runtime_1779019420499000000_5560.pkl
- Update .code2llm_cache/audit_1779028565099000000_4907.pkl
- Update .code2llm_cache/audit_1779028593707000000_207.pkl
- Update .code2llm_cache/autonomous_1779029552973000000_66358.pkl
- Update .code2llm_cache/autonomous_startup_1779028512013606777_6347.pkl
- Update .code2llm_cache/cli_command_1779028599014000000_39861.pkl
- Update .code2llm_cache/client_1779019143082000000_261.pkl
- Update .code2llm_cache/daemon_1779027721508000000_398.pkl
- Update .code2llm_cache/daemon_1779028596470000000_24874.pkl
- Update .code2llm_cache/host_setup_1779029407578000000_6895.pkl
- ... and 30 more files

## [0.1.121] - 2026-05-17

### Docs
- Update README.md

### Test
- Update tests/test_koruide_bridges.py

### Other
- Update uv.lock

## [0.1.120] - 2026-05-17

### Docs
- Update README.md

### Test
- Update tests/test_autonomous.py
- Update tests/test_autonomous_startup.py

### Other
- Update uv.lock

## [0.1.119] - 2026-05-17

### Docs
- Update README.md

### Other
- Update uv.lock

## [0.1.118] - 2026-05-17

### Test
- Update tests/test_autopilot_daemon.py
- Update tests/test_koruide_bridges.py

### Other
- Update uv.lock

## [0.1.117] - 2026-05-17

### Docs
- Update SUMD.md
- Update SUMR.md
- Update TODO.md
- Update project/README.md

### Test
- Update tests/test_ide_runtime.py
- Update tests/test_koruide_bridges.py

### Other
- Update app.doql.less
- Update project/calls.png
- Update project/compact_flow.png
- Update project/duplication.toon.yaml
- Update project/flow.png
- Update project/index.html
- Update project/map.toon.yaml
- Update project/project.toon.yaml
- Update project/prompt.txt
- Update uv.lock

## [0.1.116] - 2026-05-17

### Docs
- Update SUMD.md
- Update SUMR.md
- Update TODO.md
- Update docs/adr/adr-kide-001-koru-vs-koruide-boundary.md
- Update docs/specs/kide-002-koruide-api-v1.md
- Update docs/specs/kide-003-koruide-api-v2.md
- Update project/README.md
- Update project/context.md

### Test
- Update tests/test_autonomous.py
- Update tests/test_ide_client.py
- Update tests/test_ide_client_contract.py
- Update tests/test_ide_runtime.py
- Update tests/test_koruide_client.py
- Update tests/test_mcp_provision.py

### Other
- Update .code2llm_cache/Taskfile_1778838435307206648_31557.pkl
- Update .code2llm_cache/__init___1778944016390000000_256.pkl
- Update .code2llm_cache/agent_backend_runtime_1778943674736000000_5563.pkl
- Update .code2llm_cache/autonomous_1778843854309127812_66635.pkl
- Update .code2llm_cache/autonomous_1778944378166000000_66652.pkl
- Update .code2llm_cache/autonomous_wup_1778943284946034076_8255.pkl
- Update .code2llm_cache/client_1778944305723000000_4100.pkl
- Update .code2llm_cache/daemon_1778944369628000000_277.pkl
- Update .code2llm_cache/dispatch-plan.test_1778844015739898870_3668.pkl
- Update .code2llm_cache/extension_1778839116373289210_17311.pkl
- ... and 29 more files

## [0.1.115] - 2026-05-15

### Docs
- Update README.md

## [0.1.114] - 2026-05-15

### Docs
- Update README.md
- Update SUMD.md
- Update SUMR.md
- Update TODO.md
- Update docs/cli-examples.md
- Update docs/llm-tools/README.md

### Test
- Update tests/test_autonomous.py
- Update tests/test_semcod_tools.py

### Other
- Update Taskfile.yml
- Update app.doql.less
- Update plugins/koru-autopilot-vscode/out/extension.js
- Update plugins/koru-autopilot-vscode/out/extension.js.map
- Update plugins/koru-autopilot-vscode/package-lock.json
- Update plugins/koru-autopilot-vscode/package.json
- Update plugins/koru-autopilot-vscode/src/extension.ts
- Update project/duplication.toon.yaml
- Update project/map.toon.yaml
- Update scripts/koru-semcod-gates.sh
- ... and 1 more files

## [0.1.113] - 2026-05-15

### Docs
- Update README.md
- Update docs/llm-tools/README.md
- Update docs/llm-tools/wup/README.md
- Update project/README.md
- Update project/context.md

### Test
- Update testql-scenarios/generated-cli-tests.testql.toon.yaml
- Update tests/test_autonomous.py
- Update tests/test_autopilot_cli.py
- Update tests/test_autopilot_daemon.py
- Update tests/test_autopilot_plugin_installer.py

### Other
- Update .gitignore
- Update plugins/koru-autopilot-vscode/out/extension.js
- Update plugins/koru-autopilot-vscode/out/extension.js.map
- Update plugins/koru-autopilot-vscode/package-lock.json
- Update plugins/koru-autopilot-vscode/package.json
- Update plugins/koru-autopilot-vscode/src/dispatch-plan.test.ts
- Update plugins/koru-autopilot-vscode/src/extension.ts
- Update plugins/koru-autopilot-vscode/src/socketPath.ts
- Update project/analysis.toon.yaml
- Update project/calls.mmd
- ... and 15 more files

## [0.1.112] - 2026-05-15

### Docs
- Update README.md
- Update docs/autopilot-quickstart.md

### Test
- Update tests/test_autopilot_cli.py
- Update tests/test_autopilot_daemon.py
- Update tests/test_autopilot_ide.py
- Update tests/test_autopilot_injector.py
- Update tests/test_autopilot_os_injector.py
- Update tests/test_cli.py
- Update tests/test_init.py

### Other
- Update .planfile/config.yaml
- Update .planfile/sprints/current.yaml
- Update plugins/koru-autopilot-vscode/out/extension.js
- Update plugins/koru-autopilot-vscode/out/extension.js.map
- Update plugins/koru-autopilot-vscode/package-lock.json
- Update plugins/koru-autopilot-vscode/package.json
- Update plugins/koru-autopilot-vscode/src/extension.ts
- Update plugins/koru-autopilot-vscode/src/socketPath.ts
- Update uv.lock

## [0.1.111] - 2026-05-14

### Docs
- Update README.md

### Test
- Update tests/test_autopilot_os_injector.py

### Other
- Update uv.lock

## [0.1.110] - 2026-05-14

### Docs
- Update README.md

### Other
- Update uv.lock

## [0.1.109] - 2026-05-14

### Docs
- Update README.md
- Update SUMD.md
- Update SUMR.md
- Update TODO.md
- Update docs/autopilot-design.md
- Update plugins/koru-autopilot-vscode/CHANGELOG.md
- Update plugins/koru-autopilot-vscode/README.md
- Update project/README.md
- Update project/context.md

### Test
- Update tests/test_agent_backend_runtime.py
- Update tests/test_autonomous.py
- Update tests/test_autonomous_scenarios.py
- Update tests/test_autonomy_config.py
- Update tests/test_autonomy_env.py
- Update tests/test_cli.py
- Update tests/test_context.py
- Update tests/test_refactor_planfile_handoff.py
- Update tests/test_serve.py

### Other
- Update .gitignore
- Update .planfile/sprints/current.yaml
- Update app.doql.less
- Update plugins/koru-autopilot-vscode/out/extension.js
- Update plugins/koru-autopilot-vscode/out/extension.js.map
- Update plugins/koru-autopilot-vscode/package.json
- Update plugins/koru-autopilot-vscode/src/extension.ts
- Update project/analysis.toon.yaml
- Update project/calls.mmd
- Update project/calls.png
- ... and 15 more files

## [0.1.108] - 2026-05-14

### Docs
- Update README.md

### Other
- Update uv.lock

## [0.1.107] - 2026-05-14

### Docs
- Update README.md

### Test
- Update tests/test_autonomous_scenarios.py
- Update tests/test_autonomy_environment.py
- Update tests/test_cli.py

### Other
- Update uv.lock

## [0.1.106] - 2026-05-14

### Docs
- Update README.md

### Other
- Update uv.lock

## [0.1.105] - 2026-05-14

### Docs
- Update README.md

### Other
- Update uv.lock

## [0.1.104] - 2026-05-14

### Docs
- Update README.md

### Other
- Update uv.lock

## [0.1.103] - 2026-05-14

### Docs
- Update README.md

### Test
- Update tests/test_agent_backend_runtime.py
- Update tests/test_autonomous.py
- Update tests/test_autonomous_scenarios.py
- Update tests/test_autonomy_prompts.py
- Update tests/test_cli.py
- Update tests/test_docker_e2e.py
- Update tests/test_e2e.py

### Other
- Update Taskfile.yml
- Update scripts/koru-queue-diagnose.sh
- Update uv.lock

## [0.1.102] - 2026-05-14

### Docs
- Update README.md

### Test
- Update tests/test_agents.py
- Update tests/test_autonomous_scenarios.py
- Update tests/test_autonomy_config.py

### Other
- Update scripts/koru-autoloop.sh
- Update uv.lock

## [0.1.101] - 2026-05-14

### Docs
- Update README.md
- Update docs/autodiagnostics-auto-repair.md

### Test
- Update tests/test_autonomous.py
- Update tests/test_autonomous_scenarios.py
- Update tests/test_cli.py

### Other
- Update plugins/koru-autopilot-vscode/out/extension.js
- Update plugins/koru-autopilot-vscode/out/extension.js.map
- Update plugins/koru-autopilot-vscode/src/extension.ts
- Update uv.lock

## [0.1.100] - 2026-05-14

### Docs
- Update README.md
- Update docs/README.md
- Update docs/autodiagnostics-auto-repair.md

### Test
- Update tests/test_autonomous_scenarios.py
- Update tests/test_cli.py

### Other
- Update plugins/koru-autopilot-vscode/out/extension.js
- Update plugins/koru-autopilot-vscode/out/extension.js.map
- Update plugins/koru-autopilot-vscode/src/extension.ts
- Update uv.lock

## [0.1.99] - 2026-05-14

### Docs
- Update README.md

### Test
- Update tests/test_autonomous_scenarios.py

### Other
- Update uv.lock

## [0.1.98] - 2026-05-14

### Docs
- Update README.md

### Other
- Update uv.lock

## [0.1.97] - 2026-05-14

### Docs
- Update README.md
- Update docs/agent-backends-architecture.md

### Test
- Update tests/test_agent_backend_runtime.py
- Update tests/test_agent_backends.py

## [0.1.96] - 2026-05-14

### Docs
- Update README.md
- Update docs/mcp-ide-flow.md

### Test
- Update tests/test_autonomous_process_detection.py
- Update tests/test_cli.py
- Update tests/test_mcp_server.py

### Other
- Update plugins/koru-autopilot-vscode/src/extension.ts
- Update uv.lock

## [0.1.95] - 2026-05-14

### Docs
- Update README.md

### Test
- Update tests/test_autopilot_cli.py

### Other
- Update plugins/koru-autopilot-vscode/out/extension.js
- Update plugins/koru-autopilot-vscode/out/extension.js.map

## [0.1.94] - 2026-05-14

### Docs
- Update README.md

## [0.1.93] - 2026-05-14

### Docs
- Update README.md

### Other
- Update uv.lock

## [0.1.92] - 2026-05-14

### Docs
- Update README.md

### Other
- Update uv.lock

## [0.1.91] - 2026-05-14

### Docs
- Update README.md

### Other
- Update uv.lock

## [0.1.90] - 2026-05-14

### Docs
- Update README.md

## [0.1.89] - 2026-05-14

### Docs
- Update README.md
- Update SUMD.md
- Update SUMR.md
- Update TODO.md
- Update project/README.md
- Update project/context.md

### Other
- Update app.doql.less
- Update project/analysis.toon.yaml
- Update project/calls.mmd
- Update project/calls.png
- Update project/calls.toon.yaml
- Update project/calls.yaml
- Update project/compact_flow.mmd
- Update project/compact_flow.png
- Update project/duplication.toon.yaml
- Update project/evolution.toon.yaml
- ... and 7 more files

## [0.1.88] - 2026-05-14

### Docs
- Update README.md

### Other
- Update uv.lock

## [0.1.87] - 2026-05-14

### Docs
- Update .windsurf/workflows/koru-gate.md
- Update README.md

### Test
- Update tests/test_koru_gate_capture.py
- Update tests/test_mcp_provision.py
- Update tests/test_mcp_server.py

### Other
- Update .planfile/config.yaml
- Update .planfile/sprints/current.yaml
- Update scripts/koru-gate-capture.py
- Update templates/.windsurf/mcp_config.example.json.template
- Update uv.lock

## [0.1.86] - 2026-05-14

### Docs
- Update .windsurf/workflows/koru-gate.md
- Update README.md
- Update docs/roadmap-competition.md

### Other
- Update .planfile/config.yaml
- Update .planfile/sprints/current.yaml
- Update examples/ci/gitlab-ci.example.yml
- Update scripts/koru-gate-capture.py
- Update uv.lock

## [0.1.85] - 2026-05-14

### Docs
- Update .windsurf/workflows/koru-gate.md
- Update README.md

### Test
- Update testql-testing/scenarios/realtime-health.testql.toon.yaml

### Other
- Update regix.yaml
- Update uv.lock
- Update wup.yaml

## [0.1.84] - 2026-05-14

### Docs
- Update README.md

### Other
- Update plugins/koru-autopilot-vscode/out/extension.js
- Update plugins/koru-autopilot-vscode/out/extension.js.map
- Update plugins/koru-autopilot-vscode/package.json
- Update plugins/koru-autopilot-vscode/src/dispatch-plan.test.ts
- Update uv.lock

## [0.1.83] - 2026-05-14

### Docs
- Update README.md
- Update examples/README.md
- Update examples/ci/headless-autonomous-jsonl/README.md
- Update examples/planfile/http-api-curl/README.md
- Update examples/planfile/queue-cli-dryrun/README.md
- Update examples/protocol/autopilot-socket-smoke/README.md
- Update examples/runtime/koru-serve-health/README.md

### Test
- Update tests/test_autopilot_daemon.py

### Other
- Update Taskfile.yml
- Update examples/ci/headless-autonomous-jsonl/docker-compose.yml
- Update examples/ci/headless-autonomous-jsonl/e2e.sh
- Update examples/ci/headless-autonomous-jsonl/run-docker.sh
- Update examples/docker/koru-e2e.Dockerfile
- Update examples/planfile/http-api-curl/docker-compose.yml
- Update examples/planfile/http-api-curl/e2e.sh
- Update examples/planfile/http-api-curl/run-docker.sh
- Update examples/planfile/queue-cli-dryrun/docker-compose.yml
- Update examples/planfile/queue-cli-dryrun/e2e.sh
- ... and 13 more files

## [0.1.82] - 2026-05-14

### Docs
- Update README.md
- Update SUMD.md
- Update SUMR.md
- Update TODO.md
- Update project/README.md
- Update project/context.md

### Test
- Update tests/test_autonomous.py
- Update tests/test_init.py

### Other
- Update Taskfile.yml
- Update app.doql.less
- Update examples/docker/koru-e2e.Dockerfile
- Update project/analysis.toon.yaml
- Update project/calls.mmd
- Update project/calls.png
- Update project/calls.toon.yaml
- Update project/calls.yaml
- Update project/compact_flow.mmd
- Update project/compact_flow.png
- ... and 10 more files

## [0.1.81] - 2026-05-14

### Docs
- Update README.md
- Update docs/local-service.md

### Test
- Update tests/test_cli.py
- Update tests/test_local_service.py

### Other
- Update uv.lock

## [0.1.80] - 2026-05-13

### Docs
- Update README.md

### Test
- Update tests/test_stdio_autonomous_jsonl.py

### Other
- Update MANIFEST.in
- Update VERSION
- Update schemas/koru-stdio-event.schema.json
- Update uv.lock

## [0.1.78] - 2026-05-13

### Docs
- Update README.md

### Other
- Update VERSION
- Update uv.lock

## [0.1.29] - 2026-05-11

### Docs
- Update README.md

### Other
- Update uv.lock

## [0.1.28] - 2026-05-11

### Docs
- Update README.md

### Other
- Update uv.lock

## [0.1.27] - 2026-05-11

### Docs
- Update CHANGELOG.md
- Update README.md
- Update docs/autopilot-roadmap.md
- Update docs/cli-examples.md

### Test
- Update tests/test_scan.py

### Other
- Update uv.lock

## [0.1.26] - 2026-05-11

### Docs
- Update README.md

### Test
- Update tests/test_autopilot_cli.py
- Update tests/test_autopilot_ide.py

### Other
- Update uv.lock

## [0.1.25] - 2026-05-11

### Docs
- Update CHANGELOG.md
- Update README.md
- Update SUMD.md
- Update SUMR.md
- Update TODO.md
- Update docs/autopilot-quickstart.md
- Update docs/autopilot-roadmap.md
- Update docs/cli-examples.md
- Update project/README.md
- Update project/context.md

### Test
- Update tests/test_autopilot_cli.py
- Update tests/test_autopilot_daemon.py

### Other
- Update Taskfile.yml
- Update app.doql.less
- Update planfile.yaml
- Update prefact.yaml
- Update project.sh
- Update project/analysis.toon.yaml
- Update project/calls.mmd
- Update project/calls.png
- Update project/calls.toon.yaml
- Update project/calls.yaml
- ... and 14 more files

## [0.1.24] - 2026-05-11

### Docs
- Update CHANGELOG.md
- Update README.md
- Update docs/autopilot-quickstart.md
- Update docs/autopilot-roadmap.md

### Test
- Update tests/test_autopilot_audit.py
- Update tests/test_autopilot_cli.py

### Other
- Update uv.lock

## [0.1.23] - 2026-05-11

### Docs
- Update README.md
- Update docs/autopilot-roadmap.md
- Update plugins/koru-autopilot-vscode/CHANGELOG.md
- Update plugins/koru-autopilot-vscode/README.md

### Test
- Update tests/test_cli.py

### Other
- Update .gitignore
- Update plugins/koru-autopilot-vscode/.gitignore
- Update plugins/koru-autopilot-vscode/.vscodeignore
- Update plugins/koru-autopilot-vscode/LICENSE
- Update plugins/koru-autopilot-vscode/package-lock.json
- Update plugins/koru-autopilot-vscode/package.json
- Update uv.lock

## [0.1.22] - 2026-05-11

### Docs
- Update CHANGELOG.md
- Update README.md
- Update docs/autopilot-quickstart.md
- Update docs/autopilot-roadmap.md

### Test
- Update tests/test_autopilot_config.py
- Update tests/test_autopilot_injector.py

### Other
- Update uv.lock

## [0.1.21] - 2026-05-11

### Docs
- Update CHANGELOG.md
- Update README.md
- Update docs/autopilot-roadmap.md

### Test
- Update tests/test_autopilot_ide.py
- Update tests/test_autopilot_injector.py
- Update tests/test_autopilot_protocol.py

### Other
- Update uv.lock

## [0.1.20] - 2026-05-11

### Docs
- Update CHANGELOG.md
- Update README.md
- Update docs/README.md
- Update docs/autopilot-quickstart.md
- Update docs/autopilot-roadmap.md

### Test
- Update tests/test_autopilot_daemon.py

### Other
- Update .gitignore
- Update plugins/koru-autopilot-vscode/out/extension.js
- Update plugins/koru-autopilot-vscode/out/extension.js.map
- Update plugins/koru-autopilot-vscode/package-lock.json
- Update plugins/koru-autopilot-vscode/src/extension.ts
- Update uv.lock

## [0.1.19] - 2026-05-11

### Docs
- Update README.md

### Other
- Update uv.lock

## [0.1.18] - 2026-05-11

### Docs
- Update README.md

### Test
- Update tests/test_context.py

### Other
- Update uv.lock

## [0.1.17] - 2026-05-11

### Docs
- Update README.md

### Test
- Update tests/test_context.py

### Other
- Update uv.lock

## [0.1.16] - 2026-05-11

### Docs
- Update README.md

### Test
- Update tests/test_e2e.py

### Other
- Update uv.lock

## [0.1.15] - 2026-05-11

### Docs
- Update README.md

### Test
- Update tests/test_context.py

### Other
- Update uv.lock

## [0.1.14] - 2026-05-11

### Docs
- Update README.md

### Other
- Update uv.lock

## [0.1.13] - 2026-05-11

### Docs
- Update README.md

### Other
- Update uv.lock

## [0.1.12] - 2026-05-11

### Docs
- Update README.md

### Test
- Update tests/test_gc.py
- Update tests/test_queue_clean.py

### Other
- Update uv.lock

## [0.1.11] - 2026-05-11

### Docs
- Update README.md
- Update workflows/on-change-gates.md

### Test
- Update tests/test_context.py
- Update tests/test_gate.py

### Other
- Update .planfile/sprints/current.yaml
- Update VERSION
- Update templates/scripts/check-taskfile-escapes.sh.template

## [0.1.11] - 2026-05-11

### Docs
- Update README.md

### Other
- Update uv.lock

## [0.1.10] - 2026-05-11

### Docs
- Update README.md

### Other
- Update uv.lock

## [0.1.9] - 2026-05-11

### Docs
- Update README.md

### Test
- Update tests/test_dotenv_loader.py
- Update tests/test_scan.py

### Other
- Update uv.lock

## [0.1.8] - 2026-05-11

### Docs
- Update README.md

### Test
- Update tests/test_context.py
- Update tests/test_planfile_queue.py
- Update tests/test_serve.py

### Other
- Update .planfile/sprints/current.yaml
- Update uv.lock

## [0.1.7] - 2026-05-11

### Docs
- Update README.md

### Other
- Update uv.lock

## [0.1.6] - 2026-05-11

### Docs
- Update README.md

## [0.1.5] - 2026-05-11

### Docs
- Update .windsurf/workflows/koru-gate.md
- Update CHANGELOG.md
- Update README.md
- Update docs/llm-tools/README.md
- Update workflows/on-change-gates.md

### Other
- Update Taskfile.yml
- Update templates/wup.yaml.template
- Update uv.lock

## [0.1.4] - 2026-05-10

### Docs
- Update README.md

### Test
- Update tests/e2e/init.sh
- Update tests/test_loop.py

### Other
- Update .gitignore
- Update .planfile/config.yaml
- Update .planfile/sprints/current.yaml
- Update pipeline.yaml
- Update uv.lock

## [0.1.3] - 2026-05-10

### Docs
- Update README.md

### Test
- Update tests/test_agents.py
- Update tests/test_runtime.py
- Update tests/test_tasks.py

### Other
- Update uv.lock

## [0.1.2] - 2026-05-10

### Docs
- Update README.md
- Update SUMR.md
- Update docs/llm-tools/README.md
- Update docs/llm-tools/costs/README.md
- Update docs/llm-tools/costs/install.sh
- Update docs/llm-tools/doql/README.md
- Update docs/llm-tools/doql/install.sh
- Update docs/llm-tools/goal/README.md
- Update docs/llm-tools/goal/install.sh
- Update docs/llm-tools/mdflow/README.md
- ... and 27 more files

### Test
- Update testql-scenarios/generated-cli-tests.testql.toon.yaml
- Update testql-scenarios/generated-from-pytests.testql.toon.yaml
- Update tests/test_bootstrap.py
- Update tests/test_watch.py

### Other
- Update .gitignore
- Update .redeployignore
- Update Taskfile.yml
- Update app.doql.less
- Update examples/bootstrap.planfile.yaml.new
- Update project/map.toon.yaml
- Update redeploy/device/manifest.yaml
- Update scripts/git-hooks/install.sh
- Update scripts/git-hooks/post-commit
- Update scripts/git-hooks/post-merge
- ... and 25 more files

## [0.1.1] - 2026-05-10

### Docs
- Update README.md

### Other
- Update .env.example
- Update .idea/.gitignore
- Update .idea/inspectionProfiles/Project_Default.xml
- Update .idea/inspectionProfiles/profiles_settings.xml
- Update .idea/koru-loop.iml
- Update .idea/modules.xml
- Update .idea/pyProjectModel.xml
- Update .idea/vcs.xml
- Update uv.lock
