# koru

<img src="maori-koru-bold-400w.png" width="200" alt="koru">

## AI Cost Tracking

![PyPI](https://img.shields.io/badge/pypi-costs-blue) ![Version](https://img.shields.io/badge/version-0.1.17-blue) ![Python](https://img.shields.io/badge/python-3.9+-blue) ![License](https://img.shields.io/badge/license-Apache--2.0-green)
![AI Cost](https://img.shields.io/badge/AI%20Cost-$1.84-orange) ![Human Time](https://img.shields.io/badge/Human%20Time-12.0h-blue) ![Model](https://img.shields.io/badge/Model-openrouter%2Fqwen%2Fqwen3--coder--next-lightgrey)

- 🤖 **LLM usage:** $1.8367 (39 commits)
- 👤 **Human dev:** ~$1205 (12.0h @ $100/h, 30min dedup)

Generated on 2026-05-11 using [openrouter/qwen/qwen3-coder-next](https://openrouter.ai/qwen/qwen3-coder-next)

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

## Quick start — start an LLM session in 3 commands

```bash
cd /path/to/your/project
pip install koru
koru --init                # 1. set up .planfile/ + .koru/ + .gitignore
koru                       # 2. print the LLM brief (paste into Cascade/Cursor/aider)
koru --queue --loop        # 3. drain the queue (the agent works on each ticket)
```

That is the entire onboarding. **`koru` (no args) is the command an LLM
agent runs at the start of every session** — the markdown brief it
prints contains the active ticket, the policy gates, and the exact
`planfile ticket …` commands the agent is allowed to use. Nothing
else needs to be memorised.

If the project is not initialised yet, `koru` (no args) detects this
and prints a **⚠ Setup required** section with the exact `koru --init`
command to run — the LLM never has to guess.

## Diagnostics — `koru --doctor`

When something feels off (LLM stuck, queue runner refusing, policy
not taking effect), run:

```bash
koru --doctor                 # human-readable PASS/WARN/FAIL list
koru --doctor --format json   # machine-readable for the LLM itself
```

The doctor probes 8 things and never writes anything: `git_repo`,
`planfile_binary`, `planfile_config`, `planfile_sprints`,
`runtime_dir`, `policy_yaml`, `gitignore`, `ci_command`. Exit code is
`1` if any check fails, `0` if only warnings (warnings are advisory).
Use it after `koru --init` and whenever a session starts mis-behaving.

Natural-language intake and housekeeping are built in:

```bash
koru task "Dodaj feature importu raportów"
koru agent --list          # show Windsurf/Cursor/Claude Code/aider/OpenRouter lanes
koru agent                 # print and save the current LLM handoff prompt
koru agent --launch        # launch the best available CLI agent when possible
koru scan                  # auto-generate tickets from repo signals (TODOs, pytest errors)
koru scan --apply          # create the proposed tickets in planfile
koru gc                    # preview stale tickets eligible for cleanup
koru gc --apply            # delete old done/failed/blocked tickets
koru gate authorize PLF-070 --mode advisory --reason "..."  # record a gate waiver
```

The no-args `koru` prompt includes detected project markers
(`pyproject.toml`, `package.json`, `Taskfile.yml`, `.windsurf/`, `.cursor/`,
`.planfile/`), available LLM/IDE lanes, the recommended agent, the active
ticket, and the exact lifecycle commands the agent may use.

## Two operational modes

| Mode | When | What runs |
|---|---|---|
| **Default: IDE-native** | normal ticket work, no external API | Windsurf/Cursor LLM + `task tickets:next` + regix/pytest |
| **Opt-in: OpenRouter automation lane** | infra smoke tests, headless auto-fix, scheduled runs | `redsl improve`, `llx fix`, `vallm validate --semantic` (all use OpenRouter) |

## Install (editable)

```bash
pip install -e .
```

## Multi-repo loop mode

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

## Queue garbage collection — `koru gc`

Over time, completed and failed tickets accumulate in the sprint YAML.
`koru gc` cleans them up:

```bash
koru gc                              # dry-run: preview what would be removed
koru gc --apply                      # actually delete stale tickets
koru gc --max-age 7                  # only keep tickets younger than 7 days
koru gc --keep-last 5                # always keep the 5 newest done tickets
koru gc --status done,failed         # only clean these statuses (default: done,failed,blocked)
koru gc --no-archive                 # skip JSONL archive before deletion
koru gc --format json                # machine-readable output
```

Before deletion, tickets are archived to
`.planfile/.koru/gc/gc-YYYYMMDD-HHMMSS.jsonl` (disable with `--no-archive`).
The `--keep-last N` flag protects the N most recently finished tickets per
status even when they exceed `--max-age`.

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
    ├── gc/                      # JSONL archives from `koru gc --apply`
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

## LLM agent contract — koru as the gate

When an LLM agent (Cascade, Cursor, aider, claude-code, local model, …)
drives a koru-managed project, it must **read its instructions from
koru, not from the human chat**.

The agent's first command in every session is just `koru` — the
markdown brief that comes back is the entire contract. If the project
has never been initialised, the brief leads with **⚠ Setup required**
and the exact `koru --init` command. The contract is delivered by:

```bash
koru --context --project .                     # JSON brief (machine-readable)
koru --context --project . --format markdown   # Markdown handoff (paste-to-IDE)
koru --context --project . --ticket PLF-074    # brief for a specific ticket
```

The brief contains everything an autonomous agent needs to act safely:

- **the next runnable ticket** (or one named via `--ticket`) — id,
  name, status, files in scope, prompt, executor kind;
- **the resolved policy** — explicit booleans for every git operation
  the agent might attempt;
- **environment fingerprint** — git branch, dirty state, remote,
  whether planfile is initialised in the project;
- **imperative rules** — copy-paste-able `DO NOT …` lines so even a
  weak model can compare any candidate command to a checklist;
- **self-service vocabulary** — concrete `planfile ticket {claim,start,
  complete,fail,input}` invocations with the active ticket id pre-filled.

### Safe-by-default policy

The policy lives at `<project>/.planfile/.koru/policy.yaml`. **All
gates default to the most restrictive value.** A missing or malformed
file falls back to defaults — corruption can never silently loosen
the policy.

| gate | default | meaning |
|---|---|---|
| `allow_commit` | `false` | the agent does NOT run `git commit` |
| `allow_push` | `false` | the agent does NOT run `git push` |
| `allow_branch_create` | `false` | no `git checkout -b`, `git branch X`, `git switch -c` |
| `allow_branch_switch` | `false` | no `git checkout <ref>`, `git switch <branch>` |
| `allow_tag` | `false` | no `git tag` |
| `allow_destructive_shell` | `false` | blocks `rm -rf /`, `dd`, `mkfs`, force-pushes, … |
| `require_planfile_lifecycle` | `true` | every state change goes through `planfile ticket *` |
| `require_ci_pass_before_complete` | `true` | the agent verifies CI exit 0 before `ticket complete` |

The agent **bounces off CI/CD and koru**: it cannot commit, cannot
push, cannot mutate planfile state outside the CLI vocabulary the
brief gave it. To make a change that ships, the agent has exactly two
exits: complete the ticket (humans/CI take it from there) or call
`planfile ticket input <id> --prompt "<question>"` and stop.

### Universal quality gates (built-in)

Every `koru --init` creates a **universal CI command** that automatically
detects and runs quality tools when they're available:

```bash
# Runs on every ticket completion (if require_ci_pass_before_complete=true)
echo "=== Universal Quality Gates ==="

# 1. Project tests (auto-detects runner)
# - task test (Taskfile)
# - pytest -q (Python)
# - npm test (Node.js)
# - make test (Makefile)

# 2. TestQL E2E scenarios (when *.testql.toon.yaml files exist)
testql suite --pattern "*.testql.toon.yaml" --output console --fail-fast

# 3. WUP dependency analysis (when wup.yaml exists)
wup status

# 4. Regix quality gates (when regix.yaml exists)
regix gates
```

**Tools are gracefully skipped** if not installed or configured — no manual
setup required for basic quality control. The universal gates ensure:

- **Consistent quality** across all koru projects
- **Automatic regression testing** with testQL scenarios
- **Zero configuration** for basic validation
- **Adaptive detection** of project-specific tooling

### Auto-promotion & auto-repair for blocking tickets

Koru automatically manages workflow priorities to prevent deadlocks:

#### **Auto-promotion**
- Tickets that block others are **automatically promoted to `critical` priority**
- This ensures blocking issues are resolved first
- Promotion happens on every `koru --context` call

#### **Auto-repair mode**
- Critical tickets receive **special instructions for LLM agents**:
  - "AUTO-REPAIR MODE: Fix this issue immediately to unblock the workflow"
  - "Do NOT ask for human input unless absolutely necessary"
  - "Use all available tools and knowledge to resolve the blocking issue"
  - "After fixing, immediately call `planfile ticket complete`"

#### **Workflow**
1. **Main task** → encounters blocking issue
2. **Blocking ticket** created → auto-promoted to `critical`
3. **LLM agent** receives auto-repair instructions
4. **Issue resolved** → main task unblocked
5. **Workflow continues** without manual intervention

### Bug-first priority system

Koru ensures bugs are always fixed before features when priorities are equal:

#### **Automatic bug promotion**
- Bugs get **priority boost** within their category:
  - `low` → `normal`
  - `normal` → `high` 
  - `high` → `critical`
  - `critical` stays `critical`
- Promotion happens automatically on every `koru --context` call
- Only tickets with `bug` label are promoted

#### **Priority hierarchy**
```
critical (blocking tickets + high-priority bugs)
├── high bugs (promoted from normal)
├── high features
├── normal bugs (promoted from low)
├── normal features
├── low bugs
└── low features
```

#### **Benefits**
- **Bug-first workflow** — stability issues resolved before new features
- **Automatic triage** — no manual priority adjustments needed
- **Predictable execution** — bugs always jump ahead of same-priority features
- **Quality assurance** — prevents feature development while bugs exist

### Integration with planfile

Koru's priority system is **fully integrated with planfile**:

#### **Shared priority logic**
- **Same promotion rules** applied in both koru and planfile core
- **Consistent ticket ordering** across all planfile commands
- **Unified bug-first workflow** throughout the ecosystem

#### **Planfile commands enhanced**
- `planfile ticket next` — respects bug-first priorities
- `planfile ticket list` — shows promoted priorities
- `planfile queue` — processes bugs before features
- **All planfile operations** use the same priority hierarchy

#### **Seamless workflow**
1. **Koru auto-promotes** tickets on `--context` call
2. **Planfile respects** promoted priorities natively
3. **Consistent execution** whether using koru or planfile directly
4. **No conflicts** — both systems use identical priority logic

### Loosening the policy

Editing `<project>/.planfile/.koru/policy.yaml` is the **only** way to
relax a default. There is no CLI flag for it — that is a deliberate
choice so any loosening is reviewable in git history.

```yaml
# .planfile/.koru/policy.yaml
llm:
  allow_commit: false       # never (recommended)
  allow_push: false         # never (recommended)
  allow_branch_create: true # opt-in: agent may create feature branches
ci:
  command: pytest -q        # override universal gates (optional)
  timeout_seconds: 300
notes:
  - "Always run `task lint` before `ticket complete`."
  - "Never edit migrations under alembic/versions/."
```

### Run logs

`koru --queue` and `koru --queue --loop` write a JSON-Lines log per run
to `<project>/.planfile/.koru/runs/queue-<timestamp>-<pid>.jsonl`:

```jsonl
{"type":"run.start","run_id":"queue-…","mode":"loop","actor":"koru","pid":12345,…}
{"type":"iteration","iteration":1,"ticket_id":"PLF-074","status":"completed",…}
{"type":"iteration","iteration":2,"ticket_id":"PLF-075","status":"failed",…}
{"type":"run.end","iterations":2,"completed":["PLF-074"],"failed":["PLF-075"],…}
```

`--dry-run` skips the writer (preserves "dry-run leaves zero trace").
`--no-log` opts out explicitly. Logs are non-authoritative — planfile
sprint YAML remains the source of truth.

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
