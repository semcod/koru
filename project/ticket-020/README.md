# Ticket 020: Restore queue lower-layer import contract

- **ID**: ticket-020
- **Owner**: agent:codex under SESSION_EXECUTION_AUTHORIZATION
- **GitHub issue**: #40
- **Status**: DONE
- **Workflow state**: DONE
- **Created**: 2026-08-28

## Goal and scope

Restore the declared dependency direction by moving shared todo2code process
helpers below both queue and autonomy consumers without changing behavior.

## Acceptance criteria

- [x] AC-01: `lint-imports` kept all declared contracts on the exact PR head.
- [x] AC-02: Focused todo2code and ticket hydration tests passed on the exact
  PR head.
- [x] AC-03: No queue module imports `koru.autonomy` in the delivered diff.

## Delivery evidence

- PR #42 exact head `f77af46c2cb1ccae87d60d2238afb4d1c4e2f16b` was
  merged at 2026-08-28T16:02:20Z as
  `e40b907d9871cfa8533d5405188f60e40e178f04`.
- `smoke=SUCCESS` and `onedev/local-verify=SUCCESS` were observed on that head.
- `ifuri-validator-agent[bot]` approved that same head with ticket and
  correlation bindings before merge.

## Participants

- Human participant: active-session authorization; no user-* file was created.
- Agent participant: [ai-codex.md](ai-codex.md)
