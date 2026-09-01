# Ticket 032: Route NLP adapters through central SubLLM policy

- **ID**: ticket-032
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: PUBLICATION
- **Created**: 2026-09-01

## Goal and scope

Route both bundled natural-language adapters through the provider-neutral
SubLLM policy exposed by `korullm`. The default `nlp2koru` backend must invoke
`koru-agent/nl-to-koru-dsl`, while the default `nlp2coru` backend must invoke
`koru-agent/nl-to-coru-dsl`. Provider selection, failover and credentials stay
inside SubLLM; each adapter retains deterministic local parsing and its
injectable test-backend boundary.

The existing Python `model` parameters and CLI flag remain accepted as
deprecated compatibility hints for this release, but they no longer select a
provider or model. Obsolete adapter-owned provider configuration modules are
removed. Standalone dependency metadata and package documentation are a
dependent follow-up so this runtime ticket stays within the 15-file hard cap.

## Acceptance criteria

- [x] AC-01: The active user explicitly requested autonomous continuation and
  sequential closure of the remaining tasks on 2026-09-01.
- [x] AC-02: Default `nlp2koru` completions use only the
  `koru-agent/nl-to-koru-dsl` SubLLM route.
- [x] AC-03: Default `nlp2coru` completions use only the
  `koru-agent/nl-to-coru-dsl` SubLLM route.
- [x] AC-04: Caller-injected backends remain supported, while `model` values
  are compatibility-only and no provider environment variable activates LLM
  execution implicitly.
- [x] AC-05: Offline deterministic mapping remains bounded and available when
  SubLLM is unavailable or returns invalid output.
- [x] AC-06: Adapter runtime source contains no local provider-selection
  implementation or provider-trigger environment variable.
- [x] AC-07: Package tests, changed-file Ruff, anomaly scan, governance and
  Docker Compose checks pass before protected exact-head publication.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
