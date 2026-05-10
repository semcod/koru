# End-to-end tests for koru queue runner

This directory contains shell-based end-to-end tests that exercise the
full stack: `koru --queue` → `planfile` CLI → file-based state in
`.planfile/sprints/`.

## Requirements

- `planfile >= 0.1.87` (released or installed from
  [`semcod/planfile`](https://github.com/semcod/planfile) source). This
  version ships:
  - `TicketExecutor`, `TicketExecution`, `TicketInputs`, `TicketOutputs`
    Pydantic models on `Ticket`
  - CLI commands: `ticket next/claim/start/complete/fail/input/ready`
- `python3` on PATH
- `git` on PATH (each test creates a temp git repo to mirror real usage)

## Running locally

```bash
# Default: assumes 'planfile' is on PATH
task test:e2e

# Or explicit binary (e.g. local source venv):
PLANFILE_BIN=/home/you/github/semcod/planfile/.venv/bin/planfile \
  task test:e2e

# Or run the script directly:
bash tests/e2e/smoke.sh
```

## What `smoke.sh` covers

Six end-to-end steps with a temp project (`/tmp/koru-e2e-smoke-$$`):

1. Build `.planfile/{config.yaml,sprints/current.yaml}` with two tickets:
   - `SMOKE-001` — shell ticket, `executor.kind=shell`,
     `handler="echo SMOKE_PASS"`
   - `SMOKE-002` — human ticket, `executor.kind=human`,
     `handler=password`, blocked by SMOKE-001
2. Verify `planfile ticket list` returns the tickets
3. Verify `planfile ticket next --format json` returns SMOKE-001
   (highest priority + ready state)
4. Run `koru --queue --dry-run` — confirm preview without execution
5. Run `koru --queue --actor koru-e2e` — confirm shell command runs and
   ticket transitions to `done` with `assigned_to=koru-e2e` plus a note
   recording the command
6. Run `koru --queue` again — confirm it picks SMOKE-002 and returns
   `status=waiting_input` with the configured prompt

## CI integration

Currently the e2e suite is **not** part of GitHub Actions because it
requires planfile to be installed at the right version. To enable it:

```yaml
# .github/workflows/ci.yml — add a new job
e2e:
  needs: [lint, test]
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4
    - uses: actions/setup-python@v5
      with:
        python-version: "3.12"
    - run: pip install -e . "planfile>=0.1.87"
    - run: bash tests/e2e/smoke.sh
```

## Adding new e2e tests

Each test should:

- Create its own temp directory under `/tmp/`
- Set up `.planfile/` from scratch (no shared state between tests)
- Clean up via `trap cleanup EXIT`
- Fail fast with `set -euo pipefail` and explicit assertions
- Be self-documenting: each `==>` step describes what it verifies
