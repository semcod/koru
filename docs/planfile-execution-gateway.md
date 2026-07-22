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

## Current implementation status

The first implementation slice is now in place:

- `planfile` tickets carry `executor`, `execution`, `inputs`, and `outputs`.
- `planfile ticket next` returns the next runnable ticket.
- `planfile` exposes queue lifecycle commands: `claim`, `start`, `input`,
  `ready`, `complete`, `fail`, and `block`.
- `planfile` API exposes matching lifecycle endpoints and broadcasts ticket
  change events over `/ws`.
- `koru --queue --project .` executes one runnable ticket at a time.
- `koru` currently supports `shell`, `api`, and human-facing prompts.
- `koru --watch --ws-url ws://localhost:8000/ws` watches planfile queue
  events over WebSocket.

Remaining work:

- add explicit adapters for `mcp` and `llm`,
- add bootstrap templates that create a dependency tree of queued tasks,
- add richer release/lease recovery semantics.

## Did this require a `planfile` update?

**Yes.**

Current `planfile` already has strong ticket primitives:

- `status`
- `priority`
- `blocked_by`
- `blocks`
- REST API
- MCP server
- WebSocket / DSL transport

It did. The schema has now been extended with executor metadata and execution
state while preserving backward compatibility for existing ticket-only users.

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
      api_method: GET
      api_headers: {}
      api_body: null
      api_timeout_seconds: 30
      mcp_tool: null
      llm_model: null

    outputs:
      artifacts: []
      notes: []
      result: null
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

Expected koru behavior:

- read `inputs.api_endpoint` or `executor.handler`,
- send `inputs.api_method`, `inputs.api_headers`, and optional JSON
  `inputs.api_body`,
- mark HTTP 2xx/3xx responses as done,
- mark transport errors and HTTP 4xx/5xx responses as failed,
- attach status code and response body into `outputs.result`.

Example:

```yaml
tickets:
  PLF-220:
    name: "Notify bootstrap webhook"
    status: open
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
        event: bootstrap-ready
```

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
- management tool activity visible as `management.event` entries.

`planfile` already has a WebSocket-capable API surface, so the cheapest path
is to extend that rather than invent a second queue protocol. `koru` emits
best-effort management events when `KORU_EVENTS_URL` or `KORU_PLANFILE_API_URL`
is configured, so operators can see `koru.bootstrap`, `koru.queue`,
`koru.watch`, and repository loop activity in the same Live Events stream as
ticket lifecycle changes.

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

Implemented today:

