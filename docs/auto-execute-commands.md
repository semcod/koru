# Auto-execute commands with Koru

Koru can run shell commands **without** an IDE agent when you wire them through
the planfile queue, `koru work next --run-gates`, or autonomous loops. This
guide explains which configuration blocks actually execute commands versus which
blocks only appear in agent briefs.

## Three execution surfaces

| Surface | Config / command | Executes shell? | Typical use |
| --- | --- | --- | --- |
| **Planfile shell ticket** | `executor.kind: shell` + `koru --queue` | **Yes** | Run `koru ci run`, pytest, deploy scripts |
| **`koru work next --run-gates`** | Built-in `task_profiles.yaml` | **Yes** (auto steps only) | Refactor profiles (`verify` → `koru ci run`) |
| **`koru.yaml` `when:`** | `ticket_iteration`, `bootstrap`, … | **No** (brief only) | Operator checklist in `koru --context` |
| **`when.before_complete_ticket`** | `koru.yaml` commands list | **Yes** (verify hooks) | Gate before ticket `done` in autonomous mode |
| **`queue.post_run_verify`** | `koru.yaml` | **Yes** | Reopen ticket if CI fails after `done` |
| **`policy.yaml` `ci.command`** | `.planfile/.koru/policy.yaml` | **Yes** (via `koru ci run`) | Project test command |

The header comment in generated `koru.yaml` is intentional:

> Koru reads this file for briefs/doctor; it does not auto-run shell steps.

Only the rows marked **Yes** in the table above start subprocesses.

## 1. Shell tickets (recommended)

Add a runnable ticket to `.planfile/sprints/current.yaml`:

```yaml
CI-001:
  id: CI-001
  name: Run full local CI
  status: open
  priority: high
  executor:
    kind: shell
    handler: koru ci run --project .
    mode: automatic
  execution:
    queue: default
    state: ready
    attempt: 0
    max_attempts: 1
  sprint: current
```

Run it:

```bash
# One ticket
koru --queue --project .

# Drain runnable shell tickets
koru --queue --loop --project .
```

Koru claims the ticket, runs `executor.handler`, and marks it `done` or `failed`
through the planfile lifecycle. See
[`planfile-execution-gateway.md`](./planfile-execution-gateway.md) for queue
semantics.

## 2. `koru ci run` — policy + quality gates

`koru ci run` is **not** magic: it runs two stages in order:

1. **`policy.ci.command`** from `.planfile/.koru/policy.yaml` (e.g. `bash scripts/ci-test.sh`)
2. **Quality gates** from `.koru/topology.yaml` (typically `regix` + `redup`)

```bash
koru ci run --project .              # policy + gates
koru ci run --project . --skip-gates # policy only
koru ci gates --project .            # gates only
```

Wire the policy once per project:

```yaml
# .planfile/.koru/policy.yaml
ci:
  command: |
    set -euo pipefail
    bash scripts/ci-test.sh
  timeout_seconds: 600

llm:
  require_ci_pass_before_complete: true
```

With `require_ci_pass_before_complete: true`, agents must not call
`planfile ticket complete` until CI exits 0.

## 3. `koru work next --run-gates`

Built-in refactor profiles in `task_profiles.yaml` include auto shell steps such
as `koru ci run` on the `verify` step. Use this when the active planfile ticket
matches a profile (labels like `refactor`, `god-module`, or name patterns).

```bash
koru work next --project .              # show plan
koru work next --project . --run-gates  # execute auto-runnable steps
```

`ide_work` steps still require the IDE lane; only steps with `auto: true` and
`kind: shell` run headlessly.

## 4. Autonomous loop

`koru autonomous up` chains scan → `koru --queue --loop` → optional autopilot:

```bash
koru autonomous up --project . --max-cycles 3 --sleep-seconds 30 --agent-lane auto
```

Shell tickets run inside the queue phase. IDE tickets need autopilot connected;
see [`autopilot-quickstart.md`](./autopilot-quickstart.md).

## 5. Verification hooks (`koru.yaml`)

### Before complete

`when.before_complete_ticket.commands` is read by autonomous verification and
todo2code gates:

```yaml
when:
  before_complete_ticket:
    description: Run CI before planfile ticket done.
    commands:
      - koru ci run --project .
```

### After done (post-run verify)

Catch tickets marked `done` while the tree is still red:

```yaml
queue:
  post_run_verify:
    enabled: true
    on_failure: reopen          # reopen | block
    after_ide_drive: true
    ide_done_window_minutes: 30
    commands:
      - koru ci run --project .
```

Details: [`post-run-verify.md`](./post-run-verify.md).

Environment overrides: `KORU_POST_RUN_VERIFY=1|0`.

## 6. Practical checklist (env2llm-style repo)

```bash
cd /path/to/your-repo

# 1. Init + doctor
koru --init --project .
koru --doctor --project .

# 2. Confirm policy CI
koru ci run --project .

# 3. Add a shell ticket (see YAML above), then:
koru --queue --loop --project .

# 4. Optional: one autonomous cycle
koru autonomous up --project . --max-cycles 1 --sleep-seconds 0 --no-autopilot
```

## Troubleshooting

| Symptom | Likely cause | Fix |
| --- | --- | --- |
| `when:` commands never run | Brief-only section | Use shell ticket + `--queue` |
| `koru ci run` skips tests | Empty `ci.command` | Set `.planfile/.koru/policy.yaml` |
| Queue skips ticket | `blocked_by` / wrong `status` | `planfile ticket show <id>` |
| `claim_failed` | Planfile API not running | Start planfile server or use CLI-only queue |
| `FileNotFoundError: .../venv/bin/planfile` | Stale venv shebang after repo move | Reinstall planfile in project venv or fix shebang |
| Gates fail, tests pass | `regix` / `redup` thresholds | Tune `regix.yaml` or `.koru/topology.yaml` |

## See also

- [`quickstart-10min.md`](./quickstart-10min.md) — bootstrap + first ticket
- [`cli-examples.md`](./cli-examples.md) — closed-loop and ticket examples
- [`agent-guide.md`](./agent-guide.md) — LLM agent workflow
- [`post-run-verify.md`](./post-run-verify.md) — `queue.post_run_verify`
