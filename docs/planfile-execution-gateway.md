# planfile as execution gateway for koru

This document defines the next architectural step for `koru`:
use `planfile.yaml` not only as a ticket backlog, but also as the
**execution gateway** for queued work across humans, agents, tools, APIs,
and shell commands.

## Goal

We want to bootstrap a new project with a **tree of dependent tasks** stored
in `planfile.yaml`, then let `koru` execute or coordinate those tasks one by
one.

For the first iteration we deliberately keep the model simple:

- one active task at a time,
- a visible queue,
- clear ownership of who executes each task,
- live status over shell/API/WebSocket,
- automatic execution whenever possible,
- explicit human intervention only when necessary.

## Why this matters

Today:

- `planfile` is mainly a **ticket store and sync layer**,
- `koru` is mainly a **closed-loop command runner**,
- the connection between "task exists" and "task gets executed by the right
  actor" is still too thin.

The new model makes `planfile` the single source of truth for:

- what should happen,
- who should do it,
- whether it can be automated,
- what depends on what,
- what is running now,
- what is blocked and why.

## Required architectural split

`koru` must remain independent from `c2004`.

That means:

- the execution model belongs in `koru`,
- the generalized task schema belongs in `planfile`,
- `c2004` should only provide a **reference deployment** and real-world
  examples of those capabilities.

## Does this require a `planfile` update?

**Yes.**

Current `planfile` already has strong ticket primitives:

- `status`
- `priority`
- `blocked_by`
- `blocks`
- REST API
- MCP server
- WebSocket / DSL transport

But it does **not yet model execution semantics explicitly**.

To make `planfile` the gateway for `koru`, we need to extend the schema with
executor metadata and execution state.

## Proposed planfile schema extension

Minimal first version:

```yaml
tasks:
  - id: PLF-201
    name: "Provide OpenRouter API key"
    status: open
    priority: high
    blocked_by: []
    blocks: ["PLF-202"]

    executor:
      kind: human          # human | shell | mcp | api | llm
      mode: interactive    # interactive | automatic
      handler: prompt      # e.g. shell script path, MCP tool name, API action

    execution:
      queue: default
      state: pending       # pending | ready | running | waiting_input | done | failed | skipped
      assigned_to: null    # human name, agent id, service id
      started_at: null
      finished_at: null
      lease_expires_at: null
      attempt: 0
      max_attempts: 1
      last_error: null

    inputs:
      prompt: "Paste API key for provider X"
      env_keys: ["OPENROUTER_API_KEY"]
      script: null
      api_endpoint: null
      mcp_tool: null
      llm_model: null

    outputs:
      artifacts: []
      notes: []
+      result: null
```

## Executor kinds

### `human`

Used when a person must:

- provide an API key,
- make a decision,
- approve a branch,
- choose which branch of the task tree to continue.

Expected koru behavior:

- show the task in shell/UI,
- explain exactly what the human needs to do,
- wait for confirmation or data,
- update `execution.state` to `waiting_input` or `done`.

### `shell`

Used for scripts and local commands.

Examples:

- install dependencies,
- render templates,
- run bootstrap scripts,
- execute local checks.

Expected koru behavior:

- run the declared command,
- stream stdout/stderr,
- update `execution.state`,
- attach summary / exit code into `outputs.result`.

### `mcp`

Used when execution should happen through a tool exposed by an MCP server.

Examples:

- `planfile` MCP,
- `testql` MCP,
- `redup` MCP,
- future project-specific MCP tools.

Expected koru behavior:

- call the MCP tool with declared arguments,
- store structured result,
- move task forward automatically.

### `api`

Used for machine-to-machine HTTP actions.

Examples:

- create a remote resource,
- trigger CI,
- call a webhook,
- provision an integration.

### `llm`

Used only in the opt-in automation lane.

Examples:

- `redsl improve`,
- `llx fix`,
- future OpenRouter-backed actions.

