# Ticket 230: Implement Rust engine prototype for scan_todo

- **ID**: ticket-230
- **Owner**: gemini
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-26

## Goal and scope

Implement a high-performance native Rust engine prototype in `packages/koru-scan-todo` matching the atomized `scan_todo` API (`count_todo_markers`, `load_koruignore_patterns`, `is_koruignored`, `count_todo_markers_in_project`). Provide a fast standalone CLI binary with structured JSON output and benchmark mode, write unit tests in Rust, and add integration/benchmark tests in `tests/test_scan_todo_rust.py` comparing Python vs Rust performance.

## Acceptance criteria

- [x] AC-01: Scope is approved by human owner (SESSION_EXECUTION_AUTHORIZATION).
- [x] AC-02: `packages/koru-scan-todo` implements native marker scanning with zero external dependencies and passes `cargo test`.
- [x] AC-03: `tests/test_scan_todo_rust.py` passes, verifying exact output compatibility and demonstrating measurable speedup over Python.
- [x] AC-04: `bash project/governance-check.sh` passes with 0 errors.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
