# koru autopilot — JetBrains plugin

> **Status:** Gradle / IntelliJ Platform scaffold with a unix-socket bridge
> and experimental AI Assistant chat injection.

The JetBrains plugin mirrors the first layer of the VS Code extension:
connect to the koru autopilot daemon unix socket, send a `hello` frame,
listen for `chat.send`, and attempt to paste/submit into JetBrains AI
Assistant. Chat control is still experimental because JetBrains does not
provide the same stable chat command surface as VS Code-family IDEs.

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
    └── ChatInjector.kt                ← AI Assistant action + Robot injector
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
- sends a `hello` frame with `ide=jetbrains`, protocol version, and
  chat capabilities;
- listens for daemon `chat.send` frames;
- opens JetBrains AI Assistant via known action ids, pastes through the
  system clipboard, and submits with Ctrl+Enter;
- emits an ACK with paste/submit route evidence plus a `message.sent`
  event when the local injection attempt succeeds;
- exposes **Tools → Reconnect koru Autopilot** for manual reconnect.

Remaining lifecycle work:

- emit real `session.ended` once JetBrains exposes a stable lifecycle hook
  or a polling fallback is implemented;
- add a smoke test that validates Kotlin client frames against the Python
  daemon.
