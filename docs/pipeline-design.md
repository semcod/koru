# Koru Pipeline Architecture — Design Document

> **Status:** DRAFT (2026-05-10) — awaiting approval before implementation.
>
> **Scope:** How koru uses `planfile` as a task-queue gate and dispatches
> work to different executor types (shell, LLM, human, API, MCP).

## 1. Problem statement

Current state:
- **planfile** — ticket/task store with GitHub/GitLab/Jira sync, but tasks
  are passive records (no "runner" concept).
- **koru** — closed-loop CLI that runs one command across repos.
- **c2004** — healing-webhook creates tickets, agent reads, agent edits.

What's missing:
- A generic **task dispatcher** — given a ticket, how do we know WHO runs it?
- Support for **non-code tasks** — human decisions, API key inputs, MCP calls.
- **Dependency tree** — tasks that must run before others (`depends_on`).
- **Interactive mode** — shell/web view of the queue with live status.

## 2. Use case driving the design

**"Bootstrap koru in a new project"** — the first real pipeline we need:

```
Task 1: Check if project is a git repo                 [shell, auto]
Task 2: Install koru + underlying tools                [shell, auto]
Task 3: Ask user: "What's your OPENROUTER_API_KEY?"    [human, interactive]
Task 4: Write .env file                                [shell, auto]
Task 5: Ask user: "Which templates to install?"        [human, interactive]
Task 6: Copy selected templates                        [shell, auto]
Task 7: Run regix gate baseline                        [shell, auto]
Task 8: If baseline fails, ask LLM for fix suggestion  [llm, via OpenRouter]
Task 9: Present summary to user                        [human, info]
Task 10: Commit initial config                         [shell, auto]
```

Every task has: `id`, `executor`, `inputs`, `outputs`, `depends_on`, `status`.

## 3. Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    koru CLI (main entry)                         │
├─────────────────────────────────────────────────────────────────┤
│  koru queue              # show queue                            │
│  koru run                # run next task                         │
│  koru run --all          # run whole pipeline                    │
│  koru run TASK-ID        # run specific task                     │
│  koru pipeline load F.yml # import pipeline from yaml            │
│  koru pipeline export    # export to planfile/GitHub/GitLab/...  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    KoruPipeline (orchestrator)                   │
│                                                                   │
│  - Reads planfile.yaml                                           │
│  - Parses koru-tasks (metadata.koru + labels: koru-task)         │
│  - Builds DAG from depends_on                                    │
│  - Picks next runnable task (status=todo, deps=done)             │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Dispatcher                                  │
│                                                                   │
│  Given a KoruTask, looks at task.executor and routes to:         │
└─────────────┬───────────────────────────────────────────────────┘
              │
              ├─── shell   → run bash/subprocess
              ├─── llm     → OpenRouter API call (with .env key)
              ├─── human   → interactive prompt (rich/textual TUI)
              ├─── api     → HTTP request (requests/httpx)
              ├─── mcp     → MCP tool call (future: via mcp-client)
              └─── tool    → known CLI (regix, redup, vallm, ...)
```

## 4. Data model (`KoruTask`)

```python
from pydantic import BaseModel
from typing import Literal, Any
from datetime import datetime

ExecutorType = Literal["shell", "llm", "human", "api", "mcp", "tool"]
TaskStatus = Literal["todo", "blocked", "running", "done", "failed", "skipped"]

class KoruTask(BaseModel):
    # Identity
    id: str                              # e.g. KORU-BOOTSTRAP-001
    title: str
    description: str = ""

    # Dispatch
    executor: ExecutorType               # who runs it
    auto_run: bool = False               # true = run without confirmation

    # Shell / tool executor
    command: str | None = None           # bash command or CLI invocation
    env: dict[str, str] = {}             # extra env vars
    cwd: str | None = None               # working directory

    # LLM executor
    prompt: str | None = None            # prompt to OpenRouter
    model: str | None = None             # e.g. "openai/gpt-4o-mini"
    max_tokens: int = 2000

    # Human executor
    question: str | None = None          # question to show user
    input_type: Literal["text", "password", "choice", "confirm"] | None = None
    choices: list[str] = []              # for input_type=choice

    # API executor
    url: str | None = None
    method: Literal["GET", "POST", "PUT", "DELETE"] = "GET"
    headers: dict[str, str] = {}
    body: dict[str, Any] | None = None

    # MCP executor
    mcp_server: str | None = None        # MCP server name
    mcp_tool: str | None = None          # tool name
    mcp_args: dict[str, Any] = {}

    # Dependencies & flow
    depends_on: list[str] = []           # task IDs that must be done first
    timeout_sec: int = 300

    # I/O schema
    inputs: dict[str, Any] = {}          # values passed in
    outputs: dict[str, Any] = {}         # values produced (files, env, etc.)

    # Runtime state
    status: TaskStatus = "todo"
    assignee: str | None = None          # who picked it up (for tracking)
    started_at: datetime | None = None
    finished_at: datetime | None = None
    result: dict[str, Any] = {}          # stdout, stderr, exit_code, output_value
    error: str | None = None
