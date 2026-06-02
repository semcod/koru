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

coru text "ustaw lane windsurf-main i pokaż status"
coru text "run auto for cursor-main" --llm
coru text "start refaktoryzacje"
coru chat
coru chat --llm

# shortest UX
coru
coru "run auto for windsurf-main in windsurf"
```

`coru` without args starts chat mode.

On startup, `coru` prints runtime versions so you can verify environment quickly:

- `coru=<version>`
- `koru=<version>`

If first argument is plain text (not a subcommand), `coru` routes it to `coru text ...` automatically.

In interactive chat mode (`coru` / `coru chat`):

- normal message => sent directly to IDE chat (`koru autopilot drive`),
- `/...` message => treated as coru command-intent (ensure/lane/status/auto chain),
- if OpenRouter is configured (`OPENROUTER_API_KEY`) or `--llm` is set, prompt text is first rewritten by LLM for better IDE-chat phrasing.

`coru lane`, `coru lane-status`, `coru auto` work without arguments and use lane defaults:

- `KORU_AUTOPILOT_IDE` or `windsurf`
- `KORU_AUTOPILOT_INSTANCE` or `<ide>-main`

`coru text` now supports multi-step execution by default for setup/auto intents:

- `ensure --install`
- `lane`
- `lane-status`
- `auto` (when requested)

Use `--single-action` to disable chaining.

## Environment for LLM mode

When using --llm, set:
- OPENROUTER_API_KEY or provider-specific keys,
- CORU_LLM_MODEL (default: openrouter/qwen/qwen3-coder-next).
