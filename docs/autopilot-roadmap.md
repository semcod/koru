# koru autopilot — roadmap & refactor backlog

> Companion to [`autopilot-design.md`](./autopilot-design.md) and
> [`autopilot-quickstart.md`](./autopilot-quickstart.md). Tracks what is
> shipped (Phase 1) and what remains. Items are scoped so each one is
> a single planfile ticket. Polish gap analysis vs Cursor IDE:
> [`autonomy-ide-cursor.md`](./autonomy-ide-cursor.md).
>
> Status legend: ✅ done · 🟡 in progress · ⬜ planned · ❄ frozen / out of scope.

---

## Phase 1 — terminal-side broker + minimal plugin (shipped)

| #     | Item                                                                                    | Status |
|-------|-----------------------------------------------------------------------------------------|--------|
| P1.1  | Wire protocol (`src/koru/autopilot/protocol.py`) — NDJSON, 1 MiB cap, type whitelist    | ✅     |
| P1.2  | Unix-socket daemon with `SO_PEERCRED` UID check, `0600` perms                           | ✅     |
| P1.3  | Selector-based event loop, idempotent socket cleanup                                    | ✅     |
| P1.4  | Keyboard-sim injector (`xdotool` / `wtype` / `ydotool`) with session autodetection      | ✅     |
| P1.5  | IDE process scan via `/proc` (Windsurf, VS Code, Cursor, JetBrains, Zed)                | ✅     |
| P1.6  | CLI verbs: `daemon`, `drive`, `status`, `shutdown`, `ide-list`, `doctor`                | ✅     |
| P1.7  | Daemon-side auto-handoff when a client emits `session.ended`, with `--handoff-cooldown` anti-loop | ✅     |
| P1.8  | VS Code extension shell (TypeScript, paste-and-submit, status bar, reconnect; lifecycle hook remains P2.3) | ✅     |
| P1.9  | 53 unit + integration tests (`tests/test_autopilot_*.py`)                               | ✅     |
| P1.10 | Quickstart + design doc + roadmap                                                       | ✅     |

---

## Phase 2 — make the plugin path the default

Goal: every koru user has the VS Code extension installed and the
keyboard-sim fallback is only the safety net for headless / non-VS-Code
contexts.

| #     | Item                                                                                                                                                                                                                                                                                                                | Effort | Risk  |
|-------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|--------|-------|
| P2.1 ✅ | **Compile, package, and install the VS Code extension as a `.vsix`.** Done: `npm run package` produces the bundled VSIX and `koru autopilot manage --ide <id> --fix` resolves the current package, reasserts the install through the IDE CLI, writes the socket setting, and reports `connected/version`, `installed`, and `expected`.                                                                                                                                                | S      | low   |
| P2.2  | **Auto-publish the VSIX as a GitHub release asset** on every koru tag. Workflow under `.github/workflows/release-vsix.yml`.                                                                                                                                                                                          | S      | low   |
| P2.3  | **Emit real `session.ended` from the VS Code extension.** Currently we connect & paste; we don't hook the chat lifecycle yet. Use `vscode.chat.onDidEndSession` (Copilot Chat ≥ 1.93) and the Cascade-specific event in Windsurf (TBD via reverse-eng or extension API request).                                    | M      | med   |
| P2.4  | **Capture the LLM reply text** (read-side). Phase 4 in the design doc — pulled forward to Phase 2 because it unblocks the closed loop. Requires reading from the chat document via `vscode.workspace.openTextDocument(chatUri)` or similar.                                                                          | L      | high  |
| P2.5 ✅ | ~~**Plugin-side `koru autopilot handoff` shortcut.**~~ Done: new `handoff` action builds the koru brief via `koru.context.build_context` and pipes through `client.drive`. Supports `--project`, `--ide`, `--no-submit`, `--dry-run`.                                                                              | S      | low   |
| P2.6 ✅ | ~~**systemd `--user` unit**~~ Done: shipped `systemd/koru-autopilot.service` plus `koru autopilot install-unit` (`--print`, `--force`, `--dest`), with next-step hints for `systemctl --user daemon-reload`, `enable --now`, and `journalctl --user`.                                                                                                                                                | S      | low   |
| P2.7 ✅ | ~~**Persistent audit log**~~ Done: NDJSON log at `$XDG_STATE_HOME/koru/autopilot.log` (defaults to `~/.local/state/koru/autopilot.log`), `0600` file / `0700` directory, rotated at 10 MiB with 5 backups via `RotatingFileHandler`. Events: `daemon_started`, `daemon_stopped`, `plugin_connected`, `drive`, `handoff`, `shutdown`. | S      | low   |
| P2.8 ✅ | ~~**`koru autopilot tail`** subcommand that streams the audit log.~~ Done: text + JSON output, `-n` limit, graceful handling of missing files and malformed lines.                                                                                                                                                  | S      | low   |
| P2.9 ✅ | **Plugin install manager + version drift policy.** Done: `koru autopilot manage` inventories PATH/repo koru, package version, socket, daemon, installed extension version, connected runtime version, and expected VSIX version. `KORU_STRICT_PLUGIN_VERSION=1` blocks `drive` through stale live plugins. | M      | med   |

