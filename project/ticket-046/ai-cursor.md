# Agent plan (ticket-046)

## Findings (from env2llm + koru sessions)

1. Autonomous loop stalls on `operator` human tickets (`waiting_input`).
2. Scan dedupe keeps stale path-bound tickets after refactors.
3. `koru ci run --project .` fails (project flag only before subcommand).
4. Validator dispatch had no mergeability preflight → `mergeable=UNKNOWN` / DIRTY merges.
5. `acceptedBaseSha` still manual after rebase (out of scope here).

## Changes

- `cli_ci.py`: `--project` on subcommands too.
- `ci/github.py` + `publication.py`: poll mergeability, fail on CONFLICTING/UNKNOWN.
- `ticket_hygiene.py`: archive tickets with missing declared paths.
- `queue/ticket.py` + `runner.py`: skip operator human tickets when non-interactive.

## Validation

`python -m pytest -q tests/test_ci_pipeline.py tests/test_ticket_hygiene.py tests/test_queue_ticket_selection.py`
