# Per-IDE strategy contract (Python + TypeScript)

## Goal

Until now, Koru kept all IDE-specific knowledge (Cursor, VS Code, VSCodium,
Windsurf, Antigravity, JetBrains, Zed) entangled in a small number of
"hub" files. A single `if ide === "cursor"` lived next to logic that ran
for VSCodium and Windsurf, so a fix for one IDE could (and did) cause
regressions in the others.

The **per-IDE strategy contract** splits that knowledge into one module
per IDE so:

- changes for Cursor stay in `src/koruide/ides/cursor.py` (Python) and
  `plugins/koru-autopilot-vscode/src/ides/cursor.ts` (TypeScript);
- a regression in Cursor cannot reach VSCodium / Windsurf / etc.;
- adding a new IDE means adding one module and one test file, not editing
  seven hubs.

The migration is **incremental**. Today Cursor lives in its own module
(proof of concept). VSCodium, Windsurf, Antigravity, JetBrains, Zed
still use the legacy hub code; one ticket per IDE will move them.

## Python contract: `koruide.ides.IdeStrategy`

```python
from koruide.ides import get_strategy, IdeStrategy

strategy: IdeStrategy | None = get_strategy("cursor")
if strategy is not None:
    strategy.id                # "cursor"
    strategy.label             # "Cursor"
    strategy.detection         # DetectionSignature (proc comm patterns)
    strategy.terminal          # TerminalSignature (env / parent-chain hints)
    strategy.aliases           # IdeAliases (extra normalize_ide_id inputs)
    strategy.config_home()     # ~/.config/Cursor
    strategy.workspace_settings_path(project)   # <proj>/.cursor/settings.json
    strategy.state_vscdb_path()                 # User/globalStorage/state.vscdb
    strategy.extensions_metadata_path()         # ~/.cursor/extensions/extensions.json
    strategy.plugin                              # PluginPolicy
    strategy.keyboard                            # KeyboardPolicy
    strategy.editor_cli_candidates()             # ("cursor",)
    strategy.window_name_hints()                 # ("Cursor",)
```

A strategy is a **plain Python object with no mutable global state**. It
registers itself on import via `register_strategy()`. The registry is
import-light so loading it does not pull adapter or daemon code.

The hubs delegate when a strategy is present and fall back to the
historical dict-driven layout otherwise. The current delegation points
are:

- `src/koru/ide_adapters/shared.py`: `config_home_for_ide`,
  `user_settings_path`, `workspace_settings_path`, `fix_workspace_socket`,
  `extension_metadata_path`.
- `src/koru/ide_adapters/registry.py`: VSCode-family adapter for Cursor is
  built from `CursorStrategy`'s plugin policy so the trusted-publisher
  flag cannot drift between strategy and adapter.
- `src/koru/ide_adapters/ide_reload.py`: `_window_name_hints`,
  `_editor_cli_candidates`.

## TypeScript contract: `IdeStrategy`

```typescript
import { getStrategy } from "./ides/registry";

const strategy = getStrategy(ide);
if (strategy !== undefined) {
  strategy.detectIde(appName);                // "cursor" or undefined
  strategy.pasteDirectCommandsPrefix();       // before generic paste
  strategy.submitCommandsOverride();          // full submit list or null
  strategy.focusInputCommandsPrefix();        // before generic focus
  strategy.preferCtrlSubmit();                // Cursor: true
  strategy.sanitizeProbeCache(entry, opts);   // discard poisoned wins
  strategy.submitFallback.refuseTypeNewlineFallback;
}
```

The probe-ladder helpers (`buildPasteDirectCommands`,
`buildSubmitCommands`, `buildHostKeySubmitCandidates`,
`sanitizeProbeCacheForIde`) check the registry first; only when the IDE
has no dedicated module do they fall back to the legacy branches.

## Test layout

- **Python**: `tests/ides/test_<ide>_strategy.py` exercises the strategy
  contract in isolation. It must NOT import `koru.autonomous_cycle`, the
  daemon, or other IDEs' modules.
- **TypeScript**: `plugins/koru-autopilot-vscode/src/ides/<ide>.test.ts`
  follows the same isolation rule. Each test file ends with a
  `console.log("<ide>-strategy tests: ok")` line and the file is added to
  the `test` script in `package.json`.

## Adding a new IDE

1. Create `src/koruide/ides/<ide>.py` extending `IdeStrategy`.
2. Add `<ide>.test.py` under `tests/ides/`.
3. Register the module name in `_bootstrap_default_strategies()` inside
   `src/koruide/ides/registry.py`.
4. Remove the legacy dict entries (`_LEGACY_CONFIG_DIRS`,
   `_LEGACY_VSCODE_WORKSPACE_IDES`, `_LEGACY_EXTENSIONS_DIRNAME`,
   `_LEGACY_WINDOW_NAME_HINTS`, `_LEGACY_EDITOR_CLI`) for that IDE.
5. Mirror the same steps for TypeScript under
   `plugins/koru-autopilot-vscode/src/ides/`.
6. Update `docs/ide-strategy-contract.md` if the contract grew.

## Why this is the right shape

- **No shared mutable state per IDE.** Module-level caches in
  `koruide.ide` still exist but per-IDE knowledge is moved out.
- **One file per IDE.** Adding/editing an IDE no longer requires touching
  seven files in two languages.
- **Test isolation.** Per-IDE test suites cannot be broken by changes to
  another IDE's module.
- **Backward compatible.** The legacy hubs keep working for IDEs that
  have not been extracted yet — the migration is incremental, not
  big-bang.

## Status

| IDE         | Python strategy | TS strategy | Legacy hub still used |
|-------------|-----------------|-------------|------------------------|
| cursor      | ✅              | ✅          | no                     |
| vscode      | ✅              | ✅          | no                     |
| vscodium    | ✅              | ✅          | no                     |
| windsurf    | ✅              | ✅          | no                     |
| antigravity | ✅              | ✅          | no                     |
| jetbrains   | ✅              | n/a (no VSIX) | no                   |
| zed         | ✅              | n/a (no VSIX) | no                   |

`koruide.ide` detection tables (`_IDE_SIGNATURES`, `_IDE_ALIASES`) remain
the process-scan source of truth until a later pass wires them through
strategy objects directly.