Expected koru behavior:

- load credentials from `.env`,
- execute the configured LLM path,
- write back execution metadata and artifacts,
- stay compatible with shell/API visibility.

## Queue model for v1

We explicitly start with **single-task execution**:

- `koru run`
- find next runnable task (`status=open`, `execution.state in {pending,ready}`,
  dependencies satisfied),
- acquire it,
- execute it,
- update state,
- print live progress,
- move to next task only after current one finishes or is skipped.

This keeps the first version explainable and observable.

## Shell/API/WebSocket behavior

The same queue must be visible through three surfaces:

### Shell

Example desired UX:

```bash
koru queue
koru next
koru run
koru watch
```

Shell should show:

- next task,
- executor kind,
- current owner,
- current state,
- blocked reason,
- recent result.

### API

`koru` should expose endpoints such as:

- `GET /queue`
- `GET /tasks/next`
- `POST /tasks/{id}/start`
- `POST /tasks/{id}/complete`
- `POST /tasks/{id}/skip`
- `POST /tasks/{id}/input`

### WebSocket

For live dashboards and shells:

- task started,
- task waiting for human input,
- task completed,
- task failed,
- queue advanced.

`planfile` already has a WebSocket-capable API surface, so the cheapest path
is to extend that rather than invent a second queue protocol.

## Bootstrap of a new project

Instead of a single install script, `koru` should bootstrap a new project by:

1. selecting a template/tree,
2. generating a `planfile.yaml`,
3. inserting dependent tasks,
4. running the queue.

Example phases:

1. create repo structure
2. copy reusable templates
3. ask human for API keys / integration decisions
4. run shell bootstrap
5. run checks
6. open next human or LLM task

This makes setup:

- replayable,
- exportable,
- auditable,
- synchronizable with external systems.

## Proposed koru CLI additions

Recommended first commands:

```bash
koru init --template python-lib
koru queue
koru next
koru run
koru watch
koru task show PLF-201
koru task input PLF-201 --value "..."
koru task skip PLF-201
```

## Recommended planfile changes

These should happen in `semcod/planfile`:

1. Extend ticket/task model with:
   - `executor`
   - `execution`
   - `inputs`
   - `outputs`
2. Add CLI support:
   - `planfile ticket next`
   - `planfile ticket claim`
   - `planfile ticket release`
   - `planfile ticket complete`
   - `planfile ticket input`
3. Add API support for queue-oriented operations.
4. Add WebSocket events for execution-state transitions.
5. Preserve backward compatibility for existing ticket-only users.

## Recommended koru changes

These should happen in `semcod/koru`:

1. Add queue runner that reads executable tasks from `planfile.yaml`.
2. Add actor dispatch:
   - human
   - shell
   - mcp
   - api
   - llm
3. Add live shell output and watch mode.
4. Add bootstrap-from-template flow for new repositories.
5. Keep single-task queue semantics in v1.

## Suggested rollout

### Phase 1

- CI for `koru`
- docs/spec for execution gateway
- task queue runner prototype in `koru`
- no `planfile` schema changes yet

### Phase 2

- add `executor` / `execution` fields to `planfile`
- expose queue state via CLI/API/WebSocket

### Phase 3

- bootstrap new projects from templates into queued `planfile.yaml`
- connect shell, MCP, API, and human tasks into one loop

### Phase 4

- optional OpenRouter-backed `llm` executor
- richer multi-actor coordination

## Bottom line

If you want `koru` to:

- drive installation of a new project,
- split work into dependent tasks,
- decide whether shell, MCP, API, LLM, or human should execute a task,
- stream status live,
- and use `planfile.yaml` as the source of truth,

then **yes, `planfile` should be extended**.

The good news is that it does **not** need a rewrite.
It already has the right center of gravity: tickets, status, dependencies,
CLI, API, MCP, and WebSocket.

What it needs is one more layer: **execution semantics**.
