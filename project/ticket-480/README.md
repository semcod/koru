# Ticket 480: Scan: ingest process expectation contract audit and add the audit module

- **ID**: ticket-480
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-11-04

## Goal and scope

Make `koru scan --semcod-artifacts` open one ticket for process expectations that no producer can satisfy.
A process whose expectation can never pass fails on every cycle (observed in subactor PLF-12778: 76 failures in
one day). `koru.expectation_audit` finds such expectations statically and read-only (rules S1-S5) and writes
`.expectation-audit/report.json`; the existing structured-report scanner turns actionable findings into the
`expectation_contract` ticket. The operator asked for an algorithmic search with an LLM repair lane through koru.
The change does not alter the verifier or any producer.

## Acceptance criteria

- [x] AC-01: `python -m koru.expectation_audit` classifies synthetic fixtures by rule (S1-S5) and writes the report.
- [x] AC-02: `scan_semcod_quality_artifacts` returns one `expectation_contract` suggestion for actionable findings and none for informational ones.
- [x] AC-03: Existing scan tests, ruff and `./project/governance-check.sh` pass.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
