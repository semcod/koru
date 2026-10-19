# Ticket 460: Skip unrunnable koru.yaml task gates when Taskfile or target is absent

- **ID**: ticket-460
- **Owner**: agent:antigravity
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-10-19

SESSION_EXECUTION_AUTHORIZATION: User authorized autonomous resilience fix in `semcod/koru` so repositories with boilerplate `task quality:regix:local` in `koru.yaml` but no `Taskfile.yml` (or missing task target) automatically fall back to project test detection (`pytest -q`).

## Goal and scope

Ensure `_verify_command_from_project` in `src/koru/queue/verify/legacy.py` and `_verify_from_koru_yaml` in `src/koru/queue/todo2code_gate.py` skip `task <target>` commands declared in `koru.yaml` when the repository lacks a `Taskfile` or does not define `<target>`, falling back to the project's configured or auto-detected verification command.

## Acceptance criteria

- [x] AC-01: `pytest -q tests/test_diff_repair_and_refactor.py tests/test_todo2code_autonomous_gate.py`, `python3 -m ruff check src tests`, and `./project/governance-check.sh` pass.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
