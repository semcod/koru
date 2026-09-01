# Ticket 034: Align NLP package metadata with SubLLM runtime

- **ID**: ticket-034
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: PUBLICATION
- **Created**: 2026-09-01

## Goal and scope

Complete issue #37 after ticket-032 by aligning both standalone NLP package
extras and their operator documentation with the delivered central SubLLM
runtime. Installing either package with its `llm` extra must install
`korullm`, not an adapter-owned provider client, and both README files must
name the registered central route used by their default backend.

## Acceptance criteria

- [x] AC-01: The active user explicitly requested autonomous continuation and
  sequential closure of all remaining tasks on 2026-09-01.
- [x] AC-02: Both standalone `llm` extras depend on
  `korullm>=0.1.0,<2.0` and contain no direct provider dependency.
- [x] AC-03: Both package README files identify their registered central
  SubLLM route and assign provider/model/failover selection to central policy.
- [x] AC-04: TOML parsing, provider-reference scan, governance, Docker Compose
  and diff checks pass before protected publication closes issue #37.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
