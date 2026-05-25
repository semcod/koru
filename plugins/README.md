# koru autopilot — IDE plugins

Each IDE has its own VSIX package. A regression in one plugin's focus /
paste / submit pipeline cannot leak into another IDE.

| Plugin | IDE | Extension ID | Status |
|--------|-----|--------------|--------|
| `koru-autopilot-cursor/` | Cursor | `semcod.koru-autopilot-cursor` | live |
| `koru-autopilot-vscode/` | VS Code | `semcod.koru-autopilot-vscode` | live |
| `koru-autopilot-vscodium/` | VSCodium | `semcod.koru-autopilot-vscodium` | live |
| `koru-autopilot-windsurf/` | Windsurf | `semcod.koru-autopilot-windsurf` | live |
| `koru-autopilot-antigravity/` | Antigravity | `semcod.koru-autopilot-antigravity` | live |
| `koru-autopilot-jetbrains/` | IntelliJ family | (gradle plugin) | scaffold |

## Build all plugins

```bash
npm run sync-shared          # copy shared utilities into each plugin
npm run test:all             # compile + run per-IDE tests
npm run package:all          # build every VSIX
```

Or a single plugin:

```bash
cd plugins/koru-autopilot-cursor && npm run package
```

## Migration from legacy umbrella VSIX

If your IDE still has `semcod.koru-autopilot-vscode` installed alongside
the new dedicated build, uninstall the legacy one:

```bash
cursor --uninstall-extension semcod.koru-autopilot-vscode
cursor --install-extension plugins/koru-autopilot-cursor/koru-autopilot-cursor-*.vsix
```

`koru up` and `koru autopilot install-plugin` pick the correct VSIX
for the detected IDE automatically.

## Shared utilities

Stable IDE-agnostic helpers live in `plugins/koru-autopilot-shared/`
and are copied into each plugin's `src/_shared/` at prebuild via
`scripts/sync-plugin-shared.py`.

## Wire protocol

See [`docs/autopilot-design.md`](../docs/autopilot-design.md#wire-protocol).
