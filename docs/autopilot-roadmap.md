# koru autopilot — roadmap & refactor backlog

> Companion to [`autopilot-design.md`](./autopilot-design.md) and
> [`autopilot-quickstart.md`](./autopilot-quickstart.md). Tracks what is
> shipped (Phase 1) and what remains. Items are scoped so each one is
> a single planfile ticket.
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
| P1.7  | Auto-handoff on `session.ended` with `--handoff-cooldown` anti-loop                     | ✅     |
| P1.8  | VS Code extension shell (TypeScript, paste-and-submit, status bar, reconnect)           | ✅     |
| P1.9  | 53 unit + integration tests (`tests/test_autopilot_*.py`)                               | ✅     |
| P1.10 | Quickstart + design doc + roadmap                                                       | ✅     |

---

## Phase 2 — make the plugin path the default

Goal: every koru user has the VS Code extension installed and the
keyboard-sim fallback is only the safety net for headless / non-VS-Code
contexts.

| #     | Item                                                                                                                                                                                                                                                                                                                | Effort | Risk  |
|-------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|--------|-------|
| P2.1  | **Compile + package the VS Code extension to a `.vsix`.** Add `npm run package` (uses `vsce`), commit a `package-lock.json`, document `code --install-extension koru-autopilot-0.1.0.vsix`.                                                                                                                        | S      | low   |
| P2.2  | **Auto-publish the VSIX as a GitHub release asset** on every koru tag. Workflow under `.github/workflows/release-vsix.yml`.                                                                                                                                                                                          | S      | low   |
| P2.3  | **Emit real `session.ended` from the VS Code extension.** Currently we connect & paste; we don't hook the chat lifecycle yet. Use `vscode.chat.onDidEndSession` (Copilot Chat ≥ 1.93) and the Cascade-specific event in Windsurf (TBD via reverse-eng or extension API request).                                    | M      | med   |
| P2.4  | **Capture the LLM reply text** (read-side). Phase 4 in the design doc — pulled forward to Phase 2 because it unblocks the closed loop. Requires reading from the chat document via `vscode.workspace.openTextDocument(chatUri)` or similar.                                                                          | L      | high  |
| P2.5  | **Plugin-side `koru autopilot handoff` shortcut.** Equivalent to `koru --context --format markdown \| koru autopilot drive`. Mentioned in the design doc but not wired yet.                                                                                                                                          | S      | low   |
| P2.6  | **systemd `--user` unit** for the daemon so it survives reboots without a babysitter terminal. Ship `systemd/koru-autopilot.service` + `task autopilot:install-unit`.                                                                                                                                                | S      | low   |
| P2.7  | **Persistent audit log** under `~/.local/state/koru/autopilot.log` with 10 MiB rotation (design doc promises this). Use `logging.handlers.RotatingFileHandler`.                                                                                                                                                      | S      | low   |
| P2.8  | **`koru autopilot tail`** subcommand that streams the audit log.                                                                                                                                                                                                                                                    | S      | low   |

---

## Phase 3 — JetBrains parity

Goal: PyCharm / IntelliJ / WebStorm users get the same plugin
experience as VS Code users.

