# koruide

IDE truth for the koru ecosystem — the single place that knows what an IDE
*is*, how its plugin is installed and verified, and how a chat panel is
driven.

Extracted from `koru/src/koruide` (STARTER-563 phase 1). It was already
standalone-safe before the move: `import koruide` succeeds with both `koru`
and `gillm` blocked on the meta path, which
`tests/test_koruide_standalone_import.py` in the koru repo asserts by
spawning a fresh interpreter.

## What lives here

- **identity** — `ide.py`: alias map, binary candidates, window names. The
  single source koru's `autonomy/environment`, `agent_backend_runtime`,
  `mcp_provision` and `autopilot/install_plugin_cli` all derive from, instead
  of the four drifting copies they used to keep.
- **plugin lifecycle** — `plugin_installer.py`, `plugin_router.py`: install,
  version/build-SHA verification, stale-directory pruning, per-IDE
  `extensions.json` adapters.
- **daemon** — `daemon/`: the autopilot broker protocol, handlers and
  storage. `daemon/protocol.py` is contract-tested to stay free of both
  `daemon.handlers` and `koru`.
- **drive** — `drive_orchestrator.py`, `drive_policy.py`, `chat_history*`:
  turning "send this text to the IDE chat" into a verified sequence.

## Dependency direction

```
koru ──imports──▶ koruide ──imports──▶ gillm
                     │
                     └── one lazy, try/except-guarded back-edge into koru
                         (daemon/metadata.py::_normalized_project) with a
                         local fallback — deliberately not a hard edge
```

`import koruide` works without gillm; the submodules that need an injector
(`.config`, `.host_setup`, `.injector`) are lazy exports so the core import
stays clean.
