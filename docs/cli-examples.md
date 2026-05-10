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

### Mark done

```bash
task tickets:done TID=PLF-052
```

### Export ticket as LLM-ready prompt

```bash
task tickets:export TID=PLF-052
# → Generates a prompt with full context for pasting into Claude/GPT/etc.
```

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
