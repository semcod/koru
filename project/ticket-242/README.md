# Ticket 242: decompose god module scan by extracting semcod quality artifact scanners

- **ID**: ticket-242
- **Owner**: koru-agent
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-26

## Goal and scope

Decompose the `God Module: src.koru.scan` smell (reducing `src/koru/scan.py` from 2,083 to 836 lines) by extracting external semcod quality artifact report scanners (`jscpd`, `code2llm`, `testql`, `redup`, `vallm`, `pyqual`, `prefact`, `regix`, `redsl`, `metrun`, `pfix`, `todo2code`) into a dedicated module `src/koru/scan_artifacts.py`.

Maintain 100% backward compatibility by re-exporting all pre-existing public and internal symbols from `koru.scan`.

## Acceptance criteria

- [x] AC-01: Scope is approved by human owner (SESSION_EXECUTION_AUTHORIZATION).
- [x] AC-02: `tests/test_scan_artifacts.py` passes (9/9 passed).
- [x] AC-03: `tests/test_scan.py` passes all `TestScanSemcodArtifacts` regression tests (24/24 passed).
- [x] AC-04: `ruff check` and `ruff format --check` report 0 findings on modified files.
- [x] AC-05: `bash project/governance-check.sh` reports 0 errors.

## Tracking boundary

SESSION_EXECUTION_AUTHORIZATION: the user authorized sequential refactoring and atomization across `redup`, `code2llm`, and `koru`.

This directory contains the minimal reviewed intent. Optional participant prose and raw command logs are not required delivery output.
