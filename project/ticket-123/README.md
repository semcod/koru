# Ticket 123: Remove pfix auto-repair from packaging metadata

- **ID**: ticket-123
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-13

## Goal and scope

On 2026-09-13 the user stated that pfix, intended as development-time
auto-repair, overwrites changes and must be removed from projects or
deactivated (SESSION_EXECUTION_AUTHORIZATION). This project declares a
`[tool.pfix]` table with `auto_apply = true` and `auto_install_deps = true` and
a pfix requirement. This integration ticket removes those declarations and,
where a lockfile exists, regenerates it.

Non-goals: no source or test change, no release, and no rewrite of generated
documentation projections.

## Acceptance criteria

- [ ] AC-01: No tracked `pyproject.toml` declares a `[tool.pfix]` table or a
  pfix requirement; every other parsed value is unchanged.
- [ ] AC-02: A tracked `uv.lock` is regenerated and records no direct pfix
  requirement of this project.

Fleet evidence: `subactor/docs/architecture/analysis/semcod-library-quality.md`.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