| #     | Item                                                                                                                                                                                                       | Effort | Risk |
|-------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|--------|------|
| P3.1  | Replace `plugins/koru-autopilot-jetbrains/README.md` stub with a real Gradle / IntelliJ-Platform plugin skeleton (`build.gradle.kts`, `plugin.xml`).                                                       | M      | low  |
| P3.2  | Unix-socket bridge in Kotlin (parity with the TS extension): `hello`, listen for `chat.send`, paste into the AI Assistant chat window via `EditorActionManager` / clipboard.                               | M      | med  |
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
| **R3**    | `Injector._press_wtype` only handles `Mod+Key`; if a future IDE binding needs `Mod1+Mod2+Key` the code silently does the wrong thing. Either add explicit support, or assert `len(modifiers) ≤ 1` to fail loudly.                                                                                                                                                                                                                                                                              | `src/koru/autopilot/injector.py`                            | XS     | ⬜     |
| **R4**    | `_default_handoff` re-imports `koru.context` on every event. Memoise the import (one-time) or import at module load if it's cheap enough. Profile first.                                                                                                                                                                                                                                                                                                                                       | `src/koru/autopilot/daemon.py:_default_handoff`             | XS     | ⬜     |
| **R5**    | `detect_running_ides` scans `/proc` on every `drive` and on every `status`. Cache for ~2 s; expose `--no-cache`. Useful when many drives happen in a tight loop (e.g. during smoke tests).                                                                                                                                                                                                                                                                                                       | `src/koru/autopilot/daemon.py:_handle_drive`                | S      | ⬜     |
| **R6**    | The CLI subcommand routing in `koru.cli.main` is a long `if raw_args[0] == "x"` ladder. Migrate to a single dispatch table; the new `autopilot` branch makes the pattern visibly repetitive.                                                                                                                                                                                                                                                                                                   | `src/koru/cli.py:main`                                      | M      | ⬜     |
| **R7**    | `injector.py:_SUBMIT_KEY` is hard-coded. Lift it to a user-config file at `~/.config/koru/autopilot.toml` so people can override per IDE / per chat without patching koru.                                                                                                                                                                                                                                                                                                                       | `src/koru/autopilot/injector.py`                            | S      | ⬜     |
| **R8**    | The VS Code extension uses clipboard + paste + submit. Restore the previous clipboard in `finally` so a thrown paste/submit doesn't leave our payload in the user's clipboard. (Long-term: use `vscode.chat.sendMessage` once it stabilises.)                                                                                                                                                                                                                                                  | `plugins/koru-autopilot-vscode/src/extension.ts:injectChat` | M      | 🟡 partial |
| **R9**    | `daemon._handle_drive` mixes plugin-path and keyboard-sim branches in one method (CC ≈ 9). Extract `_drive_via_plugin` and `_drive_via_keyboard` so each is testable in isolation.                                                                                                                                                                                                                                                                                                              | `src/koru/autopilot/daemon.py`                              | S      | ✅     |
| **R10**   | Plugin-side reconnect loop has no jitter; if the daemon restarts and 30 IDE windows are open they all reconnect within the same 3 s window. Add ±500 ms random jitter.                                                                                                                                                                                                                                                                                                                          | `plugins/koru-autopilot-vscode/src/extension.ts:scheduleRetry` | XS     | ✅     |
| **R11**   | No regression test for `SO_PEERCRED` rejection. Hard to write portably; consider a `pytest.mark.skipif(os.getuid() == 0, …)` test that uses `unshare` / `setuid` if available, and document the manual verification recipe in the design doc otherwise.                                                                                                                                                                                                                                          | `tests/test_autopilot_daemon.py` (new)                      | M      | ⬜     |
| **R12**   | The `Message.to_dict()` reserves `type` and `id` but lets every other field through silently. If a plugin sends `{"type":"hello","ide":"…","__proto__":"evil"}` we forward it unchanged. Cap accepted extras to a known schema per message type.                                                                                                                                                                                                                                                  | `src/koru/autopilot/protocol.py`                            | S      | ⬜     |
| **R13**   | `koru autopilot ide-list` doesn't tell you which IDE *window* currently has focus. On X11 use `xdotool getactivewindow getwindowpid`; on Wayland use `swaymsg -t get_tree` (sway) or rely on the plugin path.                                                                                                                                                                                                                                                                                    | `src/koru/autopilot/ide.py`                                 | M      | ⬜     |
| **R14**   | VS Code extension: TS error `Thenable<T>.catch` does not exist. Wrap each `vscode.commands.executeCommand(...)` in `Promise.resolve(...)` (or extract a `runCommand()` helper that does so + logs failures). Currently blocks `npm run compile`.                                                                                                                                                                                                                                                | `plugins/koru-autopilot-vscode/src/extension.ts`            | XS     | ✅     |

### Suggested execution order

1. ~~**R1, R2** (mechanical cleanups) before Phase 2~~ — done; the harness already paid off when R9 landed.
2. **R12** (schema cap) before Phase 3 — protocol freezes once JetBrains ships.
3. ~~**R8** (clipboard race)~~ — partial fix (clipboard restored in `finally`); the long-term move to `vscode.chat.sendMessage` is still pending.
4. **R3, R4, R5** — small wins; pick up opportunistically.
5. **R7** (config file for keymap) — required before JetBrains lands so `_SUBMIT_KEY` table doesn't grow inside the codebase.
6. **R11** (peercred test) is the only security gap visible in CI today; do it after the protocol stabilises.

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
