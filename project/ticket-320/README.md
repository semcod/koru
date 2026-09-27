# Ticket 320: NL shell multi-intent batching and tillm fallback for koru config

- **ID**: ticket-320
- **Owner**: human:tom
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-27
- **Authorization**: SESSION_EXECUTION_AUTHORIZATION

## Goal and scope

Expand the NL / DSL capabilities of `koru config`:
1. Support multi-intent batching: allow users to chain configuration requests in one line using conjunctions (`i`, `oraz`, `and`, `,`, `;`), e.g. `port na 9000 i ide na cursor i wlacz mesh`.
2. Apply mutations sequentially with combined summary messages and transaction rollbacks if any part fails validation.
3. Integrate graceful Layer 3 fallback to `koru.tillm_bridge` or shell LLM plugin when deterministic patterns do not match complex phrasing, asking for confirmation if needed.
4. Add automated unit and integration tests covering multi-intent chains.

## Acceptance criteria

- [ ] AC-01: Chained commands with `i`, `and`, `,`, `;` apply all requested configuration changes.
- [ ] AC-02: Partial failures in batch commands report clear error diagnostics without corrupting other valid keys.
- [ ] AC-03: Test suite passes with 0 regressions.
- [ ] AC-04: `./project/governance-check.sh` reports `GOV-PASS: passed (0 errors, 0 warnings)`.
