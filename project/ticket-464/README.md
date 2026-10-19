# Ticket 464: Sanitize foreign runtime PYTHONPATH in verification sandbox environment

- **ID**: ticket-464
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-10-19

## Goal and scope

Sanitize `PYTHONPATH` via `sanitized_subprocess_env(project)` inside `verification_sandbox._command` so foreign Koru runtime venv `site-packages` do not leak into bubblewrap verification subprocesses.

## Acceptance criteria

- [x] AC-01: `verification_sandbox._command` strips foreign `/.local/share/koru/runtime/.../site-packages` entries from `PYTHONPATH` while preserving project-local `PYTHONPATH` entries.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
