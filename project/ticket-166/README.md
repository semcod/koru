# Ticket 166: context: prompt token budget gating, cache exclusions, and target AST slicing

- **ID**: ticket-166
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-17

## Goal and scope

Prevent LLM prompt explosion and `context_length_exceeded` errors in `koru.queue.context`:
- Exclude internal cache/runtime directories (`.code2llm_cache`, `.dirac-symbol-index`, `.koru`, `.worktrees`, `.pytest_cache`, `.mypy_cache`, `.ruff_cache`) and serialization artifacts (`*.pkl`, `*.pickle`, `*.parquet`) from project context and directory listings.
- Enforce a deterministic default token/character budget (`DEFAULT_MAX_CONTEXT_CHARS = 32_000`) whenever a ticket does not supply an explicit `max_context_chars`.
- Implement targeted AST / line slicing for oversized files (> 12,000 characters) when a ticket identifies a target symbol (e.g. `refresh_photo_vql_sidecar`) or target line, providing focused slices with module imports rather than unbounded 6000+ line dumps.
- Pass through `target_symbol`, `target_line`, and `ticket_description` in `ticket_llm_request`.

## Acceptance criteria

- [x] AC-01: `_ALWAYS_EXCLUDED_NAMES`, `_ALWAYS_EXCLUDED_SUFFIXES`, and glob patterns filter out cache directories (`.code2llm_cache`, `.dirac-symbol-index`, `.koru`, `.worktrees`, etc.) and `.pkl` files.
- [x] AC-02: `DEFAULT_MAX_CONTEXT_CHARS` is applied as the default ceiling in `build_project_context` when `max_context_chars` is omitted.
- [x] AC-03: `_extract_symbol_slice` and `_extract_line_slice` extract focused code slices around target symbols / lines for oversized source files.
- [x] AC-04: `ticket_llm_request` extracts and forwards `target_symbol`, `target_line`, and `ticket_description`.
- [x] AC-05: Unit tests pass in `tests/test_llm_context.py` covering exclusions, default budgeting, and AST slicing.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
