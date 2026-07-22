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

**Step 1 DONE (2026-07-22)** — VQL sidecar reading is now `vdisplay.vql`:
13 functions (`png_path_for_vql_sidecar`, `main_vql_layer_count`,
`imgl_sidecar_path_for_vql`, `layers_from_imgl_sidecar_file`,
`layers_from_vdisplay_sidecar`, `with_embedded_capture_validation`, the six
`vql_from_*` normalizers and `parse_fresh_vql_elements`), with 29 tests in
vdisplay and thin koru-side wrappers kept for one release cycle. koru keeps
`load_vql_metadata`, `_vql_candidate_is_stale` and `_vql_imgl_fallback_layers`
— those are freshness policy about a run, not facts about a screen.

**The ~60-70% estimate above does not survive measurement.** Counted on the
2026-07-22 tree, `vdisplay_client.py` is 6635 lines across 260 functions, and
the parts that plausibly belong to vdisplay are:

| cluster | lines | status |
|---|---|---|
| VQL sidecar reading | ~130 | moved |
| `photo_vql_target.py` | 525 | **examined — went to koruide, not vdisplay; see below** |
| `photo_vql_monitor.py` | 376 | separate file, not yet examined |
| pointer/coordinate mapping | ~70 | **blocked**, see below |

That totals ~1100 lines, not ~4000. The bulk of the file is drive
orchestration (koru's own) and input actuation (`_type_text_*`,
`_move_mouse_*`), which §2 assigns to **gillm**, not vdisplay — so the
remaining shrink has to come from the gillm move, and this section should
stop promising it.

The pointer/coordinate cluster is blocked on real coupling, not on effort:
`_enrich_capture_meta_for_pointer` calls koru's
`_matching_ide_map_capture_meta`, and `_map_chat_target_capture_local` calls
six koru IDE-map functions (`_ide_prompt_app_id`, `_resolve_ide_prompt_map`,
`_map_chat_input_candidate_keys`, `_map_chat_pointer_meta`,
`_map_chat_bottom_right_target`, `_map_chat_nonnegative_target`). Moving it
means either inverting those into injected callbacks or moving koru's
IDE-map calibration format into vdisplay — a design decision, not a
mechanical extraction.

Two implementation traps worth recording, both hit during step 1:

1. A module-level `from vdisplay import vql` breaks `import koru` wherever
   vdisplay is absent — it is an optional extra, which is exactly why every
   other vdisplay import in that file already sits inside a function body.
2. PEP 562 module `__getattr__` looks like the fix for (1) and is not: it is
   only consulted for `module.attr` access, never for LOAD_GLOBAL inside the
   module itself. The resulting `NameError` was swallowed by the broad
   `except Exception` in `load_vql_metadata`, which then silently returned
   zero `ui_elements` — green imports, wrong data. Use real wrapper
   functions.

**`photo_vql_target.py` had the wrong destination (2026-07-22).** This section
listed it under "vdisplay owns screen truth". Measuring it says otherwise: of
34 functions, **31 (383 lines) are IDE knowledge** — where JetBrains puts its
composer, how a VS Code-family top chat differs from a status bar, what a
plausible input box looks like. None of that is a fact about a screen; all of
it is a fact about an IDE, which is koruide's domain.

Moved to `koruide/chat_target.py`. koru's file went **525 → 79 lines** and is
now a binding layer.

The remaining 3 functions (16 lines) stayed in koru because they describe
*koru*, not any IDE: the vocabularies that recognise koru's own terminal
output inside a capture (`KORU_`, `DRY_RUN`, Polish operator prompts) and
`vql_candidates_polluted`. Rather than let koruide import them, koru registers
them through `set_label_noise_tokens()` — the same injection idiom
`koruide.__init__` already uses for its activity sink. With nothing registered
the penalties are zero, so the module stays usable standalone; verified in a
clean venv with koru absent, where a noisy label's score moved from -730 to
-6730 once tokens were registered.

Tests: 94 passed across the chat-target, photo-VQL drive, koruide-standalone
and IDE-map suites.

**Method note.** Three sections of this document (§1 vdisplay geometry, §2
gillm actuation, and this file) turned out to be mis-specified once measured.
The common error was assigning code by the subsystem it *talks to* rather than
the domain it *knows about*. `photo_vql_target` reads VQL layers, so it looked
like vdisplay's; what it actually encodes is IDE layout. Measure the knowledge,
not the imports.

### 2. gillm owns GUI actuation & recovery — recovery half DONE (2026-07-03)

Failure classification (`classify_plugin/input/environment_failure`) now lives
in `gillm.recovery.diagnose`; koru's `ide_adapters/gillm_recovery.py` keeps
re-export shims plus its gillm-absent fallback copies (that block *is* the
§6 soft-degradation path). Remaining: the input-strategy chain move (blocked
on the vdisplay_client split, STARTER-554/562). Tracked as STARTER-561.

