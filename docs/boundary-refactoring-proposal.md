# Boundary refactoring — slim koru, specialized dependencies

Status: proposal (2026-07-03). Grounded in: the c2004 field incident (silent
lane misroute + missing deps in a project venv), the CC-cleanup waves that
brought `vdisplay_client.py` from CC≤84 to CC≤14, and the 36 remaining
module-level MI hard-gate violations.

## Problem

koru embeds large generic subsystems that belong to its dependencies:

| Area in koru | Size | Actually belongs to |
|---|---|---|
| `integrations/vdisplay_client.py` | ~6.3k lines | vdisplay (VQL parsing, pointer math, actuation) |
| `integrations/photo_vql_{target,guard,monitor}.py` | ~1.5k lines | vdisplay (geometry, monitor topology) |
| `ide_adapters/gillm_{client,recovery}.py` + os-injector wrappers | ~700 lines | gillm (driver stubs, failure classification) |
| `tillm_bridge.py` fallback token/CLI lists | dup of tillm registry | tillm |
| IDE alias maps ×4 (`mcp_provision`, `autonomy/environment`, `agent_backend_runtime`, koruide) | drift-prone | koruide (single source) |

Consequences observed in production (c2004, 2026-07-02/03):
- `koru -a --ide claude` with no tillm in the venv silently drove the
  **vscode** GUI lane instead: 45 `drive_failed` blockers
  (`chat_input_not_empty`, `plugin_version_mismatch`), 1581 `tasks.reused`
  vs **1** `task_completed`.
- `KORU_PLANFILE_CMD=.venv/bin/python -m planfile.cli` with no planfile in
  the venv: 28 `planfile_queue.tick_error`.
- Deployment requires 4+ sibling packages in exactly the right env; nothing
  verifies this up front.

## Target architecture

koru core = autonomy loop + planfile queue + event store + `AgentBackend`
protocol + operator UX. Everything device/IDE/LLM-client-specific lives in
the dependency that owns the domain.

### 1. vdisplay owns screen truth (biggest win)

Move, as `vdisplay.vql` / `vdisplay.geometry` / `vdisplay.monitors`:
- VQL sidecar parsing: `load_vql_metadata` + `_vql_*` helpers,
  `_parse_fresh_vql_elements`, `_layers_from_*_sidecar`.
- Pointer/coordinate math: `_enrich_capture_meta_for_pointer`,
  `_map_chat_target_capture_local`, `photo_vql_target` geometry
  (`_global_to_capture_local_for_source`, monitor rect mapping).
- Monitor topology: `photo_vql_monitor` equivalence/candidate-ordering.

koru keeps: drive orchestration (`prepare_photo_vql_for_drive`,
`perform_photo_vql_focus_and_edit`), capture-guard *policy*, autonomy-session
persistence, operator hints. The CC waves already grouped the movable code
into `_`-prefixed helper clusters — the move is now mostly mechanical.
Expected effect: `vdisplay_client.py` shrinks ~60-70%, killing most of the
36 MI hard violations.

### 2. gillm owns GUI actuation & recovery

- Input strategy chain from `_type_text_at_vql_coords` (AT-SPI set_value →
  ydotool click → vision click → wl-copy/xclip paste → type → forced) is
  generic input actuation → `gillm.injection.strategies`.
- Failure classification in `gillm_recovery._classify_failure` (plugin /
  input / environment) → `gillm.recovery`; koru keeps only the mapping to
  operator guidance and tickets.
- The in-file stub classes in `gillm_client.py` (when gillm is absent) →
  gillm ships a `gillm-stub` contract or koru keeps only the soft-degradation
  shims added 2026-07-03.

### 3. tillm owns the shell-client registry — DONE (2026-07-03, no split needed)

tillm turned out to already be zero-dependency (~250 KB, stdlib only), so the
planned `tillm-core` split was unnecessary. Implemented instead:

- `tillm>=0.1.35` promoted to a **core dependency** of koru — `--ide claude`
  can no longer silently fall through to an editor lane on a fresh install.
- The two koru-side fallback lists stay (resilience for broken envs) but are
  now **drift-guarded by contract tests**
  (`tests/test_tillm_registry_contract.py`): every tillm registry id must be
  in `_FALLBACK_SHELL_CLIENT_TOKENS` and in the `--ide` parser choices, and
  dashboard fallback binaries must match the registry specs' `commands`.
  First run immediately caught a real gap (`cline` missing from parser and
  fallbacks — now added).
- `ensure_local_tillm_path()` / `KORU_TILLM_PATH` remain as dev-checkout
  escape hatches only.

### 4. koruide is the single IDE truth

- Publish `koruide` as its own distribution (it is already a separate
  top-level package in this repo).
- Consolidate into it the four alias/window/binary maps:
  `mcp_provision` aliases, `autonomy/environment.KNOWN_IDES` (+ jetbrains,
  antigravity gaps), `agent_backend_runtime` window-name map.

### 5. planfile invocation hardening

`KORU_PLANFILE_CMD` / project-venv `python -m planfile.cli` must fall back
to `planfile` on PATH (with one warning) when the module is missing —
the c2004 queue died on this exact gap.

### 6. Packaging: extras + doctor

```
koru                → core loop, queue, events, backend protocol (deps: planfile-client, tillm-core, pyyaml, rich)
koru[shell]         → + tillm            (drive claude/aider/codex headlessly)
koru[gui]           → + gillm, vdisplay  (photo-VQL / GUI takeover)
koru[ide]           → + koruide plugin lane assets
koru[api]           → dashboard/API (exists)
```

The soft-degradation shims (gillm import guards, tillm bridge) added
2026-07-03 make these extras real: core imports everywhere. `koru doctor`
(and autonomous startup) must then verify the *selected lane's* extra and
fail with `pip install 'koru[shell]'`-style guidance — the c2004 misroute
becomes impossible (the loud-guard added 2026-07-03 already aborts; doctor
makes it preventive).

## Migration order (each step shippable)

1. ~~planfile-cmd PATH fallback + lane-deps check in doctor~~ — **DONE
   2026-07-03** (`queue/ticket.py` pin validation + warn-once fallback;
   `doctor` probes `planfile_binary` hardened and new `lane_dependencies`).
2. ~~tillm registry as single source~~ — **DONE 2026-07-03** (core dep +
   contract tests instead of a package split; see §3).
3. koruide → own distribution; alias-map consolidation.
4. gillm recovery/strategies move.
5. vdisplay VQL/geometry/monitors move (largest; after 1-4 the remaining
   `vdisplay_client.py` is orchestration-only).

Risks: cross-repo version skew (mitigate: `koru doctor` reports dep
versions; contract tests in each dep pinned in koru CI); the helpers being
moved are exactly the ones tests monkeypatch — keep koru-side re-export
shims for one release cycle.
