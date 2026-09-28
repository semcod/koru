# Ticket 334: feat(autonomy): process uri registry and dsl reconfigurator

- **ID**: ticket-334
- **Owner**: agent:gemini
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-28

SESSION_EXECUTION_AUTHORIZATION: User requested implementation of process URI registry,
DSL reconfiguration, URN resource & action URI standards under wellmanifest/*,
and GBNF/JSON-guided query parsing for zero-hallucination reconfiguration.

## Goal and scope

1. Implement `ProcessUri` and `ProcessUriRegistry` in `src/koru/autonomy/process_uri.py`:
   - RFC 3986 parse & format for `action://scheme/action?query` and `urn:resource:...`.
   - Action schema registry defining required/optional params, descriptions, and handlers.
   - GBNF grammar generator (`to_gbnf()`) enforcing valid URIs and compact JSON payloads during LLM decoding.
2. Implement `koru reconfigure` engine and CLI command in `src/koru/autonomy/dsl_reconfigure.py` & `src/koru/cli_reconfigure.py`:
   - Parse concise `yaml: uri {json}` declarations.
   - Generate project runtime configurations and validate against `wellmanifest/dsl` standards.
3. Add comprehensive test suite in `tests/test_process_uri.py` and `tests/test_dsl_reconfigure.py`.

## Acceptance criteria

- [ ] AC-01: `ProcessUri` validates syntax, parses URNs/URIs, and extracts query/json parameters.
- [ ] AC-02: `ProcessUriRegistry` registers actions, validates payloads against schemas, and exports GBNF grammar.
- [ ] AC-03: `koru reconfigure` CLI parses `yaml: uri {json}` and executes atomic reconfigurations.
- [ ] AC-04: Test suite passes 100% and `governance-check.sh` reports `GOV-PASS`.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
