# koru

<img src="maori-koru-bold-400w.png" width="200" alt="koru">

## AI Cost Tracking

![PyPI](https://img.shields.io/badge/pypi-costs-blue) ![Version](https://img.shields.io/badge/version-0.1.31-blue) ![Python](https://img.shields.io/badge/python-3.9+-blue) ![License](https://img.shields.io/badge/license-Apache--2.0-green)
![AI Cost](https://img.shields.io/badge/AI%20Cost-$2.10-orange) ![Human Time](https://img.shields.io/badge/Human%20Time-4.6h-blue) ![Model](https://img.shields.io/badge/Model-openrouter%2Fqwen%2Fqwen3--coder--next-lightgrey)

- 🤖 **LLM usage:** $2.1000 (14 commits)
- 👤 **Human dev:** ~$461 (4.6h @ $100/h, 30min dedup)

Generated on 2026-05-10 using [openrouter/qwen/qwen3-coder-next](https://openrouter.ai/qwen/qwen3-coder-next)

---

Python package for **closed-loop refactor automation** across multi-repo
workspaces (validated on `semcod/*`, `maskservice/c2004`, and other monorepos).

The name refers to *Koru* (Māori spiral), matching the "spiraling loop"
refactor flow: **detect → plan → execute → verify → heal → repeat**.

## What koru is

A meta-orchestrator that coordinates **LLM-augmented refactor tools** with
**ticket-driven workflow** and **regression-free verification**:

```
┌────────────────────────────────────────────────────────────────┐
│                          KORU                                  │
├──────────┬──────────┬──────────┬──────────┬─────────┬──────────┤
│ DETECT   │ PLAN     │ EXECUTE  │ VERIFY   │ HEAL    │ LEARN    │
├──────────┼──────────┼──────────┼──────────┼─────────┼──────────┤
│ redup    │ planfile │ Windsurf │ regix    │ healing │ pyqual   │
│ regix    │ tickets  │ Cursor   │ pytest   │ webhook │ metrics  │
│ TestQL   │ Promet.  │ aider    │ TestQL   │ retry   │dashboards│
│ Probe    │ Alertmgr │ vallm    │ vallm    │         │          │
└──────────┴──────────┴──────────┴──────────┴─────────┴──────────┘
        ↑                                                  │
        └─────────── closed-loop feedback ─────────────────┘
```

## Two operational modes

| Mode | When | What runs |
|---|---|---|
| **Default: IDE-native** | normal ticket work, no external API | Windsurf/Cursor LLM + `task tickets:next` + regix/pytest |
| **Opt-in: OpenRouter automation lane** | infra smoke tests, headless auto-fix, scheduled runs | `redsl improve`, `llx fix`, `vallm validate --semantic` (all use OpenRouter) |

## Install (editable)

```bash
pip install -e .
```

## Quick start

Run one command across matching repositories and retry failures in a closed loop:

```bash
koru \
  --workspace /path/to/repos \
  --include "semcod/*" \
  --command "python -m pytest -q"
```

### Or use Taskfile

```bash
task                          # list all tasks (40+)
task install                  # pip install -e .
task ci                       # local CI equivalent: lint + tests
task install:tools            # planfile, regix, redup, vallm, prefact, pfix
task tickets:next             # highest-priority open ticket
task queue:run                # execute one runnable planfile queue task
task queue:dry-run            # preview the next planfile queue task
task queue:watch              # watch planfile WebSocket queue events
task quality:regix            # regression metrics gate
task quality:redup            # duplicate detection
task template:install         # bootstrap configs in current dir
task webhook:run              # start healing-webhook on :8810
```

Full examples: [`docs/cli-examples.md`](./docs/cli-examples.md)

## Planfile queue runner

`koru` can execute one runnable `planfile` ticket at a time, or drain
the entire queue in a single call:

```bash
# Single tick (legacy, default):
koru --queue --project . --actor koru-shell

# Drain everything:
koru --queue --project . --loop --max-iterations 50

# Drain shell tickets AND answer humans interactively in one shot:
koru --queue --project . --loop --interactive --actor c2004-koru

# Preview without execution:
koru --queue --project . --dry-run
```

By default koru uses the current Python environment's `planfile` module when
available, then falls back to the `planfile` executable in `PATH`. To pin a
specific command:

```bash
KORU_PLANFILE_CMD="python -m planfile.cli" koru --queue --project .
```

Supported executor kinds:

- `executor.kind: shell` — claim, start, run `inputs.script` or `executor.handler`,
  then complete or fail the ticket.
- `executor.kind: api` — claim, start, call `inputs.api_endpoint` (or
  `executor.handler`) with `inputs.api_method`, `inputs.api_headers`,
  `inputs.api_body`, then complete or fail the ticket.
- `executor.kind: llm` — claim, start, POST `inputs.prompt` to an
  OpenAI-compatible chat-completion endpoint (default OpenRouter),
  capture the assistant's text as the ticket's `stdout`, and store
  `llm_model` + token `usage` in the result-json. Configure via
  `OPENROUTER_API_KEY` / `OPENAI_API_KEY` / `KORU_LLM_ENDPOINT`. See
  [`docs/cli-examples.md`](docs/cli-examples.md) for the full schema.
- `executor.kind: human` — print the prompt and leave the task for
  an operator. With `--interactive`, koru collects the answer on
  stdin (multi-line, Ctrl-D submits, Ctrl-C cancels) and completes
  the ticket itself.

The remaining executor kind (`mcp`) is intentionally reported as
unsupported until its adapter is wired (Phase 5).

Minimal API ticket:

```yaml
tickets:
  PLF-010:
    name: "Notify deployment API"
    status: open
    priority: high
    executor:
      kind: api
      mode: automatic
    execution:
      queue: default
      state: ready
    inputs:
      api_endpoint: "http://localhost:8810/probe-failure"
      api_method: POST
      api_headers:
        content-type: application/json
      api_body:
        source: koru
```

To watch queue changes streamed by the `planfile` API:

```bash
uvicorn planfile.api.server:app --reload --port 8000
koru --watch --ws-url ws://localhost:8000/ws
task queue:watch
```

For transparent management-layer logs in a dashboard, point koru at the
planfile event-ingest endpoint:

```bash
export KORU_EVENTS_URL="http://localhost:8000/events/ingest"
koru --queue --project . --dry-run
```

When configured, koru emits best-effort `management.event` entries for
`koru.bootstrap`, `koru.queue`, `koru.watch`, and repository loop runs. This is
intended for UI surfaces such as planfile's **Live Events** panel and does not
change queue execution semantics.

`watch` support uses the optional `websockets` package. Install it with:

```bash
pip install "koru[watch]"
```

## Filesystem contract

**koru never writes outside `<project>/.planfile/`.** This is a hard
rule for the production code path; any deviation is a bug.

```
<project>/.planfile/
├── config.yaml                  # planfile-owned (project config)
├── sprints/
│   └── current.yaml             # planfile-owned (source of truth)
└── .koru/                       # koru-owned, opt-in, gitignore-friendly
    ├── runs/                    # one log per `koru --queue` invocation
    ├── prompts/                 # captured `--interactive` answers
    ├── llm-cache/               # opt-in LlmExecutor response cache
    └── README.md                # in-place explainer
```

The `.koru/` subtree is **non-authoritative** — planfile sprint YAML is
always the source of truth. Anything in `.koru/` can be deleted at any
time without losing ticket state. Recommended `.gitignore` entry:

```gitignore
.planfile/.koru/
```

The path helpers exposed by `koru.runtime` (`runtime_dir`, `runs_dir`,
`new_run_id`, `ensure_runs_dir`) are pure resolvers — they only touch
disk via `ensure_runs_dir`, so a `--dry-run` invocation leaves zero
trace.

**`/tmp/` policy.** Production code does not use `/tmp/`. Test
fixtures (`tests/` and `tests/e2e/*.sh`) are the only allowed
`/tmp/` users and MUST be PID-scoped (`/tmp/koru-*-$$`) with
`trap cleanup EXIT` so a failed run leaves nothing behind. If you find
koru artefacts elsewhere, please open an issue.

## Documentation

The full documentation lives in [`docs/`](./docs/):

- **[`docs/agent-guide.md`](./docs/agent-guide.md)** — full LLM agent
  workflow guide (originally written for `maskservice/c2004` Windsurf
  agent, generalized for any koru-driven repo). Covers ticket workflow,
  validation gates, anti-patterns, troubleshooting.
- **[`docs/planfile-llm-guide.md`](./docs/planfile-llm-guide.md)** —
  ticket-driven development with `planfile` CLI.
- **[`docs/planfile-execution-gateway.md`](./docs/planfile-execution-gateway.md)** —
  design for turning `planfile.yaml` into the execution gateway for shell,
  MCP, API, human, and LLM tasks.
- **[`docs/llm-tools/`](./docs/llm-tools/)** — per-tool docs and install
  scripts:
  - [`planfile/`](./docs/llm-tools/planfile/) — ticket backlog
  - [`regix/`](./docs/llm-tools/regix/) — Python regression metrics
  - [`redup/`](./docs/llm-tools/redup/) — duplicate detection
  - [`redsl/`](./docs/llm-tools/redsl/) — OpenRouter auto-refactor (opt-in)
  - [`vallm/`](./docs/llm-tools/vallm/) — multi-tier patch validator
  - [`prefact/`](./docs/llm-tools/prefact/) — proactive LLM-aware linter
  - [`pfix/`](./docs/llm-tools/pfix/) — auto-fix imports
  - [`llx/`](./docs/llm-tools/llx/) — LLM CLI wrapper
  - [`sumd/`](./docs/llm-tools/sumd/) — LLM refactor snapshots (SUMR.md)
  - [`redeploy/`](./docs/llm-tools/redeploy/) — multi-target deployment (markpact specs)
  - [`goal/`](./docs/llm-tools/goal/) — automated git push + smart commits + release workflow
  - [`doql/`](./docs/llm-tools/doql/) — declarative infrastructure-as-code (.doql files)
  - [`costs/`](./docs/llm-tools/costs/) — zero-config AI cost tracker per commit
  - [`op3/`](./docs/llm-tools/op3/) — layered infrastructure observation (multi-layer scan)
  - [`toonic/`](./docs/llm-tools/toonic/) — universal TOON format platform (LLM-friendly compact files)
  - [`protogate/`](./docs/llm-tools/protogate/) — migration tool dla legacy systems (bounded slices)
  - [`rebuild/`](./docs/llm-tools/rebuild/) — code evolution intelligence (git history walker)
  - [`mdflow/`](./docs/llm-tools/mdflow/) — markdown dependency analyzer
  - [`metrun/`](./docs/llm-tools/metrun/) — execution intelligence + bottleneck detection
  - [`aider/`](./docs/llm-tools/aider/) — pair-programming agent
  - [`claude-code/`](./docs/llm-tools/claude-code/) — Anthropic agent
  - [`cursor/`](./docs/llm-tools/cursor/) — Cursor IDE setup
  - [`testql/`](./docs/llm-tools/testql/) — declarative HTTP tests

## Templates (config snippets)

Reference configurations from the c2004 reference deployment:

- [`templates/pyqual.yaml.template`](./templates/pyqual.yaml.template) — full pipeline orchestrator
- [`templates/redup.toml.template`](./templates/redup.toml.template) — duplicate budget
- [`templates/redsl.yaml.template`](./templates/redsl.yaml.template) — refactor lane config
- [`templates/regix.yaml.template`](./templates/regix.yaml.template) — regression metrics

## Reference deployment

[`maskservice/c2004`](https://github.com/maskservice/c2004) — the original
production-grade closed-loop refactor system that koru generalizes.
Real metrics from c2004 (May 2026):

- **88% size reduction** in compatibility shim files (14640 → 1812 bytes)
- **8 stale alerts auto-closed** in single workflow run
- **0 errors / 42 improvements** per regix gate after refactor
- **58/58 endpoint health probes** post-migration

## License

Licensed under Apache-2.0.