```

## 5. Storage: planfile.yaml integration

A koru pipeline is stored as a collection of planfile tickets. Each ticket
uses the existing planfile schema + `metadata.koru` extension:

```yaml
# planfile.yaml
schema: "1.1"
project: my-new-project
tasks:
  - id: KORU-001
    title: "Check git repo initialized"
    status: todo
    labels: [koru-task, executor:shell, pipeline:bootstrap]
    metadata:
      koru:
        executor: shell
        command: "test -d .git"
        auto_run: true
        timeout_sec: 5
        depends_on: []

  - id: KORU-002
    title: "Install koru package"
    status: todo
    labels: [koru-task, executor:shell, pipeline:bootstrap]
    metadata:
      koru:
        executor: shell
        command: "pip install koru"
        auto_run: true
        timeout_sec: 120
        depends_on: [KORU-001]

  - id: KORU-003
    title: "Get OPENROUTER_API_KEY from user"
    status: todo
    labels: [koru-task, executor:human, pipeline:bootstrap]
    metadata:
      koru:
        executor: human
        question: "Enter your OPENROUTER_API_KEY (starts with sk-or-v1-...)"
        input_type: password
        outputs:
          env_var: OPENROUTER_API_KEY
        depends_on: [KORU-002]

  - id: KORU-004
    title: "Write .env with API key"
    status: todo
    labels: [koru-task, executor:shell, pipeline:bootstrap]
    metadata:
      koru:
        executor: shell
        command: 'echo "OPENROUTER_API_KEY=${OPENROUTER_API_KEY}" >> .env'
        auto_run: true
        depends_on: [KORU-003]
        inputs:
          OPENROUTER_API_KEY: "@KORU-003.outputs.env_var"  # reference another task's output
```

## 6. Executor contracts

Each executor is a Python class implementing a small protocol:

```python
class Executor(Protocol):
    executor_type: ExecutorType

    def can_auto_run(self, task: KoruTask) -> bool: ...
    def run(self, task: KoruTask, context: RunContext) -> TaskResult: ...
```

### 6.1 ShellExecutor

- Runs `task.command` via subprocess with `task.env` merged into `os.environ`
- Captures stdout/stderr/exit_code → `task.result`
- Respects `task.timeout_sec`

### 6.2 LlmExecutor (opt-in, OpenRouter)

- Loads `OPENROUTER_API_KEY` from `.env` or env
- Calls OpenRouter chat completion with `task.prompt` + `task.model`
- Stores response → `task.result.response`
- If `OPENROUTER_API_KEY` missing → exits with `error="missing_api_key"`
  and marks task `blocked`

### 6.3 HumanExecutor (interactive)

- Uses `rich.prompt` or `questionary` for the question
- Types:
  - `text` → `Prompt.ask(task.question)`
  - `password` → `Prompt.ask(task.question, password=True)`
  - `choice` → menu from `task.choices`
  - `confirm` → yes/no
- Non-interactive mode (`--non-interactive` flag): task marked `blocked`
  with clear message for next human session.

### 6.4 ApiExecutor

- `requests.request(task.method, task.url, headers=..., json=...)`
- Stores response body → `task.result.body`

### 6.5 McpExecutor (future)

- Placeholder: calls into an MCP server via subprocess or stdio
- Will be implemented after basic executors are stable

### 6.6 ToolExecutor

- Wrappers for known CLIs: `regix`, `redup`, `vallm`, `planfile`, etc.
- Abstracts argument parsing and error classification

## 7. CLI UX

### 7.1 `koru queue`

```
$ koru queue
┌─────────────┬─────────────────────────────────────┬──────────┬────────┬─────────┐
│ ID          │ Title                               │ Executor │ Status │ Depends │
├─────────────┼─────────────────────────────────────┼──────────┼────────┼─────────┤
│ KORU-001    │ Check git repo initialized          │ shell    │ done   │ —       │
│ KORU-002    │ Install koru package                │ shell    │ done   │ KORU-001│
│ KORU-003    │ Get OPENROUTER_API_KEY from user    │ human    │ todo ← │ KORU-002│
│ KORU-004    │ Write .env with API key             │ shell    │ blocked│ KORU-003│
│ KORU-005    │ Install config templates            │ shell    │ blocked│ KORU-004│
└─────────────┴─────────────────────────────────────┴──────────┴────────┴─────────┘