---

## Phase 3 — JetBrains parity

Goal: PyCharm / IntelliJ / WebStorm users get the same plugin
experience as VS Code users.

| #     | Item                                                                                                                                                                                                       | Effort | Risk |
|-------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|--------|------|
| P3.1 ✅ | ~~Replace `plugins/koru-autopilot-jetbrains/README.md` stub with a real Gradle / IntelliJ-Platform plugin skeleton (`build.gradle.kts`, `plugin.xml`).~~ Done: Gradle scaffold, plugin metadata, application service, socket path helper, reconnect action.                                                       | M      | low  |
| P3.2  | Unix-socket bridge in Kotlin (parity with the TS extension): `hello`, listen for `chat.send`, paste into the AI Assistant chat window via `EditorActionManager` / clipboard. First slice sends `hello`; read loop and chat injection remain.                               | M      | med  |
| P3.3  | Hook the JetBrains AI Assistant lifecycle (`AIAssistantChatSessionListener` once it exists, or polling fallback) to emit `session.ended`.                                                                  | L      | high |
| P3.4  | Publish to the JetBrains Marketplace. Optional; sideload via "Install from Disk" works for the MVP.                                                                                                        | M      | low  |
| P3.5  | Add `tests/test_autopilot_jetbrains.py` — at minimum a smoke test that runs the Kotlin daemon-shim against the Python daemon to verify protocol compatibility.                                             | S      | low  |

---

## Phase 4 — closed loop with reply capture

Goal: koru can read what the LLM said back, decide what to do, and
either type the next prompt or stop. This is the autonomy unlock.

| #     | Item                                                                                                                                                                                                                                                                                          | Effort | Risk |
|-------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|--------|------|
| P4.1  | Extend the protocol with `chat.reply` (plugin → daemon) carrying `{text, role, finished}`.                                                                                                                                                                                                       | S      | low  |
| P4.2  | Daemon-side router that decides what to send next based on `chat.reply`. Plug in `koru.context.build_context()` + planfile lifecycle (claim → start → complete).                                                                                                                                | L      | high |
| P4.3  | "Looper" mode (`koru autopilot loop`): each `chat.reply` triggers either a follow-up `chat.send` (continue) or a `planfile ticket complete` (done) based on a small policy DSL.                                                                                                                  | L      | high |
| P4.4  | Safety rails: kill switch (`koru autopilot brake`), per-loop iteration cap, mandatory human-in-the-loop checkpoint every N turns.                                                                                                                                                                | M      | high |

---

## Refactor backlog (independent of phase work)

These are technical-debt items I noticed while shipping Phase 1. They
do not block any feature, but they should be addressed before this
subsystem reaches "stable" status.

