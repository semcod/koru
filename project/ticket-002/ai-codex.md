---
participant-id: agent:codex
participant: codex
role: agent
ticket: ticket-002
---
# Participant: codex (AI agent)

## Understanding

Koru already consumes todo2code and has a project ticket directory, but it has
no `AGENTS.md`, `.governance` package, immutable adoption lock or deterministic
governance gate. Goal's read-only adapter reports exactly 19 required managed
changes for new-project 0.11.0 and performs no target writes in check mode.

## Execution plan

1. After approval, transition ticket-002 to `IN_PROGRESS / EDIT`.
2. Seed a Koru-specific 0.11.0 manifest preserving Python/Docker ownership and
   the generator-owned analysis namespace.
3. Re-run Goal adoption in check mode, compare the exact plan and apply it.
4. Verify immutable lock provenance and work-classification hashes.
5. Run the deterministic governance gate, focused Koru tests and Docker checks.
6. Publish a ticket-scoped PR for independent current-head validation.

## Actual changes

- Governance plan only; runtime and managed package are unchanged.

## Preflight evidence

- Docker client/server: 29.1.3 / 29.1.3.
- Local Goal governance adapter: available.
- Check-mode result: 19 CREATE/UPDATE operations required; no target writes.
- Draft PR smoke reproduces the baseline Ruff failure from current `main`:
  36 existing findings in runtime files outside this ticket's allowed paths.

## Blockers

- Human approval is required before managed governance files are installed.
- Full hosted smoke cannot become green without a separate runtime-quality
  ticket or a reviewed CI baseline policy; neither is inferred here.
