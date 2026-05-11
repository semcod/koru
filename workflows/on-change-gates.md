# On-Change Gates — wup + testql + regix triad

## Goal

Every project that runs koru gets the **same** automatic on-change gate
flow, so the agent (and the human) learn within seconds — not in CI —
whether a save broke anything observable. Three packages, one cycle.

## Layered architecture

```
        ┌─────────────────────┐
file →  │  wup (daemon)       │  ← fs watcher, debounce, gitignore
save    │  layer 1: detect    │
        └──────────┬──────────┘
                   │ filtered change event
                   ▼
        ┌─────────────────────┐
        │  wup (resolver)     │  ← dependency map: file → service → tests
        │  layer 2: priority  │
        └──────────┬──────────┘
                   │ list of testql endpoints (≤3)
                   ▼
        ┌─────────────────────┐
        │  testql (CLI)       │  ← run quick smoke scenarios
        │  HTTP probe         │
        └──────────┬──────────┘
                   │ pass / fail
            ┌──────┴──────┐
       pass │             │ fail
            ▼             ▼
       ✓ idle      ┌─────────────────────┐
                   │  testql full scen.  │  ← full TOON scenario
                   │  layer 3: detail    │
                   └──────────┬──────────┘
                              ▼
                   ┌─────────────────────┐
                   │  regix compare      │  ← metric delta vs HEAD~1
                   │  quality regression │
                   └──────────┬──────────┘
                              ▼
                   ┌─────────────────────┐
                   │  blame report       │  ← .wup/blame-history.jsonl
                   │  + healing-webhook  │     + planfile ticket auto-create
                   └─────────────────────┘
```

## Three packages, three responsibilities

| Package | Role | Trigger | Input | Output |
|---|---|---|---|---|
| `wup` | **detection + routing** | every file save | watch paths | service list + endpoint list |
| `testql` | **probe execution** | wup priority/detail | endpoints/scenario | per-endpoint pass/fail |
| `regix` | **quality regression** | on testql fail | git refs | metric delta + violations |

`wup` owns the cycle. `testql` and `regix` are atomic invocations.

### Supplementary lints (cheap, opt-in)

| Lint | Detects | Script |
|---|---|---|
| `taskfile-escapes` | `$${VAR}` footgun (Task v3 leaks `$$` to shell as PID) | `scripts/check-taskfile-escapes.sh` |
| `version-drift` | Inconsistent version pins across manifests | `scripts/check-version-drift.sh` |
| `redup` | New cross-module duplicates | `scripts/redup-precommit.sh` |

These run on save (via wup `lint_strategy`) and as the koru pre-commit hook
when `Taskfile.yml` / `requirements*.txt` / `*.py` files are staged. Each
exits 0 with an advisory message by default; export the matching
`*_STRICT=true` to make it blocking.

> **Why `taskfile-escapes` deserves its own lint:** the `$${VAR:-default}`
> pattern silently produces URLs like `http://localhost:<PID>{PORT:-8810}/…`
> at runtime — curl rejects them with `Port number was not a decimal
> number between 0 and 65535`. The bug looks like an env-var problem until
> you trace the shell substitution. PLF-065 in c2004 spent significant
> debug time on this; this lint catches the whole class in <1 s.

## Lifecycle integration with koru

When a koru-managed project (markers: `git`, `planfile`, `wup_yaml`,
`testql_scenarios`, `regix_yaml`) is opened:

1. **`koru` brief** surfaces an **"On-change gates"** section with:
   - `wup`        — daemon running? last activity timestamp?
   - `testql`     — N scenarios discovered under `testql-testing/scenarios/`
   - `regix`      — last gate result (PASS/FAIL with violation count)

2. **agent decision rules** (added to ticket policy when these markers
   are present):

   - Before editing files in a ticket's scope → check the `regix gates`
     baseline so the comparison is fair afterward.
   - After every batch of edits inside a ticket → run `wup` quick layer
     on the affected service before claiming the work is done.
   - Before `planfile ticket complete` → require `regix compare` exit
     0 (no introduced regression). This is enforced automatically when
     `require_ci_pass_before_complete: true`.

3. **healing-webhook integration** (optional): if observability stack is
   running and `WUP_WEBHOOK_URL` is set, blame reports forward as
   alerts; alertmanager routes them to a planfile ticket via
   `healing-webhook`'s alert→ticket bridge.

## Bootstrap (per project)

```bash
# 1. Install wup config from koru template
task template:install:wup     PROJECT=<name>

# 2. Adjust wup.yaml (services, paths)  ← human one-time tuning
$EDITOR wup.yaml

# 3. Build dependency map
wup map-deps

# 4. Verify testql-endpoints are reachable from wup
wup testql-endpoints

# 5. Start the watcher (foreground for first run; daemonize after)
wup watch

# 6. (optional) Init regix baseline if not present
regix init
regix snapshot --label "wup-baseline-$(date +%Y%m%d)"
```

After bootstrap, `koru --project .` shows the three gate statuses in
the handoff.

## Manual gate run (slash command for the agent)

The agent can run the full triad on demand:

```
/koru-gate
```

This slash-command:
1. Runs `regix gates` (absolute thresholds) → exit 0/1.
2. Runs `testql run` on each scenario in the active ticket's scope (or
   all under `testql-testing/scenarios/` if no ticket).
3. Reports `wup status` (daemon up? last detection?).
4. Aggregates: any failure → suggest `planfile ticket input` with
   findings; clean → green light to continue editing.

## Failure modes & escape hatches

| Symptom | Cause | Fix |
|---|---|---|
| `wup watch` hammers CPU | watch paths too broad | tighten `watch.paths`, add gitignored excludes |
| Quick tests time out | service slow to start | raise `test_strategy.quick.timeout_s` |
| Same blame report 100x | dependency map stale | `wup map-deps` (after refactor) |
| `regix compare` always fails | baseline not snapshotted | `regix snapshot --label baseline` once |
| Healing-webhook noise | every quick-fail forwards | gate webhook on `full_tests` only |

## Why this triad

- `wup` alone — no quality regression awareness (only HTTP pass/fail).
- `testql` alone — runs on demand, not on save. No file→service link.
- `regix` alone — measures metrics, not behavior. No live signal.

Together: live behavior probe + metric-aware quality gate + human
blame report. This is the same shape as `quality:gate` but **continuous
and per-save** instead of pre-merge.
