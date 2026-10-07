# Ticket 442: Detect tracked koru runtime files that .gitignore no longer excludes

- **ID**: ticket-442
- **Owner**: claude-code
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-10-07

## Goal and scope

Seven repositories (semcod/prefact, repatch, tagi, nxdo, markpact/propact, subactor/orchestrator, coru-agent/coru-dev) keep `.koru/event-store.jsonl` and `.koru/events/*` tracked although `.gitignore` lists `.koru/`; they were committed before the ignore entry, so every koru run dirties the primary checkout. koru doctor/scan only checked for the `.gitignore` line. Report ignored-but-tracked runtime files instead. User authorization: investigate the last 8 hours with monag and reflex, propose prevention, then continue (`kontynuuj`).

## Acceptance criteria

- [ ] AC-01: `check_gitignore` warns and `scan_gitignore_drift` suggests untracking when ignored koru runtime files are still tracked; clean or non-Git projects pass.
- [ ] AC-02: Tests, Ruff and governance pass.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
