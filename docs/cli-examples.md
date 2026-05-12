# CLI Examples — koru

This document shows real-world usage patterns for koru CLI and Taskfile.
For the underlying tools (`planfile`, `regix`, `redup`, `vallm`, ...) see
[`llm-tools/`](./llm-tools/).

## Table of contents

- [Quick start](#quick-start)
- [Installation](#installation)
- [Closed-loop automation](#closed-loop-automation)
- [Quality gates](#quality-gates)
- [Ticket workflow](#ticket-workflow)
- [Templates (config bootstrapping)](#templates-config-bootstrapping)
- [Healing-webhook (alert → ticket service)](#healing-webhook)
- [Common scenarios](#common-scenarios)

---

## Quick start

```bash
# 1. Install koru
pip install -e .

# 2. Install underlying tools
task install:tools

# 3. Bootstrap a new repo with config templates
cd /path/to/new-repo
task -d /path/to/koru template:install

# 4. Edit configs to fit your project
$EDITOR pyqual.yaml redup.toml regix.yaml

# 5. Start using
task -d /path/to/koru tickets:next
task -d /path/to/koru quality:regix
```

---

## Installation

### From source (editable)

```bash
git clone https://github.com/semcod/koru.git
cd koru
pip install -e .
task install:tools     # planfile, regix, redup, vallm, prefact, pfix
```

### From PyPI (when published)

```bash
pip install koru
```

### Verify

```bash
task version           # → koru v0.1.1
task                   # → list all tasks
koru --help            # CLI help
```

---

## Closed-loop automation

The core koru CLI runs a command across multiple repositories and
**retries on failures in a closed loop**.

### Basic loop

```bash
# Run pytest across all repos in /workspace
koru \
  --workspace /workspace \
  --include "**/repo-*" \
  --command "pytest -q"
```

### Via Taskfile

```bash
task loop WORKSPACE=/workspace INCLUDE='**/repo-*' COMMAND='pytest -q'

# Shortcut: pytest in current dir
task loop:test

# Shortcut: ruff in current dir
task loop:lint
```

### Real-world example (semcod org)

```bash
# Run regix gate across all semcod/* repos, retry on failure
koru \
  --workspace ~/github \
  --include "semcod/*" \
  --command "regix gate" \
  --max-rounds 3
```

---

## Quality gates

LLM-free local validation. Use these before committing.

### regix (regression metrics)

```bash
# Direct
regix gate

# Via koru
task quality:regix
```

Output:
```
Summary: 0 error(s), 0 warning(s), 42 improvement(s)
Gates: ✓ PASS
```

### redup (duplicate detection)

```bash
# Direct
redup scan . --min-lines 10 --min-sim 0.85

# Via koru
task quality:redup

# With budget enforcement (uses scripts/redup-check.sh)
task quality:redup:check
```

### vallm (patch validator)

Tier 1 (syntax only — no LLM):

```bash
vallm check -f path/to/file.py
# → Score: 1.00, PASS
```

Tier 2+ (multi-tier with LLM-as-judge — uses OpenRouter):

```bash
# Single file
task quality:vallm FILE=backend/app/foo.py

# With semantic check (LLM)
export OPENROUTER_API_KEY=sk-or-v1-xxxxx
task quality:vallm:semantic FILE=backend/app/foo.py
```

---

## Ticket workflow

koru integrates with `planfile` for ticket-driven development.

### List and show tickets

```bash
# Highest-priority open ticket
task tickets:next

# All open tickets
task tickets:list

# Specific ticket details
task tickets:show TID=PLF-052
```

### Scan the repo and ignore local noise via `.koruignore`

```bash
# Dry-run suggestions
koru scan

# Apply suggestions as planfile tickets
koru scan --apply
```

If local probe files create noisy TODO-marker suggestions, add a
project-root `.koruignore` file (one glob per line):

```text
# Ignore temporary scan probes
.koru_scan_*.py
generated/
```

`koru scan` respects `.koruignore` for TODO/FIXME marker scanning.

### Mark done

```bash
task tickets:done TID=PLF-052
```

### Export ticket as LLM-ready prompt

```bash
task tickets:export TID=PLF-052
# → Generates a prompt with full context for pasting into Claude/GPT/etc.
```

### Bootstrap a project from a flat pipeline YAML

koru bridges two pipeline formats:

- **Flat (authoring)** — top-level `tasks:` list, used in
  `examples/bootstrap.planfile.yaml` and aligned with
  `docs/planfile-execution-gateway.md`.
- **Nested (runtime)** — planfile-native layout under
  `.planfile/sprints/<sprint>.yaml`, read by `planfile` CLI and
  `koru --queue`.

The `--bootstrap` flag converts the flat format into the runtime layout:

```bash
# Import a flat pipeline into a fresh project
mkdir -p /tmp/new-project && cd /tmp/new-project && git init -q
koru --bootstrap \
     --from /path/to/koru/examples/bootstrap.planfile.yaml \
     --project . \
     --sprint current
# → koru bootstrap: ✓ imported
# → tickets: 15 imported
# → config:  .planfile/config.yaml created
# → sprint:  .planfile/sprints/current.yaml created

# Drain the queue task by task
koru --queue --project .                # runs first ready ticket
koru --queue --project . --dry-run      # preview next ticket only
koru --queue --project . --actor agent-x  # set actor when claiming
```

Validation rules (see `koru.bootstrap.validate_flat_pipeline`):

- Every task needs `id`, `name` (or `title`), and `executor.kind`
  ∈ `{shell, human, llm, api, mcp}`
- `priority` ∈ `{critical, high, normal, low}` (NOT `medium`)
- `status` ∈ `{open, in_progress, review, done, blocked}`
- `execution.state` ∈
  `{pending, ready, running, waiting_input, done, failed, skipped}`
- `blocked_by` references must resolve and the DAG must be acyclic

If validation fails, `koru --bootstrap` exits non-zero and prints every
error so they can be fixed in a single pass:

```text
koru bootstrap: examples/bootstrap.planfile.yaml: validation failed
  - KORU-B-022: priority: 'medium' not in ['critical', 'high', 'low', 'normal']
```

To overwrite an existing sprint file, pass `--force`.

### Answer human-input tickets interactively

When the next runnable ticket has `executor.kind=human`, koru would
normally exit with `status=waiting_input` and leave the ticket for a
human operator to handle via `planfile ticket complete`. With
`--interactive`, koru pauses to collect the answer on stdin and
completes the ticket itself:

```bash
koru --queue --project . --interactive --actor c2004-koru
# 📝 PLF-067 — human input needed
# ────────────────────────────────────────────────────────────
# Confirm that this refactor wave should only move reusable
# frontend/backend code to packages/ or shared/, while
# connect-*/** keeps module-specific UI, routes, scenarios,
# and runtime wiring.
# ────────────────────────────────────────────────────────────
# Type your answer (Ctrl-D to submit, Ctrl-C to cancel):
# > Yes — confirmed. Only reusable code to packages/, the
# > connect-*/ tree stays module-specific for now.
# > [Ctrl-D]
# koru queue: status=completed ticket=PLF-067 executor=human
```

The recorded note captures `actor`, the original `prompt`, and the
verbatim `answer`, all visible later via `planfile ticket show PLF-067`.

Behaviour matrix:

| Flag combo | Effect on `human` ticket |
|---|---|
| (default) | exit with `status=waiting_input`, ticket untouched |
| `--interactive` | open stdin prompt, complete on submit, leave on cancel |
| `--interactive --dry-run` | no prompt, no execution — still `waiting_input` (safety) |

You can also pipe the answer non-interactively (handy for scripted CI):

```bash
echo "Yes, proceed with reusable-only scope." | \
  koru --queue --project . --interactive --actor ci-bot
```

### Drain the queue with `--loop`

`koru --queue` runs **one** ticket per invocation. For long pipelines
(e.g. the 15-task bootstrap example), use `--loop` to drain the queue
in a single command:

```bash
koru --queue --project . --loop --max-iterations 50
#   [  1] ✓ completed              KORU-B-001     (shell)
#   [  2] ✓ completed              KORU-B-002     (shell)
#   [  3] ✓ completed              KORU-B-010     (shell)
#   [  4] ✓ completed              KORU-B-011     (shell)
#   [  5] ⏸ waiting_input          KORU-B-020     (human)
#
# koru queue loop: iterations=5 completed=4 failed=0 waiting=1 last_status=waiting_input
#   completed: KORU-B-001, KORU-B-002, KORU-B-010, KORU-B-011
#   waiting:   KORU-B-020
```

The loop terminates on:

| `last_status` | Reason | Exit code |
|---|---|---|
| `idle` | Queue is fully drained | 0 |
| `waiting_input` | A `human` ticket needs a person | 0 |
| `unsupported_executor` | Encountered `llm`/`api`/`mcp` (not yet wired) | 1 |
| `planfile_error` | `planfile ticket next` itself failed | 1 |
| `failed` (max-iterations hit) | Cap reached without idling | 1 |

**`failed` tickets do NOT halt the loop** — koru records them and moves
on. This matches the design that one bad ticket should not block the
rest of the pipeline.

### Drain shell tickets AND answer humans in one shot

Compose `--loop` with `--interactive` to get the most useful agent UX:

```bash
koru --queue --project . --loop --interactive --actor c2004-koru
# … runs every shell ticket immediately,
# … pauses on each human ticket so you can type the answer,
# … and continues until idle or you Ctrl-C.
```

Or pipe answers in for scripted runs:

```bash
{ echo "yes — proceed"; echo "sk-or-v1-MY-KEY"; } | \
  koru --queue --project . --loop --interactive --actor ci-bot
```

### Run unattended autoloop (scan + queue + autopilot)

After `pip install koru`, the shortest setup is now one command:

```bash
cd /path/to/repo
koru autonomous up
```

Useful flags:

```bash
# one-cycle smoke check
koru autonomous up --max-cycles 1 --sleep-seconds 0

# explicit actor + queue
koru autonomous up --actor koru-bot --queue-name default

# disable autopilot injection (queue/scan only)
koru autonomous up --no-autopilot

# inspect AI tool coverage from registry (phase 1)
koru tools detect
koru tools detect --format json
koru tools detect --registry docs/ai-tool-registry-2026.yaml
```

For terminal-driven autonomy, use the built-in wrapper script via Taskfile:

```bash
# Continuous loop:
# 1) koru scan --apply
# 2) koru --queue --loop
# 3) koru autopilot drive "continue with the next ticket"
# 4) sleep 120s
task queue:autoloop
```

Useful overrides:

```bash
# Faster cadence (every 30s) and larger queue pass
task queue:autoloop SLEEP_SECONDS=30 MAX_ITERATIONS=100

# Disable autopilot ping (queue-only daemon mode)
task queue:autoloop ENABLE_AUTOPILOT_DRIVE=false

# Restrict to one execution queue
task queue:autoloop QUEUE_NAME=default

# Allow interactive handling of human tickets inside the loop
task queue:autoloop ENABLE_INTERACTIVE=true
```

Under the hood this runs `scripts/koru-autoloop.sh` (env-driven), so you
can also launch it directly:

```bash
PROJECT=/path/to/repo ACTOR=c2004-koru SLEEP_SECONDS=60 \
  bash scripts/koru-autoloop.sh
```

### Auto-answer tickets with an LLM (`executor.kind=llm`)

Tickets with `executor.kind=llm` are sent to an OpenAI-compatible
chat-completion endpoint — by default OpenRouter
(`https://openrouter.ai/api/v1/chat/completions`). The assistant's
text reply lands in the ticket's `outputs.result`/`stdout`, and token
usage is stored in `outputs.result.llm_usage`.

Minimal LLM-backed ticket:

```yaml
- id: PLF-067-LLM
  name: "Decide refactor scope"
  status: open
  priority: high
  executor:
    kind: llm
    mode: automatic
  execution:
    queue: c2004-refactor
    state: ready
  inputs:
    llm_model: openai/gpt-4o-mini
    prompt: |
      Should this refactor wave move only reusable frontend/backend
      code to packages/, while connect-*/** keeps module-specific UI,
      routes, scenarios, and runtime wiring? Answer 'yes' or 'no'
      with one short sentence of rationale.
    # Optional: structured response (sent as response_format json_schema)
    response_schema:
      type: object
      required: [decision, rationale]
      properties:
        decision: {type: string, enum: [yes, no]}
        rationale: {type: string}
```

Required environment:

```bash
# OpenRouter (default endpoint):
export OPENROUTER_API_KEY="sk-or-v1-..."

# Or use OpenAI directly via inputs.llm_endpoint or KORU_LLM_ENDPOINT:
export OPENAI_API_KEY="sk-..."
export KORU_LLM_ENDPOINT="https://api.openai.com/v1/chat/completions"

# Optional OpenRouter ranking metadata:
export KORU_LLM_HTTP_REFERER="https://github.com/your-org"
export KORU_LLM_X_TITLE="koru-c2004-refactor"
```

Run it like any other queue task:

```bash
koru --queue --project . --actor c2004-koru
# koru queue: status=completed ticket=PLF-067-LLM executor=llm
# llm openai/gpt-4o-mini

# Or drain everything (shell + llm + human via --interactive) in one shot:
koru --queue --project . --loop --interactive --actor c2004-koru
```

Supported `inputs.*` fields:

| Field | Default | Purpose |
|---|---|---|
| `prompt` | (required) | User message; falls back to `description` then `name` |
| `llm_model` | `openai/gpt-4o-mini` | OpenRouter or OpenAI model ID |
| `llm_endpoint` | OpenRouter | Override per-ticket (or via `executor.handler`) |
| `system_prompt` | – | Sent as the system message |
| `llm_max_tokens` | – | Cap on response length |
| `llm_temperature` | `0.0` | Determinism (0 = greedy) |
| `response_schema` | – | JSON Schema → forces structured JSON output |
| `llm_timeout_seconds` | `60.0` | Per-call timeout |

Safety: when neither `OPENROUTER_API_KEY` nor `OPENAI_API_KEY` is set,
koru refuses the call and returns `status=failed` with a clear message
("OPENROUTER_API_KEY is not set — refusing to call …"). No silent
fallthrough to a human prompt — the failure is logged on the ticket via
`planfile ticket fail`, so it shows up in dashboards.

### Healing-webhook integration (auto-tickets)

When alertmanager fires (e.g., `EndpointDown`), the healing-webhook
auto-creates a planfile ticket. Run the agent loop to consume them:

```bash
while true; do
  TID=$(planfile ticket next --format yaml | yq '.id')
  if [ "$TID" = "null" ]; then break; fi
  task tickets:show TID=$TID
  # ... agent edits code ...
  task quality:regix
  task tickets:done TID=$TID
done
```

---

## Templates (config bootstrapping)

koru ships reference configs from the c2004 production deployment.

### Install all templates

```bash
cd /path/to/your-repo
task -d /path/to/koru template:install
```

This copies:
- `pyqual.yaml` — full pipeline orchestrator
- `redup.toml` — duplicate budget config
- `redsl.yaml` — refactor lane config
- `regix.yaml` — regression metrics
- `llx.toml` / `llx.yaml` — LLM CLI wrapper
- `prefact.yaml` — proactive linter

### Install specific template

```bash
task template:install:single TPL=redup.toml
task template:install:single TPL=pyqual.yaml
```

### Install docker-compose quality stack

```bash
task template:install:compose
# → Copies docker-compose.quality.yml with redup-watch, redsl-watch services
```

### List available templates

```bash
task template:list
```

---

## Healing-webhook

A generic alertmanager → planfile ticket service.

### Run locally

```bash
task webhook:run
# → Listens on http://localhost:8810
# → Endpoints: /alert (POST), /healthz (GET), /metrics (GET)
```

### Run in Docker

```bash
task webhook:docker:build
task webhook:docker:run
```

### Smoke test

```bash
# Send fake alertmanager payload
task webhook:test

# Or manually:
curl -X POST http://localhost:8810/alert \
  -H "Content-Type: application/json" \
  -d '{
    "alerts": [{
      "status": "firing",
      "labels": {"alertname": "TestAlert", "severity": "warning"},
      "annotations": {"summary": "Smoke test from koru"}
    }]
  }'
# → Returns: {"created": ["PLF-XXX"]}
```

---

## Common scenarios

### Scenario 1: Bootstrap a new project

```bash
cd /path/to/new-project

# 1. Install koru tools globally
pip install koru
task -t /path/to/koru/Taskfile.yml install:tools

# 2. Copy config templates
task -t /path/to/koru/Taskfile.yml template:install

# 3. Adjust configs for your project size
$EDITOR redup.toml   # Set max_groups to your baseline + 20%

# 4. Initialize planfile backlog
mkdir -p .planfile/sprints
touch .planfile/sprints/current.yaml

# 5. Run first quality gate
task -t /path/to/koru/Taskfile.yml quality:regix
```

### Scenario 2: Fix a critical alert

```bash
# 1. Check newest ticket (likely from healing-webhook)
task tickets:next
# → PLF-052 critical: EndpointDown /api/v3/data/tables

# 2. Read full context
task tickets:show TID=PLF-052

# 3. Reproduce
curl -sS http://localhost:8101/api/v3/data/tables -w '%{http_code}'

# 4. Edit code (use your IDE's LLM)
# ... agent makes the patch ...

# 5. Validate locally (LLM-free)
task quality:regix
task quality:redup:check

# 6. Commit (pre-commit hooks run regix + redup)
git commit -m "fix(api): handle stale connection in /data/tables"

# 7. Mark done
task tickets:done TID=PLF-052
```

### Scenario 3: OpenRouter automation lane (opt-in)

```bash
export OPENROUTER_API_KEY=sk-or-v1-xxxxx

# Validate a tricky patch with LLM-as-judge
task quality:vallm:semantic FILE=backend/app/refactored.py

# Run redsl improve in dry-run on a specific module
REFACTOR_DRY_RUN=true redsl improve packages/shared/foo --max-actions 1

# Run aider for pair-programming
aider --message "Refactor backend/app/protocols.py per PLF-051" backend/app/protocols.py
```

### Scenario 4: Workflow from .windsurf/workflows/

koru ships generic workflow templates for common automation loops:

```bash
task workflow:list
# → aider-docker-autoloop.md, testql-autoloop.md

task workflow:show NAME=testql-autoloop
# → Shows the markdown instructions for the testql-autoloop workflow
```

Copy them to your `.windsurf/workflows/` to use in Windsurf IDE:

```bash
cp /path/to/koru/workflows/testql-autoloop.md .windsurf/workflows/
```

### Scenario 5: Multi-repo refactor across semcod/*

```bash
# Run a refactor command across all semcod/* repos
# (e.g., update Python version requirement)

koru \
  --workspace ~/github/semcod \
  --include "*" \
  --command 'sed -i "s/python_requires=\">=3.11\"/python_requires=\">=3.12\"/" setup.py' \
  --max-rounds 1

# Verify with quality gate
koru \
  --workspace ~/github/semcod \
  --include "*" \
  --command "regix gate"
```

---

## Cheat sheet

```bash
# Show all tasks
task

# Quality gates (LLM-free)
task quality:regix              # regression metrics
task quality:redup              # duplicates
task quality:redup:check        # with budget enforcement
task quality:vallm FILE=foo.py  # syntax/imports/complexity

# Tickets
task tickets:next                       # highest-priority open
task tickets:show TID=PLF-052           # details
task tickets:done TID=PLF-052           # mark done
task tickets:export TID=PLF-052         # LLM-ready prompt

# Templates
task template:list                       # list available
task template:install                    # install all
task template:install:single TPL=foo.bar # install one

# Healing-webhook
task webhook:run                # local
task webhook:docker:build       # build image
task webhook:test               # smoke test

# Closed-loop
task loop:test                  # pytest in current dir
task loop COMMAND='ruff check'  # custom command

# OpenRouter (opt-in)
task quality:vallm:semantic FILE=foo.py
```

---

## Further reading

- [`docs/agent-guide.md`](./agent-guide.md) — full LLM agent workflow
- [`docs/planfile-llm-guide.md`](./planfile-llm-guide.md) — ticket-driven dev
- [`docs/llm-tools/`](./llm-tools/) — per-tool docs
- [`templates/`](../templates/) — copy-paste configs
- [`workflows/`](../workflows/) — IDE workflow markdown