```bash
koru --queue --project .
koru --queue --project . --dry-run
koru --watch --ws-url ws://localhost:8000/ws
task queue:run
task queue:dry-run
task queue:watch
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
   - `planfile ticket complete`
   - `planfile ticket input`
3. Add API support for queue-oriented operations.
4. Add WebSocket events for execution-state transitions.
5. Preserve backward compatibility for existing ticket-only users.

Items 1, 2, 3, 4, and 5 have an initial working implementation. Release/lease
recovery is still future work.

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

Items 1, `human`, `shell`, `api`, watch mode, and item 5 have an initial
working implementation.

## Suggested rollout

### Phase 1

- CI for `koru`
- docs/spec for execution gateway
- task queue runner prototype in `koru`
- first `planfile` execution schema changes

### Phase 2

- add `executor` / `execution` fields to `planfile`
- expose queue state via CLI/API/WebSocket

### Phase 3

- bootstrap new projects from templates into queued `planfile.yaml`
- connect shell, MCP, API, and human tasks into one loop

### Phase 4

- optional OpenRouter-backed `llm` executor
- richer multi-actor coordination

## Typed lifecycle SDK migration (updated 2026-07-20)

Koru supports the published Planfile 0.1.117 baseline and the primary queue
lifecycle now routes `claim`, `start`, `complete`, `fail`, `ready`, `block`,
and note append through
`planfile.client.PlanfileClient`. Storage lock retry and stable transition
codes therefore belong to Planfile, while Koru still decides whether and when
the transition is allowed.

Planfile 0.1.118 adds typed `fail` and `ready`. When those methods are absent
from an older SDK, Koru falls back before emitting an SDK control event and
performs the mutation once through the CLI. Planfile 0.1.117 leaves a started
ticket's board status as `in_progress` after `ready`, so the compatibility path
also applies `ticket update --status open`. Newer Planfile returns an already
open ticket and needs no extra mutation.

The compatibility release uses a single-write dual-run:

1. perform the mutation exactly once through the SDK;
2. read the ticket through `planfile ticket show --format json`;
3. compare a canonical projection of lifecycle fields;
4. report `verified`, `mismatch`, or `unavailable` as parity telemetry.

A typed SDK failure is never retried as a CLI mutation. Every SDK request emits
`koru.control.v1` with `interface_id=planfile_client_lifecycle`,
`transport=python_sdk`, and `replayable=false`. Note and reason contents are
excluded from the control log.

Compatibility controls:

- `KORU_PLANFILE_SDK=cli` — force the legacy CLI path;
- `KORU_PLANFILE_SDK=sdk` — force SDK mode for a custom embedded runner;
- `KORU_PLANFILE_SDK_VERIFY=0` — disable the read-only CLI parity probe.

Custom runners retain CLI behavior unless SDK mode is explicitly requested.
CLI executable discovery remains temporarily for read-only/administrative
operations and for the one-release compatibility path.

## Queue retry contract

`execution.max_attempts` belongs to the Koru scheduler. A nonzero executor exit
or a completion-verification error causes this sequence:

```text
running
  → fail (attempt += 1, last_error persisted)
  → ready + open, if attempt < max_attempts
  → next queue iteration

running
  → fail
  → block, if attempt >= max_attempts
```

The attempt counter records failures. Thus a success after two failures leaves
`attempt: 2`; it does not rewrite the audit history. If `fail`, `ready`, or the
0.1.117 compatibility reopen cannot be completed, Koru blocks the ticket to
avoid a stale running claim.

Patch-mode retries are nested inside a queue execution:

- `execution.max_attempts` limits complete queue executor runs;
- `inputs.max_patch_attempts` limits mechanical patch re-asks inside one run;
- a capability contract may further reduce the patch retry budget.

Set `inputs.max_patch_attempts` explicitly when these limits must be
independent. For compatibility, tickets that omit it inherit the patch retry
budget from `execution.max_attempts`.

Do not raise both budgets casually. Human approval, missing credentials,
resource waits, and other non-improving operational boundaries should be kept
out of the autonomous queue or configured with one execution attempt.

## External queue adapters (Mullm and others)

Multiple products can **emit** tickets into the same planfile without owning
execution runtime:

| Source | `source` field | `execution.queue` | `executor.kind` | Replaces local queue? |
| --- | --- | --- | --- | --- |
| Koru scan / code2llm | `koru.scan` | `default` | `human` | — |
| Mullm routing feedback | `mullm.routing` | `mullm-routing` | `human` | Mullm `improvements.jsonl` (optional) |
| Mullm shell (future) | `mullm.execution` | `mullm-shell` | `shell` | Mullm orchestrator only with NATS adapter |
| Mullm nlp2dsl workflow | `mullm.nlp2dsl` | `mullm-workflow` | `human` | partial (DSL engine stays in nlp2dsl) |

Recommended ticket fields for cross-system dedupe:

```yaml
labels:
  - mullm
  - routing-improvement
  - "dedupe:mullm-routing-<turn_id>"
metadata:
  external_ref: "mullm://routing-improvement/<uuid>"
  mullm_session_id: "<session>"
```

Mullm implements optional sync via `MULLM_PLANFILE_PROJECT` +
`planfile ticket create` (see `mullm/docs/ticket-queues-and-planfile.md`).
**Planfile becomes the human-facing backlog**; Mullm EventStore remains the
shell **execution bus** until `koru --queue` or a projector adapter unifies
completion events.

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
