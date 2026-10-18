# Ticket 459: Prevent duplicate historical ticket IDs and cross-venv PYTHONPATH scan pollution

- **ID**: ticket-459
- **Owner**: antigravity
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-10-18

SESSION_EXECUTION_AUTHORIZATION: User authorized autonomous diagnosis and repair of ticket allocation and cross-venv scan anomalies across `semcod/koru`.

## Goal and scope

1. Ensure `_generate_ticket_id` in `src/koru/task_intake.py` computes the highwater ticket ID across `.planfile/sprints/*.yaml`, `.planfile/index/history-locations.yaml`, `.planfile/sync/*.state.yaml`, and `.planfile/events/operations.jsonl` so `koru task` never reuses an archived historical ticket ID when `.planfile/config.yaml` `next_id` lags behind history.
2. Add `sanitized_subprocess_env` in `src/koru/utils/subprocess_runner.py` and use it in `default_subprocess_runner` and `scan_pytest_collect` (`src/koru/scan.py`) so foreign virtualenv `site-packages` entries in `PYTHONPATH` do not leak into target project `pytest --collect-only` probes.
3. Extend `_existing_code2llm_issue_keys` in `src/koru/autonomy/code2llm_discovery.py` to include archived `history-*.yaml` terminal tickets whose target files on disk are unchanged.

## Acceptance criteria

- [x] AC-01: `create_nl_task` allocates IDs above the highest historical/sprint ticket ID, `scan_pytest_collect` strips foreign virtualenv `site-packages` from `PYTHONPATH`, and `run_code2llm_discovery` skips archived history tickets when target files on disk are unchanged.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
