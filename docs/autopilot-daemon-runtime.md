# Autopilot Daemon Runtime

Koru uses a local Unix-socket daemon between the CLI/autonomous loop and IDE
plugins. The daemon reports its runtime identity through `koru autopilot status`
and writes a project-local sidecar when it starts:

```text
.planfile/.koru/<socket-name>.daemon.json
```

The sidecar includes the daemon PID, Koru package version, git SHA, Python
executable, project path, socket path, start time, and selected environment
values. This makes version drift visible when a CLI has been upgraded but an
older daemon process is still attached to the socket.

`koru auto` probes an existing daemon before reuse. If the daemon status reports
a different Koru version from the current CLI package, Koru requests daemon
shutdown and starts a replacement on the same socket.

Related runtime status:

```bash
koru autopilot status --explain
```

The JSON payload contains both `daemon` and `daemon_metadata` fields. Useful
fields during diagnosis are:

- `daemon.pid`
- `daemon.version`
- `daemon.git_sha`
- `daemon.python_executable`
- `daemon.metadata_path`
- `plugins[].ide`
- `plugins[].version`
- `plugins[].workspaceName`
- `plugins[].workspaceFolders`

VSCodium focus-open policy is intentionally conservative. The command picker
filters QuickChat/openChat/panel-open candidates for `focus_open` and prefers
`workbench.action.chat.focusInput`, so a normal drive targets the existing chat
input instead of creating a new chat surface.

When more than one VSCodium/VS Code-family window is open, the daemon also uses
plugin workspace metadata for routing. A fresh plugin hello includes
`workspaceName` and `workspaceFolders`; `koru auto` prefers the connected plugin
whose workspace contains the current project root. Workspace-aware plugin
connections are kept over legacy connections that do not report a workspace, so
an unrelated window cannot keep replacing the project window on the same socket.
If the shell log says `workspace=unknown`, reload the IDE window so the current
VSIX code is active.

Project-level policy is documented in `koru.yaml` under `autonomy.daemon`.
