# coru

coru is a thin, stable client layer over koruenv and koru.

Goal:
- keep end-user commands simple and stable,
- allow backend refactors in koruenv/koru without changing user UX.

## Install

```bash
pip install -e ./packages/coru
```

Optional LLM command planning:

```bash
pip install -e ./packages/coru[llm]
```

## Main commands

```bash
coru ensure
coru ensure --install
coru sync
coru sync --all-ides
coru sync --repair
coru sync windsurf windsurf-main --repair

coru lane
coru lane windsurf windsurf-main --print-env
coru env
coru env cursor cursor-main --shell zsh
coru lane-status
coru lane-status windsurf windsurf-main
coru status
coru status cursor cursor-main

coru auto
coru auto windsurf windsurf-main
coru auto windsurf windsurf-main -- --max-cycles 1 --sleep-seconds 0

# orchestrated diagnostics (prefer system shell)
coru doctor
coru doctor cursor cursor-main --fix --probe

coru text "ustaw lane windsurf-main i pokaż status"
coru text "run auto for cursor-main" --llm
coru text "start refaktoryzacje"
coru chat
coru chat --llm
coru --log-format jsonl chat

# shortest UX
coru
coru "run auto for windsurf-main in windsurf"
```

`coru` without args starts autonomous work. It runs the same high-level chain users
previously had to remember manually:

- `ensure --install`
- `lane`
- `manage --fix`
- `lane-status`
- `auto`

`coru sync` is the explicit one-shot for the full ecosystem (editable `koruenv`/`koru`/`coru`,
repo VSIX plugins via `koru autopilot install-plugin`). By default it does **not** run
`manage --fix` (use `--repair` to opt in — that path can open extra IDE windows).
After plugin upgrades, reload each IDE window manually — autopilot cannot do that safely from an
integrated terminal.

Use `coru chat` for interactive IDE-chat mode (or `CORU_MODE=chat coru`).

Pass extra flags to `koru auto`:

```bash
coru -- --max-cycles 1 --sleep-seconds 0
```

On startup, `coru` prints runtime versions so you can verify environment quickly:

- `coru=<version>`
- `koru=<version>`

If first argument is plain text (not a subcommand), `coru` routes it to `coru text ...` automatically.

In interactive chat mode (`coru chat`):

- normal message => sent directly to IDE chat (`koru autopilot drive`),
- `/...` message => treated as coru command-intent (ensure/lane/status/auto chain),
- if OpenRouter is configured (`OPENROUTER_API_KEY`) or `--llm` is set, prompt text is first rewritten by LLM for better IDE-chat phrasing.

`coru lane`, `coru lane-status`, `coru auto` work without arguments and use lane defaults:

- `KORU_AUTOPILOT_IDE` or `windsurf`
- `KORU_AUTOPILOT_INSTANCE` or `<ide>-main`

`coru doctor` is the orchestrator entrypoint for bridge diagnostics:

- validates lane + daemon status,
- can run bridge repair (`--fix`),
- can run plugin-required probe (`--probe`).

By default it requires a system shell (outside integrated IDE terminal). Use
`--allow-integrated-shell` only when necessary.

### Bridge repair (CQRS + event sourcing)

Autodiagnostics produce `RepairProblem` rows; the registry maps each code to a
repair **command** (`RepairStepDef` in `coru.repair.registry.REPAIR_REGISTRY`).
Every repair session is appended to `.planfile/.koru/repair-events.jsonl` so an
LLM (or operator) can inspect prior fixes:

```bash
coru repair run --ide cursor --instance cursor-main   # detect + autorepair
coru repair history --format llm --limit 20             # markdown case briefs
coru repair history --code submit_unverified --format json
```

To add a new bugfix command:

1. Add a `RepairStepDef` row (issue codes → `action_id`, priority, `llm_playbook`).
2. Implement the handler in `coru.repair.pipeline._execute_step` (if new action).
3. Optionally extend `coru.repair.diagnostics` to emit a new problem code.

`coru text` now supports multi-step execution by default for setup/auto intents:

- `ensure --install`
- `lane`
- `lane-status`
- `auto` (when requested)

Use `--single-action` to disable chaining.

## Supervisor (background lane registry)

`coru supervisor` keeps one registry of IDE lanes (socket, daemon health, active lane)
without a desktop app. HTTP API defaults to `http://127.0.0.1:8766`.

```bash
cd ~/github/semcod/koru
pip install -e ./packages/coru

# register lane (--project must exist; prefer absolute path)
coru supervisor register cursor cursor-main \
  --project ~/github/semcod/koru --set-active

# start background supervisor (health refresh every 30s)
coru supervisor start

# inspect
coru supervisor status
coru supervisor lanes
curl -s http://127.0.0.1:8766/api/lanes | jq .

# VSIX — absolute path (relative paths resolve from cwd!)
/usr/bin/cursor --install-extension \
  ~/github/semcod/koru/plugins/koru-autopilot-cursor/koru-autopilot-cursor-0.2.1.vsix \
  --force

# in Cursor: Developer: Reload Window → koru: Connect autopilot daemon

coru supervisor daemon start cursor-main
coru supervisor reconnect cursor-main
cd ~/github/semcod/koru && coru   # project from registry, not cwd

# stop supervisor
coru supervisor stop
```

When the registry has an active lane, bare `coru` / `coru auto` use it automatically.
`coru auto` passes `--agent-lane <instance>` and `--project <path from registry>` to
`koru auto` so suffixed lanes like `cursor-main` stay on the correct socket/project.

Optional systemd user unit: `systemd/coru-supervisor.service`.

Recovery API (for dashboard buttons):

- `POST /api/lanes/{instance}/reconnect` (restart daemon + refresh lane health)

## Logging contract

`coru` supports a standard event contract for debugging output.

- format: `--log-format human|jsonl` (or `CORU_LOG_FORMAT`, fallback `KORU_STDIO_FORMAT`)
- jsonl fields: `ts`, `corr`, `component`, `level`, `action`, `result`, `rc`

Examples:

```bash
coru --log-format jsonl chat
coru --log-format jsonl text "run auto for cursor-main"
```

## Environment for LLM mode

When using --llm, set:
- OPENROUTER_API_KEY or provider-specific keys,
- CORU_LLM_MODEL (default: openrouter/qwen/qwen3-coder-next).
