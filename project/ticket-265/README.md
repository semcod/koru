# Ticket 265: Address code smell: shotgun surgery content in sync vscode plugin version

- **ID**: ticket-265
- **Owner**: claude
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-26

## Goal and scope

Clear the code2llm `Shotgun Surgery: content` smell (planfile ticket PLF-041,
dedupe key `code2llm:smell:shotgun_surgery:scripts/sync-vscode-plugin-version.py`)
in `scripts/sync-vscode-plugin-version.py`.

Five functions each assign a generic local `content` for the file text they
read (`get_plugin_version_from_source`, `get_plugin_version_from_package`,
`update_plugin_version_source`, `update_package_json`,
`update_github_workflow`). The detector groups mutations by (file, variable)
and fires at >= 5 scopes — the shared *name* is the smell; the five locals are
logically independent (different files, different regexes).

Fix: stage-accurate local names named for the artifact each function reads —
`version_source` (plugin_version.py text, 2 scopes), `package_text`
(package.json text, 2 scopes), `workflow_text` (workflow YAML text, 1 scope).
Mutation groups drop to 2/2/1, under the threshold. Pure rename inside
function bodies; no behavior change.

Tests: add coverage for the three functions the existing test file does not
exercise (`get_plugin_version_from_package`, `update_package_json`,
`update_github_workflow`) so every renamed scope is executed.

Allocatable via ticket-264 (PR #473), which added `scripts/**/*.py` to
`application.ownedPaths`.

Authorization: the operator handoff for PLF-041 explicitly requested this
refactor and its execution, recorded here as SESSION_EXECUTION_AUTHORIZATION
(agent-owned file; no `user-*.md` input used).

## Acceptance criteria

- [x] AC-01: code2llm smell re-scan (same invocation that generated the
  ticket) no longer reports `shotgun_surgery` for
  `scripts/sync-vscode-plugin-version.py`, and introduces no new smell for
  that file.
- [x] AC-02: `pytest tests/test_sync_plugin_version_script.py` passes
  (2 existing + 2 new tests) and ruff reports zero errors on the touched
  files.
- [x] AC-03: `bash project/governance-check.sh` passes with 0 errors from the
  ticket worktree.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