- ~~Input strategy chain from `_type_text_at_vql_coords` (AT-SPI set_value →
  ydotool click → vision click → wl-copy/xclip paste → type → forced) is
  generic input actuation → `gillm.injection.strategies`.~~
  **Re-examined 2026-07-22 and withdrawn as specified.** The chain is 703
  lines across 17 functions, and it is not generic actuation — it is
  cross-provider *orchestration*:

  | step | provider |
  |---|---|
  | ydotool clicks | `vdisplay.input.linux_ydotool.LinuxYdotoolInput` |
  | AT-SPI set_value / click | `vdisplay.control`, or the agent RPC fallback |
  | paste / type | `gillm.injection.injector.Injector` |
  | target resolution, telemetry | koru (`_ide_map_message_target`, `_log_vql_cursor_positioning_at_command`) |

  Moving it into `gillm.injection.strategies` would make **gillm depend on
  vdisplay**, inverting the layering this document exists to fix. gillm
  already owns the generic half — `Injector.type_text`, backend probing,
  `select_backend`, the window guard — and koru is left holding exactly the
  part that decides *which provider to try next and how to prove it worked*.
  That is koru's job, not a boundary violation.

  The cluster also calls 15 sibling functions in `vdisplay_client.py`
  (`_canonical_ide`, `_control_click`, `_control_focus`, `_control_set_value`,
  `_enrich_capture_meta_for_pointer`, `_ide_hints`, `_ide_map_message_target`,
  `_ide_prompt_app_id`, `_log_vql_cursor_positioning_at_command`,
  `_photo_capture_meta_for_source`, `_resolve_ide_prompt_map`,
  `_surface_bounds_target_safe_for_actuation`, `_vdisplay_source_for_ide`,
  `vdisplay_available`, `verify_chat_text_visible`), so there is no mechanical
  cut here either.

  If this is still worth doing, the real question is narrower: should gillm's
  `Injector` grow a *coordinate-targeted* entry point so koru stops driving
  ydotool through vdisplay directly? That is an interface change in gillm, not
  a code move out of koru, and it should be re-specified before anyone starts.
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

### 4. koruide is the single IDE truth — map consolidation DONE (2026-07-03)

- Consolidated (guarded by `tests/test_ide_map_consolidation.py`):
  - `koruide.ide` gained `ide_binary_candidates()` and `ide_window_name()`
    as the single source next to the existing alias map;
  - `autonomy/environment.py`: `KNOWN_IDES` now derives from
    `autopilot_ide_choices()` (jetbrains + antigravity gaps closed; bogus
    `code`/`code-oss` pseudo-ids dropped), binary probe uses koruide;
  - `agent_backend_runtime.py`: window-name map replaced by
    `ide_window_name()`;
  - `mcp_provision.py`: alias dict reduced to a provisioner-compat map
    (`antigravity→vscode`), normalization via koruide;
  - `autopilot/install_plugin_cli.py`: `PLUGIN_IDE_CLI` derives from
    koruide; redundant `PLUGIN_INSTALL_IDE_ALIASES` deleted.
- **Phase 2 DONE (2026-07-03)**: `import koruide` is standalone-safe — hard
  koru/gillm edges inverted (`koruide/host_hooks.py` registry wired from
  `koru/koruide_bridge.py` at daemon start; `env_truthy` inlined; lazy
  `.daemon`/`.config`/`.host_setup` exports; plugin-installer cycle killed
  with bidirectional patch-binding shims). Smoke-tested with koru and gillm
  imports blocked (`tests/test_koruide_standalone_import.py`).
- **Phase 1 DONE (2026-07-22)**: koruide moved to `packages/koruide/src/`
  with its own `pyproject.toml` (name `koruide`, version 0.1.0, single
  dependency `gillm>=0.1.23`). Proven to be a distribution and not merely a
  directory: built and installed into a clean venv **with koru absent**,
  where `import koruide`, `koruide.ide`, `koruide.plugin_installer` and
  `koruide.protocol` all work while `koruide.daemon` stays unimported until
  touched. koru's full suite: 3523 passed / 0 failed. The move flushed out
  four stale path references — both inventory YAMLs, the interface registry
  (symlinked into `koru/data/`) and `docs/IDE_PROTOCOL.md` — now corrected.
  koru keeps bundling the package through `packages.find`, so nothing
  downstream breaks; that path is removed when 0.1.0 ships.
- Still open (STARTER-563 phases 3-5): publish 0.1.0, add `koruide>=0.1.0`
  to koru's dependencies, then drop `packages/koruide/src` from koru's
  `packages.find` — full plan in the ticket.

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
3. ~~koruide alias-map consolidation~~ — **DONE 2026-07-03** (see §4);
   publishing koruide as its own distribution remains open.
4. gillm recovery/strategies move.
5. vdisplay VQL/geometry/monitors move (largest; after 1-4 the remaining
   `vdisplay_client.py` is orchestration-only).

Risks: cross-repo version skew (mitigate: `koru doctor` reports dep
versions; contract tests in each dep pinned in koru CI); the helpers being
moved are exactly the ones tests monkeypatch — keep koru-side re-export
shims for one release cycle.
