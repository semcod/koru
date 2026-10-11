# Ticket 448: Support pythonpath src and dot fallback in python-pytest builtin verify profile

- **ID**: ticket-448
- **Owner**: gemini
- **Status**: IN_PROGRESS
- **Workflow state**: PUBLICATION
- **Created**: 2026-10-11

SESSION_EXECUTION_AUTHORIZATION: user requests continuation, test and merge. Builtin python-pytest profile must include src and . in pythonpath so packages with src/ layout can run pytest in clean worktrees without prior editable install.

## Goal and scope

Update `BUILTIN_PROFILES["python-pytest"]` in `src/koru/queue/verify/profiles.py` to use `python -m pytest -o pythonpath="src ." -q`. This ensures that in isolated worktrees (where repositories have not been installed via `pip install -e .`), pytest can discover and import package code located under `src/` as well as the repository root `.`.

## Acceptance criteria

- [x] AC-01: `BUILTIN_PROFILES["python-pytest"].command` is `python -m pytest -o pythonpath="src ." -q`.
- [x] AC-02: Regression tests verify that `python-pytest` executes with `pythonpath="src ."` option.
- [x] AC-03: Governance checks pass cleanly.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