| Tag       | Item                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          | Where                                                       | Effort | Status |
|-----------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|-------------------------------------------------------------|--------|--------|
| **R1**    | `_HANDLERS` is a module-level dict referencing private `_handle_*` methods through thin `_h_*` wrappers. Replace with bound methods set in `__init__`, or a `@_handler("type")` decorator collected on the class.                                                                                                                                                                                                                                                                              | `src/koru/autopilot/daemon.py:_HANDLERS`                    | S      | ✅     |
| **R2**    | Integration tests duplicate "start daemon in a thread, connect, read frames" plumbing. Extract a `pytest` fixture + helper context manager.                                                                                                                                                                                                                                                                                                                                                    | `tests/test_autopilot_daemon.py`                            | S      | ✅     |
| **R3**    | `Injector._press_wtype` now raises `InjectorError` when given a `Mod1+Mod2+Key` combo instead of silently doing the wrong thing.                                                                                                                                                                                                                                                                                                                                                                | `src/koru/autopilot/injector.py`                            | XS     | ✅     |
| **R4**    | `_default_handoff` re-imports `koru.context` on every event → now goes through `_load_context_module()` cached with `functools.lru_cache(maxsize=1)`.                                                                                                                                                                                                                                                                                                                                          | `src/koru/autopilot/daemon.py:_default_handoff`             | XS     | ✅     |
| **R5**    | `detect_running_ides` scans `/proc` on every call → new `detect_running_ides_cached(ttl=2.0)` + `clear_detect_cache()`; daemon imports the cached entry-point.                                                                                                                                                                                                                                                                                                                                  | `src/koru/autopilot/ide.py`                                 | S      | ✅     |
| **R6**    | `koru.cli.main` `if/elif` ladder for 8 subcommands replaced with `_SUBCOMMANDS: dict[str, Callable]` dispatch table. Adding a new subcommand is now one line.                                                                                                                                                                                                                                                                                                                                   | `src/koru/cli.py:main`                                      | M      | ✅     |
| **R7**    | Submit keymap moved to `~/.config/koru/autopilot.toml` (`[submit_keys]` section). New module `src/koru/autopilot/config.py` (TOML loader + cached access + safe fallback on missing/malformed). `injector._submit_key_for(ide)` consults the config.                                                                                                                                                                                                                                            | `src/koru/autopilot/config.py`, `src/koru/autopilot/injector.py` | S      | ✅     |
| **R8**    | The VS Code extension uses clipboard + paste + submit. Restore the previous clipboard in `finally` so a thrown paste/submit doesn't leave our payload in the user's clipboard. (Long-term: use `vscode.chat.sendMessage` once it stabilises.)                                                                                                                                                                                                                                                  | `plugins/koru-autopilot-vscode/src/extension.ts:injectChat` | M      | 🟡 partial |
| **R9**    | `daemon._handle_drive` mixes plugin-path and keyboard-sim branches in one method (CC ≈ 9). Extract `_drive_via_plugin` and `_drive_via_keyboard` so each is testable in isolation.                                                                                                                                                                                                                                                                                                              | `src/koru/autopilot/daemon.py`                              | S      | ✅     |
| **R10**   | Plugin-side reconnect loop has no jitter; if the daemon restarts and 30 IDE windows are open they all reconnect within the same 3 s window. Add ±500 ms random jitter.                                                                                                                                                                                                                                                                                                                          | `plugins/koru-autopilot-vscode/src/extension.ts:scheduleRetry` | XS     | ✅     |
| **R11**   | Added regression test that monkeypatches `_peer_uid` to a foreign UID and asserts the daemon closes the connection before registering any client, preserving same-UID enforcement in CI without requiring `setuid`/`unshare`.                                                                                                                                                                                                                                          | `tests/test_autopilot_daemon.py`                            | M      | ✅     |
| **R12**   | Per-type field whitelist (`_FIELD_SCHEMA`) applied in `decode()`; strict types drop unknown keys, `ack`/`error` keep arbitrary info blocks.                                                                                                                                                                                                                                                                                                                                                     | `src/koru/autopilot/protocol.py`                            | S      | ✅     |
| **R13**   | Focused-window arbitration added: `detect_focused_ide_id()` maps active X11 window PID (`xdotool getactivewindow getwindowpid`) to IDE id; `pick_target()` now prefers focused IDE when `--ide` is not explicit; `ide-list` and `doctor` surface focus as `[focused]` / `focused_ide`.                                                                                                                                                                                                                                                                                    | `src/koru/autopilot/{ide,cli_command}.py`                   | M      | ✅     |
| **R14**   | VS Code extension: TS error `Thenable<T>.catch` does not exist. Wrap each `vscode.commands.executeCommand(...)` in `Promise.resolve(...)` (or extract a `runCommand()` helper that does so + logs failures). Currently blocks `npm run compile`.                                                                                                                                                                                                                                                | `plugins/koru-autopilot-vscode/src/extension.ts`            | XS     | ✅     |
| **R15**   | Extracted plugin-install command implementation out of the autopilot CLI router. `cli_command.py` now keeps parser/action wiring and compatibility shims; VS Code-family and JetBrains plugin install flows live in `install_plugin_cli.py`.                                                                                                                                                                                                                                                        | `src/koru/autopilot/{cli_command,install_plugin_cli}.py`     | S      | ✅     |
| **R16**   | Extracted audit-log tail rendering out of the autopilot CLI router. The `tail` command action now lives in `tail_cli.py`; `cli_command.py` keeps only the parser and compatibility aliases.                                                                                                                                                                                                                                                                                            | `src/koru/autopilot/{cli_command,tail_cli}.py`               | XS     | ✅     |
| **R17**   | Extracted `install-unit` systemd rendering/writing out of the autopilot CLI router. The command action now lives in `systemd_cli.py`; compatibility aliases remain in `cli_command.py` for tests and older imports.                                                                                                                                                                                                                                                                      | `src/koru/autopilot/{cli_command,systemd_cli}.py`            | XS     | ✅     |
| **R18**   | Extracted `doctor` and `setup-host` command actions out of the autopilot CLI router. Diagnostic rendering and host remediation dispatch now live in `doctor_cli.py`; parser wiring and compatibility aliases remain in `cli_command.py`.                                                                                                                                                                                                                                       | `src/koru/autopilot/{cli_command,doctor_cli}.py`             | S      | ✅     |
| **R19**   | Extracted OS-injector profile calibration commands out of the autopilot CLI router. `calibrate` and `session-start` now live in `calibrate_cli.py`; parser wiring and sleep/detection compatibility hooks remain in `cli_command.py`.                                                                                                                                                                                                                                      | `src/koru/autopilot/{cli_command,calibrate_cli}.py`          | S      | ✅     |

