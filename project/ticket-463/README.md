# Ticket 463: Stamp scan_executor_kind and patch_mode contract on code2llm_discovery tickets

- **ID**: ticket-463
- **Owner**: agent:agy
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-10-19

## Goal and scope

1. Update `koru.autonomy.code2llm_discovery._ticket_item_scaffold` to resolve `executor_kind` via `koru.scan_ticket_emission.scan_executor_kind()` instead of hardcoding `"human"`, and stamp `"inputs": {"expect_files_changed": True, "patch_mode": True}` when `files` is non-empty so `code2llm` project-discovery tickets created on headless lanes with `KORU_SCAN_EXECUTOR_KIND=llm` satisfy `_llm_completion_scope_gap` and execute automatically.

## Acceptance criteria

- [x] AC-01: `_ticket_item_scaffold` uses `scan_executor_kind()` and stamps `inputs.expect_files_changed=True` and `inputs.patch_mode=True` when `files` is non-empty.
- [x] AC-02: Unit tests in `tests/test_code2llm_discovery.py` and governance checks pass.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
