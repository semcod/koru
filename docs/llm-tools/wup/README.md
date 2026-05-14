# WUP on-change gate

`wup` is the local file watcher in the on-change gate triad. In koru it is
configured by [`../../../wup.yaml`](../../../wup.yaml) and is meant for the
developer loop between saving files and committing changes.

## Commands

| Scenario | Command |
|---|---|
| Check config/status | `task quality:wup` |
| Direct status check | `wup status` |
| Start watcher | `wup watch` |
| Rebuild dependency map | `wup map-deps` |
| Inspect TestQL endpoints | `wup testql-endpoints` |

## Koru bootstrap

The root `wup.yaml` watches:

- `src/**` for core Python changes
- `plugins/koru-autopilot-vscode/src/**` for autopilot plugin changes

The lightweight `task quality:wup` gate validates that `wup` is installed,
`wup.yaml` exists, `gate:wup` is enabled in topology, and `wup status` can read
the configuration. It does not start the long-running watcher.

Use `wup watch` when you want the continuous 3-layer loop:

1. detect file changes
2. run quick related probes
3. run full detail/blame checks only after quick failures