### Suggested execution order

1. ~~**R1, R2** (mechanical cleanups), **R9** (split _handle_drive), **R10/R14** (extension): done in refactor pass 1.~~
2. ~~**R3, R4, R5** (small wins), **R12** (protocol schema cap): done in refactor pass 2.~~
3. ~~**R7** (TOML config for submit keymap): done in refactor pass 3.~~
4. ~~**R6** (CLI dispatch table): done in refactor pass 4.~~
5. ~~**R8** (clipboard race)~~ — partial fix landed; long-term move to `vscode.chat.sendMessage` still open.
6. ~~**R13** (focused-window arbitration)~~ — done in refactor pass 6.

**Status snapshot:** 18/19 refactor items shipped (R1, R2, R3, R4, R5, R6, R7, R9, R10, R11, R12, R13, R14, R15, R16, R17, R18, R19 ✅; R8 🟡).

Phase 2 progress: **P2.1, P2.5, P2.6, P2.7, P2.8, P2.9 ✅** shipped (VSIX build/install/reassert via `manage`; `handoff` one-shot; systemd user unit; audit log; `tail` renderer; install/runtime version drift detection and strict stale-plugin gate). Phase 2 still needs P2.2 (CI release), P2.3 (real `session.ended`), P2.4 (capture reply).

Phase 3 progress: **P3.1 ✅** shipped (JetBrains Gradle scaffold and minimal socket bridge). P3.2 still needs daemon read-loop handling for `chat.send` plus AI Assistant paste/submit.

---

## Out of scope (intentional)

| Item                                              | Why                                                                                                            |
|---------------------------------------------------|----------------------------------------------------------------------------------------------------------------|
| Windows / macOS support                           | koru is Linux-first; no maintainer bandwidth. Patches welcome.                                                |
| Network listener (`koru autopilot daemon --tcp`)  | Security model is "same UID on the same machine". Networked IDE remote control is a different product.        |
| OCR / screen-scraping                             | Brittle, IDE-version-coupled. We have a plugin path; if it doesn't exist, keyboard-sim is good enough.        |
| Headless IDE driving (no display)                 | A headless IDE has no chat panel. Use the planfile queue runner (`koru --queue --loop`) instead.              |
| Cross-machine driving                             | Use SSH X11/Wayland forwarding or run koru in the remote terminal — both already work without new plumbing.   |

---

## Sizing guide

| Size | Engineer-hours | Examples                                                  |
|------|----------------|-----------------------------------------------------------|
| XS   | < 1            | adding jitter, capping a regex                            |
| S    | 1–4            | extracting a fixture, adding a CLI flag                   |
| M    | 4–16           | a new subsystem with tests (e.g. systemd unit + install)  |
| L    | 16–40          | a new feature crossing daemon + plugin (P4.x)             |
