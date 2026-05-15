# WUP on-change gate

`wup` is the `semcod/wup` package: the local file and service watcher in the
on-change gate triad. In koru it is configured by
[`../../../wup.yaml`](../../../wup.yaml) and is meant for the developer loop
between saving files and committing changes.

Use it when you want real-time regression detection:

- file changes are detected from `wup.yaml`
- changed files are mapped to affected services through `deps.json`
- quick TestQL probes run first
- detail/blame checks run only after quick failures
- live service health is written to `.wup/service-health.json`

## Commands

| Scenario | Command |
|---|---|
| Check config/status | `task quality:wup` |
| Direct status check | `wup status` |
| Start watcher | `wup watch` |
| Start watcher with TestQL in this repo | `wup watch . --deps deps.json --cpu-throttle 0.8 --mode testql --scenarios-dir testql-scenarios --testql-bin scripts/koru-wup-testql --track-dir .wup/tracks --quick-limit 3` |
| Rebuild dependency map | `wup map-deps` |
| Inspect TestQL endpoints | `wup testql-endpoints testql-scenarios` |

## First run

```bash
wup status
wup map-deps
wup testql-endpoints testql-scenarios
wup watch . \
  --deps deps.json \
  --cpu-throttle 0.8 \
  --mode testql \
  --scenarios-dir testql-scenarios \
  --testql-bin scripts/koru-wup-testql \
  --track-dir .wup/tracks \
  --quick-limit 3
```

The `scripts/koru-wup-testql` launcher is a compatibility adapter for the real
`testql` binary used by this project. It normalizes WUP timeout arguments such
as `10s` to TestQL milliseconds and then executes `testql`; it does not mock or
simulate test results.

To trigger a local smoke check, edit or touch a watched file:

```bash
touch src/koru/__init__.py
cat .wup/service-health.json
```

Expected healthy status after a passing quick probe:

```json
{
  "koru-core": {
    "status": "up",
    "stage": "quick",
    "message": "Quick TestQL passed"
  }
}
```

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

## Koru autonomous

Koru can start WUP as part of the autonomous loop:

```bash
koru autonomous up --wup-watch --wup-mode testql
```

The autonomous integration uses the same `wup.yaml`, `deps.json`,
`testql-scenarios/`, and TestQL launcher path. `--wup-cpu-throttle` accepts
either WUP's native `0.0-1.0` value or a percent-style value such as `70`; Koru
normalizes percent values before invoking WUP.

## WUP vs. Regix

Use `wup` for runtime/on-change regression monitoring of files and services.
Use `regix` for git-native code metric regressions against `HEAD` or another
revision.
