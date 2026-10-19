# Ticket 467: fix(queue): prevent redact_secrets from corrupting code excerpts and repair missing + on closing delimiters (#728)

- **ID**: ticket-467
- **Owner**: agent:antigravity
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-10-19

SESSION_EXECUTION_AUTHORIZATION: User authorized autonomous resilience and prevention repairs in `semcod/koru` (`#728`) observed while delegating tickets through `willman` / `willops`.

## Goal and scope

Prevent `redact_secrets` in `src/koru/queue/patch_mode.py` from corrupting code expressions (`===`, `new Set([`, `decryptJson(...)`, `this.key = encryptionKey`) when quoting files in `current_file_excerpt` and `build_verify_retry_prompt`, and recover unmarked closing delimiters (`}`, `};`, `)`, `);`, `]`, `];`) plus trailing-blank `pre_ctx` anchors in `src/koru/queue/diff_repair.py`.

## Acceptance criteria

- [x] AC-01: `PYTHONPATH=src pytest -q -o addopts='' tests/test_planfile_queue.py -k 'redact or context_excerpt' tests/test_queue_evidence.py -k 'secrets'`, `python3 -m ruff check src/koru/queue/patch_mode.py src/koru/queue/diff_repair.py tests/test_planfile_queue.py`, and `./project/governance-check.sh` pass.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