Next runnable: KORU-003 (human). Run with: koru run
```

### 7.2 `koru run` (next task)

```
$ koru run
→ KORU-003: Get OPENROUTER_API_KEY from user [executor: human]

? Enter your OPENROUTER_API_KEY (starts with sk-or-v1-...): **********
✓ Saved to context (env_var: OPENROUTER_API_KEY)

✓ KORU-003 done (took 14s).

Next: KORU-004 (shell, auto_run=true). Run with: koru run
```

### 7.3 `koru run --all`

Runs the full pipeline, stopping only at human/non-auto tasks.

### 7.4 `koru run TASK-ID`

Skip dependency checks, force-run a specific task (useful for retry after fix).

### 7.5 `koru pipeline load <file>`

Import a pipeline YAML into planfile.yaml (adds tasks with `koru-task` label).

### 7.6 `koru pipeline export`

Export to GitHub Issues / GitLab / Jira via planfile's sync backends.

## 8. Configuration

```yaml
# koru.yaml (optional — defaults work for most repos)
pipeline:
  storage: planfile               # planfile.yaml (via planfile package)
  filter_labels: [koru-task]      # only manage tickets with this label

executors:
  llm:
    provider: openrouter
    default_model: "anthropic/claude-3.5-sonnet"
    api_key_env: OPENROUTER_API_KEY
  human:
    interactive: true             # false = just mark "blocked" and exit
  shell:
    default_timeout: 300
    shell_path: /bin/bash

ui:
  mode: cli                       # cli | web | tui
  web_port: 8090                  # for `koru web` (future)
```

## 9. Does this require updating planfile?

**NO for phase 1** — we use `metadata.koru` + labels which work with the
current planfile schema.

**YES for phase 2 (after validation)** — we propose a PR to semcod/planfile
adding `executor` as an optional first-class field on `TicketState`:

```python
class TicketState(BaseModel):
    # ... existing fields ...
    executor: ExecutorType | None = None   # NEW optional field
```

This makes the koru dispatcher simpler and enables planfile to show
executor info in its own UI. Until then, koru parses `metadata.koru` itself.

## 10. Implementation plan

| Phase | What | Status |
|---|---|---|
| **P1** | Data model (`KoruTask`, `TaskStatus`, `ExecutorType`) | not started |
| **P2** | Pipeline loader (reads planfile.yaml, parses koru metadata) | not started |
| **P3** | ShellExecutor + HumanExecutor | not started |
| **P4** | `koru queue` and `koru run` CLI | not started |
| **P5** | LlmExecutor (OpenRouter) + `.env` loading | not started |
| **P6** | Example: `examples/bootstrap.planfile.yaml` (this design doc's use case) | not started |
| **P7** | Integration tests (end-to-end pipeline run) | not started |
| **P8** | ApiExecutor + ToolExecutor | not started |
| **P9** | McpExecutor (once MCP is stable) | not started |
| **P10** | Web UI (`koru web` — Flask + simple TSX) | future |

## 11. Open questions

1. **Context passing:** `inputs: {FOO: "@KORU-003.outputs.env_var"}` syntax.
   Do we resolve at task run time or at pipeline load?
2. **Secrets:** human-provided API keys — store in `.env` (default) or
   use a secrets manager (future)?
3. **Parallelism:** phase 1 is strictly serial (one task at a time). Do we
   need parallel branches in the DAG for MVP?
4. **Failure policy:** on task failure → stop pipeline, retry, skip, or ask?
5. **Storage location:** `planfile.yaml` in project root (default) vs
   `.koru/pipelines/*.yaml` (multi-pipeline support)?

## 12. Next steps after approval

1. Implement `src/koru/pipeline/models.py` — pydantic models
2. Implement `src/koru/pipeline/loader.py` — reads planfile.yaml
3. Implement `src/koru/executors/shell.py` + `human.py`
4. Implement `src/koru/cli/pipeline.py` — `koru queue`, `koru run` commands
5. Ship `examples/bootstrap.planfile.yaml` as reference + tutorial
6. Add tests
