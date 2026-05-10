# koru


## AI Cost Tracking

![PyPI](https://img.shields.io/badge/pypi-costs-blue) ![Version](https://img.shields.io/badge/version-0.1.1-blue) ![Python](https://img.shields.io/badge/python-3.9+-blue) ![License](https://img.shields.io/badge/license-Apache--2.0-green)
![AI Cost](https://img.shields.io/badge/AI%20Cost-$0.45-orange) ![Human Time](https://img.shields.io/badge/Human%20Time-2.0h-blue) ![Model](https://img.shields.io/badge/Model-openrouter%2Fqwen%2Fqwen3--coder--next-lightgrey)

- 🤖 **LLM usage:** $0.4500 (3 commits)
- 👤 **Human dev:** ~$200 (2.0h @ $100/h, 30min dedup)

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
│                          KORU                                   │
├──────────┬──────────┬──────────┬──────────┬─────────┬──────────┤
│ DETECT   │ PLAN     │ EXECUTE  │ VERIFY   │ HEAL    │ LEARN    │
├──────────┼──────────┼──────────┼──────────┼─────────┼──────────┤
│ redup    │ planfile │ Windsurf │ regix    │ healing │ pyqual   │
│ regix    │ tickets  │ Cursor   │ pytest   │ webhook │ metrics  │
│ TestQL   │ Promet.  │ aider    │ TestQL   │ retry   │ dashboards│
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
task quality:regix            # regression metrics gate
task quality:redup            # duplicate detection
task template:install         # bootstrap configs in current dir
task webhook:run              # start healing-webhook on :8810
```

Full examples: [`docs/cli-examples.md`](./docs/cli-examples.md)

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
