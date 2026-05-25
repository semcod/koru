# Koru Control Command DSL

Every side-effecting control action should be represented as a replayable
`control.command` event before Koru executes it.

The canonical storage is `.koru/events/observability.jsonl`; the readable DSL
is rendered by `koru observe trace --format dsl`.

## Shape

```text
@2026-05-25T16:50:55Z version=koru.obs.v1 corr=cli-drive component=control actor=operator
command args={"argv":["koru","autopilot","drive","--ide","vscodium","--prompt","..."],"cwd":"/repo"} authority=high interface_id=subprocess_local_tools operation=koru replayable=true surface=shell_cli transport=subprocess verification=exit_code_and_output
```

Required command fields:

- `surface`: `api`, `shell_cli`, `ide_chat`, `desktop_gui`.
- `interface_id`: id from `docs/interfaces/koru-interface-registry.yaml`.
- `transport`: concrete transport, for example `http_json`, `subprocess`,
  `unix_socket_ndjson`, `xdotool`.
- `operation`: formal operation name, such as `GET /api/autonomy/trace`,
  `koru`, `chat.send`, `type_text`.
- `args`: structured replay arguments.
- `replayable`: whether the command can be safely replayed without live GUI
  state.

## Constructor Functions

Use functions from `koru.control_commands`, not ad-hoc strings:

- `api_command(...)`
- `shell_command(...)`
- `plugin_socket_command(...)`
- `desktop_gui_command(...)`
- `control_command(...)`

This keeps API routes, shell CLI, plugin socket traffic, and desktop GUI input
under one auditable command vocabulary.

## Trace Views

Use one source of truth with three views:

```bash
koru observe trace --ticket STARTER-277
koru observe trace --corr cli-drive --format compact
koru observe trace --corr cli-drive --format path
koru observe trace --corr cli-drive --format dsl
koru observe trace --corr cli-drive --format json
```

`compact` emits short terminal lines such as:

```text
[17:10:34] koru > OBS: corr=cli-drive ticket=STARTER-277 component=autopilot severity=error failure code=autopilot_daemon_timeout message="daemon unreachable: timed out"
```

`dsl` emits the full two-line record. `json` emits the canonical event
projection for replay and tooling.

`path` emits the shortest semantic axis:

```text
OBS intent(deliver_prompt_to_ide_chat) -> decision(plugin) -> phase(submit awaiting_ack) -> failure(autopilot_daemon_timeout) -> blocker(drive_failed) -> next(retry_next_cycle)
```

The dashboard exposes the same trace contract over HTTP:

```bash
curl -s 'http://127.0.0.1:8765/api/observe/trace?ticket=STARTER-277'
curl -s 'http://127.0.0.1:8765/api/observe/trace?corr=cli-drive&limit=25'
```

The response contains:

- `events`: canonical JSONL envelopes.
- `compact`: terminal-ready semantic timeline lines.
- `path`: one-line semantic axis for the selected trace.
- `dsl`: replayable two-line DSL records.
