# koru autopilot — JetBrains plugin (stub)

> **Status:** scaffolding only. Phase 3 of the autopilot rollout.

The JetBrains plugin will mirror the VS Code extension: connect to
`$XDG_RUNTIME_DIR/koru-autopilot.sock`, send a `hello`, and translate
the IDE's chat lifecycle into `session.*` events.

## Tooling skeleton

```
plugins/koru-autopilot-jetbrains/
├── README.md                          ← this file
├── build.gradle.kts                   ← (to add) IntelliJ Platform plugin
├── gradle.properties                  ← (to add) platform version
└── src/main/kotlin/com/semcod/koru/
    ├── KoruAutopilotService.kt        ← (to add) socket bridge
    └── ChatInjector.kt                ← (to add) AI Assistant API hook
```

## Why is this only a stub?

The JetBrains AI Assistant API is still moving; we don't want to ship
a Kotlin extension that bit-rots between IDE versions. Until the
extension exists, JetBrains users get keyboard-simulation fallback
via `ydotool` / `xdotool`, which is still good enough for the MVP
described in the design doc.

## Wire protocol

Identical to the VS Code extension — see
[`docs/autopilot-design.md`](../../docs/autopilot-design.md#wire-protocol).
