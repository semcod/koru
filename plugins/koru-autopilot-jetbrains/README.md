# koru autopilot — JetBrains plugin

> **Status:** Gradle / IntelliJ Platform scaffold with a minimal unix-socket
> bridge. Chat injection and AI Assistant lifecycle hooks remain Phase 3 work.

The JetBrains plugin mirrors the first layer of the VS Code extension:
connect to the koru autopilot daemon unix socket and send a `hello`
frame. It deliberately does not pretend to control JetBrains AI Assistant
yet; that code is isolated behind `ChatInjector.kt` until a stable API or
polling fallback is selected.

## Layout

```
plugins/koru-autopilot-jetbrains/
├── README.md
├── build.gradle.kts                   ← IntelliJ Platform Gradle Plugin 2.x
├── gradle.properties                  ← platform + plugin compatibility
├── settings.gradle.kts                ← plugin repositories
├── src/main/resources/META-INF/
│   └── plugin.xml                     ← application service + reconnect action
└── src/main/kotlin/com/semcod/koru/
    ├── KoruAutopilotService.kt        ← same-UID unix-socket bridge
    ├── SocketPath.kt                  ← KORU_AUTOPILOT_* socket resolution
    ├── KoruAutopilotReconnectAction.kt
    └── ChatInjector.kt                ← AI Assistant hook placeholder
```

## Build

```bash
cd plugins/koru-autopilot-jetbrains
gradle buildPlugin
```

The repository does not vendor a Gradle wrapper for this plugin yet. Use
a local Gradle installation compatible with the IntelliJ Platform Gradle
Plugin 2.x line.

## Wire protocol

Identical to the VS Code extension — see
[`docs/autopilot-design.md`](../../docs/autopilot-design.md#wire-protocol).

Current bridge behavior:

- resolves the socket using `KORU_AUTOPILOT_SOCKET`,
  `KORU_AUTOPILOT_INSTANCE`, `XDG_RUNTIME_DIR`, and `/tmp` fallback rules;
- sends a `hello` frame with `ide=jetbrains`;
- exposes **Tools → Reconnect koru Autopilot** for manual reconnect.

Remaining Phase 3 work:

- listen for daemon `chat.send` frames and paste/submit into AI Assistant;
- emit real `session.ended` once JetBrains exposes a stable lifecycle hook
  or a polling fallback is implemented;
- add a smoke test that validates Kotlin client frames against the Python
  daemon.
