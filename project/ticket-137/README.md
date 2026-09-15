# Ticket 137: Expose and reconcile legacy skipped Planfile tickets in queue reads

- **ID**: ticket-137
- **Owner**: codex
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **GitHub issue**: semcod/koru#182

## Goal and scope

Keep records written by older Planfile versions visible to Koru read-only
surfaces. A legacy `status: skipped` record must appear in `all_tickets` and
queue housekeeping even when the installed Planfile CLI omits it during model
validation. The adapter annotates recovered records and reports migration and
unknown-status counts; it never changes YAML or event history.

## Acceptance criteria

- [x] Raw records omitted by a successful or failed legacy Planfile list are
      recovered by id for Koru history/maintenance reads.
- [x] Recovered `skipped` and unknown statuses carry explicit diagnostics and
      aggregate counts in context output.
- [x] The existing explicit `koru queue migrate-legacy-skipped --apply` remains
      the only mutation path and preserves the Planfile audit note.
- [x] Regression tests cover context history, queue listing, and unknown
      status accounting.

## Delivery evidence

- `pytest -q tests/test_context.py tests/test_queue_clean.py` — 53 passed.
- `ruff check src/koru/planfile_compat.py src/koru/context.py src/koru/queue_clean.py tests/test_context.py tests/test_queue_clean.py` — passed.
- `./project/governance-check.sh` — passed.
